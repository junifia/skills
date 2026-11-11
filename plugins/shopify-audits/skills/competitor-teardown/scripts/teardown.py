#!/usr/bin/env python3
"""Competitor teardown: read a store's public pages and compute catalog,
pricing, merchandising, app and policy facts as JSON.

Python standard library only. Read-only. Public pages only.

Usage:
  python3 teardown.py https://competitor.com [https://other.com ...]
  python3 teardown.py https://competitor.com --own https://mystore.com
  python3 teardown.py https://competitor.com --track [--snapshot-dir DIR]
  python3 teardown.py https://competitor.com --track --previous old.json

Politeness rules (not configurable upward):
  - robots.txt is fetched first and respected for every request
  - at most 15 requests per store, one at a time, with a delay between them
  - a 429 is retried once only if the store asks for a short wait
  - 401, 403, captchas and password pages are never worked around
"""

import argparse
import datetime as dt
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

VERSION = "0.1.0"
USER_AGENT = (
    "Mozilla/5.0 (compatible; JunifiaTeardown/" + VERSION
    + "; +https://github.com/junifia/skills)"
)
ROBOTS_TOKEN = "junifiateardown"
MAX_REQUESTS = 15
MAX_BYTES = 8 * 1024 * 1024
PAGE_SIZE = 250
SIGNATURES_FILE = Path(__file__).resolve().parent.parent / "references" / "app-signatures.md"

BUNDLE_RE = re.compile(
    r"\b(bundle|bundles|kit|gift set|set of \d+|value pack|variety pack|\d+[- ]?pack|"
    r"pack of \d+|duo|trio|combo|starter set|sampler)\b",
    re.I,
)
NON_MERCH_RE = re.compile(
    r"gift ?card|e-?gift|insurance|shipping protection|package protection|packing material|gift wrap", re.I)
SEASONAL_COLLECTION_RE = re.compile(
    r"black friday|cyber|bfcm|holiday|christmas|gift|sale|deal|clearance|outlet|last chance",
    re.I,
)
PROMO_RE = re.compile(
    r"(\d{1,2}\s?% off|up to \d{1,2}\s?%|black friday|cyber monday|buy one,? get one|\bbogo\b|"
    r"free gift|gift with purchase|subscribe (?:&|and) save|sitewide|site-wide|"
    r"free (?:\w+ )?(?:shipping|delivery))",
    re.I,
)
AMOUNT = r"\d{1,3}(?:[,.]\d{3})+(?:[.,]\d{2})?|\d{1,6}(?:[.,]\d{2})?"
MONEY_RE = re.compile(
    r"(?:(?P<sym>[$£€¥₹]|[A-Z]{1,3}\$|CHF|kr)\s?(?P<a1>" + AMOUNT + r"))"
    r"|(?:(?P<a2>" + AMOUNT + r")\s?(?P<code>USD|CAD|AUD|NZD|EUR|GBP|SEK|NOK|DKK|CHF|JPY|€|kr))"
)
FREE_SHIP_RE = re.compile(r"free (?:\w+ ){0,2}(?:shipping|delivery)|ships? free|shipping is free", re.I)
THRESHOLD_WORDS_RE = re.compile(r"over|above|from|orders of|spend|or more|\+|minimum|when you", re.I)
RETURN_DAYS_RE = re.compile(r"(\d{1,3})[\s-]*(?:\(\d{1,3}\)\s*)?(?:calendar |business )?days?\b", re.I)
RETURN_WORDS_RE = re.compile(r"return|refund|exchange", re.I)
NO_RETURNS_RE = re.compile(
    r"(?:do not|don't|don’t|does not|cannot|can't|can’t|unable to) (?:accept|offer|take) (?:any )?returns|"
    r"\bno returns\b|all sales (?:are )?final", re.I)
RETURN_TERMS = [
    ("free returns", re.compile(r"free returns?", re.I)),
    ("free exchanges", re.compile(r"free exchanges?", re.I)),
    ("final sale items", re.compile(r"final sale", re.I)),
    ("restocking fee", re.compile(r"restocking fee", re.I)),
    ("return fee", re.compile(r"[$£€]\s?\d+(?:[.,]\d{2})? returns?|return (?:shipping )?(?:fee|label) (?:of|is)", re.I)),
    ("store credit", re.compile(r"store credit", re.I)),
    ("money-back guarantee", re.compile(r"money[- ]back guarantee", re.I)),
]
DEEP_DISCOUNT = 0.70


# ---------------------------------------------------------------- robots.txt

def parse_robots(text):
    """Return rules for our token, else for '*': list of (allow, pattern)."""
    groups, agents, rules, last_was_agent = [], [], [], False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            if not last_was_agent and agents:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
            last_was_agent = True
        elif key in ("allow", "disallow"):
            last_was_agent = False
            if agents and value:
                rules.append((key == "allow", value))
    if agents:
        groups.append((agents, rules))
    for wanted in (ROBOTS_TOKEN, "*"):
        matched = [r for a, r in groups if wanted in a]
        if matched:
            return [rule for rs in matched for rule in rs]
    return []


def _pattern_regex(pattern):
    anchored = pattern.endswith("$")
    body = re.escape(pattern.rstrip("$")).replace(r"\*", ".*")
    return re.compile("^" + body + ("$" if anchored else ""))


def robots_allows(rules, path):
    """Longest matching rule wins; on a tie, allow wins (Google's rules)."""
    best_len, allowed = -1, True
    for allow, pattern in rules:
        if _pattern_regex(pattern).match(path):
            if len(pattern) > best_len or (len(pattern) == best_len and allow):
                best_len, allowed = len(pattern), allow
    return allowed


# ------------------------------------------------------------------ fetching

class Fetcher:
    """Polite, budgeted, robots-aware GET client for one store."""

    def __init__(self, origin, delay, max_wait):
        self.origin = origin
        self.delay = delay
        self.max_wait = max_wait
        self.made = 0
        self.log = []
        self.rules = []
        self.robots_status = "not fetched"
        self._last = 0.0

    def _wait(self, seconds=None):
        gap = self.delay if seconds is None else seconds
        sleep_for = self._last + gap - time.monotonic()
        if sleep_for > 0:
            time.sleep(sleep_for)

    def _raw_get(self, url):
        self._wait()
        self.made += 1
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        })
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                body = resp.read(MAX_BYTES)
                status, headers, final = resp.status, resp.headers, resp.geturl()
        except urllib.error.HTTPError as err:
            body = err.read(MAX_BYTES) if err.fp else b""
            status, headers, final = err.code, err.headers, err.geturl()
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            self._last = time.monotonic()
            return {"status": None, "error": str(getattr(err, "reason", err)),
                    "headers": {}, "text": "", "url": url}
        self._last = time.monotonic()
        charset = headers.get_content_charset() if headers else None
        return {"status": status, "headers": headers or {}, "url": final,
                "text": body.decode(charset or "utf-8", "replace")}

    def load_robots(self):
        res = self._raw_get(self.origin + "/robots.txt")
        self.log.append({"path": "/robots.txt", "status": res["status"]})
        if res["status"] == 200:
            self.rules = parse_robots(res["text"])
            self.robots_status = "found"
            final = urllib.parse.urlsplit(res["url"])
            self.origin = f"{final.scheme}://{final.netloc}"
        elif res["status"] is not None and 400 <= res["status"] < 500:
            self.robots_status = "none (all allowed)"
        else:
            self.rules = [(False, "/")]
            self.robots_status = "unreachable (treated as disallow all)"

    def get(self, path, label=None):
        """Return the response dict, or a dict with 'skipped' explaining why."""
        entry = {"path": path}
        if label:
            entry["label"] = label
        self.log.append(entry)
        if not robots_allows(self.rules, path):
            entry["skipped"] = "disallowed by robots.txt"
            return {"skipped": entry["skipped"]}
        if self.made >= MAX_REQUESTS:
            entry["skipped"] = "request budget used up"
            return {"skipped": entry["skipped"]}
        res = self._raw_get(self.origin + path)
        if res["status"] == 429 and self.made < MAX_REQUESTS:
            retry_after = _retry_after_seconds(res["headers"])
            if retry_after is not None and retry_after <= self.max_wait:
                self._wait(retry_after)
                res = self._raw_get(self.origin + path)
                entry["retried_after_seconds"] = retry_after
        entry["status"] = res["status"]
        if res.get("error"):
            entry["error"] = res["error"]
        return res


def _retry_after_seconds(headers):
    value = headers.get("Retry-After") if headers else None
    if value and value.strip().isdigit():
        return int(value.strip())
    return None


def describe_failure(res):
    if "skipped" in res:
        return res["skipped"]
    status = res.get("status")
    if status is None:
        return "could not connect (" + res.get("error", "network error") + ")"
    if status == 429:
        return "rate limited by the store (HTTP 429)"
    if status in (401, 403):
        return f"blocked by the store (HTTP {status})"
    if status == 404:
        return "not found (HTTP 404)"
    return f"HTTP {status}"


def as_json(res):
    if res.get("status") != 200:
        return None
    try:
        return json.loads(res["text"])
    except ValueError:
        return None


# --------------------------------------------------------------- HTML parsing

class PageParser(HTMLParser):
    """Collects visible text, links, announcement text and code strings."""

    SKIP_TEXT = {"script", "style", "noscript", "svg", "template"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.code = [], [], []
        self.announcements = []
        self.policy_text = []
        self._stack = []
        self._link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = (attrs.get("class") or "") + " " + (attrs.get("id") or "")
        if attrs.get("class"):
            self.code.append(attrs["class"])
        for key in ("src", "href", "data-src"):
            if attrs.get(key) and tag in ("script", "link", "iframe", "img"):
                self.code.append(attrs[key])
        if tag in self.VOID:
            return
        self._stack.append((tag, "announcement" in cls.lower(), "shopify-policy__body" in cls.lower()))
        if tag == "a" and attrs.get("href"):
            self._link = [attrs["href"], []]

    def handle_endtag(self, tag):
        if tag == "a" and self._link:
            self.links.append((self._link[0], " ".join("".join(self._link[1]).split())))
            self._link = None
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        current = self._stack[-1][0] if self._stack else ""
        if current in ("script", "style"):
            if current == "script" and data.strip():
                self.code.append(data)
            return
        if any(item[0] in self.SKIP_TEXT for item in self._stack):
            return
        if not data.strip():
            return
        self.text.append(data)
        if self._link is not None:
            self._link[1].append(data)
        if any(item[1] for item in self._stack):
            self.announcements.append(" ".join(data.split()))
        if any(item[2] for item in self._stack):
            self.policy_text.append(data)


def parse_page(text):
    parser = PageParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception:  # malformed HTML: keep what was parsed
        pass
    visible = " ".join(" ".join(parser.text).split())
    seen, announcements = set(), []
    for line in parser.announcements:
        if line and line.lower() not in seen and len(line.split()) >= 3:
            seen.add(line.lower())
            announcements.append(line[:200])
    return {
        "text": visible,
        "links": parser.links,
        "code": "\n".join(parser.code).lower(),
        "announcements": announcements[:8],
        "policy_text": " ".join(" ".join(parser.policy_text).split()),
    }


def snippet(text, start, end, pad=70):
    a, b = max(0, start - pad), min(len(text), end + pad)
    return ("..." if a else "") + text[a:b].strip() + ("..." if b < len(text) else "")


# ------------------------------------------------------------ detections

def detect_platform(home_res):
    headers = home_res.get("headers") or {}
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items()).lower() if headers else ""
    raw = home_res.get("text", "")
    signals = []
    if "x-shopid" in header_blob or "x-shopify-stage" in header_blob:
        signals.append("Shopify response headers")
    if "powered-by: shopify" in header_blob:
        signals.append("'powered-by: Shopify' header")
    if "hydrogen" in header_blob or "oxygen" in header_blob:
        signals.append("Hydrogen or Oxygen headers (headless Shopify)")
    if "Shopify.theme" in raw:
        signals.append("Shopify theme script on homepage")
    if "cdn.shopify.com" in raw:
        signals.append("assets served from cdn.shopify.com")
    if "myshopify.com" in raw:
        signals.append("myshopify.com reference in homepage code")
    theme = None
    m = re.search(r"Shopify\.theme\s*=\s*(\{.*?\})\s*;", raw, re.S)
    if m:
        try:
            data = json.loads(m.group(1))
            theme = {
                "name": data.get("name"),
                "base_theme": data.get("schema_name"),
                "base_theme_version": data.get("schema_version"),
                "theme_store_id": data.get("theme_store_id"),
            }
        except ValueError:
            theme = {"name": None, "base_theme": None, "note": "theme script found but unreadable"}
    return signals, theme


def load_signatures():
    apps = []
    try:
        lines = SIGNATURES_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return apps
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("App", "") or set(cells[0]) <= {"-"}:
            continue
        sigs = re.findall(r"`([^`]+)`", cells[2])
        if sigs:
            apps.append({"app": cells[0], "category": cells[1], "signatures": [s.lower() for s in sigs]})
    return apps


def detect_apps(code):
    found = []
    for app in load_signatures():
        hits = [s for s in app["signatures"] if s in code]
        if hits:
            found.append({"app": app["app"], "category": app["category"],
                          "evidence": "homepage code contains " + ", ".join(f"'{h}'" for h in hits)})
    return found


def parse_money(match):
    """'1,000.00', '1.000,00', '1,000' are a thousand; '49,99' and '49.99' are decimals."""
    amount = match.group("a1") or match.group("a2")
    symbol = match.group("sym") or match.group("code") or ""
    groups = re.split(r"[.,]", amount)
    if len(groups) > 1 and len(groups[-1]) == 2:
        amount = "".join(groups[:-1]) + "." + groups[-1]
    else:
        amount = "".join(groups)
    return float(amount), symbol


def find_free_shipping(sources):
    """sources: list of (label, text). Returns candidates with evidence."""
    candidates = []
    for label, text in sources:
        if not text:
            continue
        for m in FREE_SHIP_RE.finditer(text):
            window_start, window_end = max(0, m.start() - 90), min(len(text), m.end() + 90)
            window = text[window_start:window_end]
            money = [mm for mm in MONEY_RE.finditer(window)]
            threshold = None
            for mm in money:
                near = window[max(0, mm.start() - 30):mm.start()]
                if THRESHOLD_WORDS_RE.search(near) or THRESHOLD_WORDS_RE.search(window[mm.end():mm.end() + 12]):
                    threshold = parse_money(mm)
                    break
            entry = {"source": label, "evidence": snippet(text, m.start(), m.end())}
            if threshold:
                entry["threshold"] = threshold[0]
                entry["currency_symbol"] = threshold[1]
            elif re.search(r"all orders|every order|on everything", window, re.I):
                entry["threshold"] = 0
            candidates.append(entry)
            if len(candidates) >= 6:
                return candidates
    return candidates


def summarize_free_shipping(candidates):
    with_amount = [c for c in candidates if c.get("threshold") is not None]
    if not with_amount:
        if candidates:
            return {"status": "free shipping mentioned, no threshold detected", "evidence": candidates[:3]}
        return {"status": "not detected", "evidence": []}
    values = Counter(c["threshold"] for c in with_amount)
    top, _ = values.most_common(1)[0]
    status = "free on all orders" if top == 0 else "threshold detected"
    result = {"status": status, "threshold": top,
              "evidence": [c for c in with_amount if c["threshold"] == top][:3]}
    if len(values) > 1:
        result["other_thresholds_seen"] = sorted(v for v in values if v != top)
    return result


def find_return_terms(text):
    terms = []
    for name, rx in RETURN_TERMS:
        m = rx.search(text or "")
        if m:
            terms.append({"term": name, "evidence": snippet(text, m.start(), m.end(), 60)})
    return terms


def find_return_window(text):
    if not text:
        return {"status": "not detected", "evidence": []}
    no_returns = NO_RETURNS_RE.search(text)
    days = Counter()
    evidence = {}
    for m in RETURN_DAYS_RE.finditer(text):
        n = int(m.group(1))
        if not 1 <= n <= 365:
            continue
        window = text[max(0, m.start() - 120):m.end() + 120]
        if RETURN_WORDS_RE.search(window):
            days[n] += 1
            evidence.setdefault(n, snippet(text, m.start(), m.end()))
    terms = find_return_terms(text)
    if not days:
        if no_returns:
            return {"status": "no returns stated", "evidence": [snippet(text, no_returns.start(), no_returns.end())],
                    "terms": terms}
        return {"status": "not detected", "evidence": [], "terms": terms}
    top, _ = days.most_common(1)[0]
    return {"status": "detected", "days": top,
            "other_day_counts_mentioned": sorted(d for d in days if d != top),
            "evidence": [evidence[top]], "terms": terms}


# --------------------------------------------------------------- metrics

def to_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def parse_time(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def nice_bands(prices):
    """Round price bands on a 1-2-5 scale, about 4 to 6 bands."""
    if not prices:
        return []
    lo, hi = min(prices), max(prices)
    ladder = [m * 10 ** e for e in range(-1, 7) for m in (1, 2, 5)]
    edges = [x for x in ladder if lo < x < hi]
    while len(edges) > 5:
        edges = edges[1::2] if len(edges) % 2 == 0 else edges[::2]
    bounds = [0] + edges + [None]
    bands = []
    for low, high in zip(bounds, bounds[1:]):
        count = sum(1 for p in prices if p >= low and (high is None or p < high))
        label = f"{_fmt(low)} and up" if high is None else f"{_fmt(low)} to under {_fmt(high)}"
        bands.append({"band": label, "products": count, "share": pct(count, len(prices))})
    return bands


def _fmt(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}"


def pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


def quantile(sorted_values, q):
    if not sorted_values:
        return None
    idx = (len(sorted_values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    return round(sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (idx - lo), 2)


def top_counts(values, n, total):
    """total is the number of products, so shares read as 'share of products'."""
    counts = Counter(v for v in values if v)
    return [{"value": k, "products": c, "share": pct(c, total)} for k, c in counts.most_common(n)]


def catalog_metrics(products, now):
    priced, sale_depths, gift_cards, zero_priced, bundles, deep = [], [], 0, 0, [], []
    variant_total, variant_oos, sold_out_products, on_sale_products, on_sale_variants = 0, 0, 0, 0, 0
    variants_per_product = []
    created_30 = created_90 = published_30 = published_90 = 0
    for p in products:
        variants = p.get("variants") or []
        variants_per_product.append(len(variants))
        variant_total += len(variants)
        oos = sum(1 for v in variants if v.get("available") is False)
        variant_oos += oos
        if variants and oos == len(variants):
            sold_out_products += 1
        for key in ("created_at", "published_at"):
            stamp = parse_time(p.get(key))
            if stamp:
                age = (now - stamp).days
                if key == "created_at":
                    created_30 += age <= 30
                    created_90 += age <= 90
                else:
                    published_30 += age <= 30
                    published_90 += age <= 90
        title = p.get("title") or ""
        if NON_MERCH_RE.search(title) or NON_MERCH_RE.search(p.get("product_type") or ""):
            gift_cards += 1
            continue
        prices = [to_float(v.get("price")) for v in variants]
        prices = [x for x in prices if x is not None]
        if prices:
            low = min(prices)
            if low == 0:
                zero_priced += 1
            else:
                priced.append(low)
        depth = 0.0
        for v in variants:
            price, compare = to_float(v.get("price")), to_float(v.get("compare_at_price"))
            if price is not None and compare and compare > price:
                on_sale_variants += 1
                depth = max(depth, (compare - price) / compare)
        if depth > 0:
            on_sale_products += 1
            sale_depths.append(depth)
        if depth >= DEEP_DISCOUNT:
            deep.append({"title": title, "type": p.get("product_type") or None, "discount_pct": round(100 * depth, 1)})
        if BUNDLE_RE.search(title):
            bundles.append(title)
    priced.sort()
    sale_depths.sort()
    counted = len(products) - gift_cards
    return {
        "products_analyzed": len(products),
        "non_merchandise_excluded_from_pricing": gift_cards,
        "zero_price_products": zero_priced,
        "product_types": {"distinct": len({p.get("product_type") for p in products if p.get("product_type")}),
                          "products_without_type": sum(1 for p in products if not p.get("product_type")),
                          "top": top_counts([p.get("product_type") for p in products], 10, len(products))},
        "vendors": {"distinct": len({p.get("vendor") for p in products if p.get("vendor")}),
                    "top": top_counts([p.get("vendor") for p in products], 10, len(products))},
        "tags": {"distinct": len({t for p in products for t in _tags(p)}),
                 "top": top_counts([t for p in products for t in set(_tags(p))], 15, len(products))},
        "price": {
            "basis": "lowest variant price per product; gift cards, shipping insurance, packing and gift wrap add-ons, and zero prices excluded",
            "products_priced": len(priced),
            "min": priced[0] if priced else None,
            "p25": quantile(priced, 0.25),
            "median": quantile(priced, 0.5),
            "p75": quantile(priced, 0.75),
            "max": priced[-1] if priced else None,
            "bands": nice_bands(priced),
        },
        "discounts": {
            "basis": "a product is on sale if any variant has a compare-at price above its price",
            "products_on_sale": on_sale_products,
            "products_on_sale_pct": pct(on_sale_products, counted),
            "variants_on_sale": on_sale_variants,
            "median_discount_pct": round(100 * statistics.median(sale_depths), 1) if sale_depths else None,
            "max_discount_pct": round(100 * sale_depths[-1], 1) if sale_depths else None,
            "deep_discount_outliers": deep[:10],
            "deep_discount_note": ("70% or more off is unusual. Sometimes it is a real clearance, but it often "
                                   "means the compare-at price holds a multi-month, multi-pack or bundle value, "
                                   "or an old reference price. Check these before treating them as sales.") if deep else None,
        },
        "variants": {
            "total": variant_total,
            "per_product_median": statistics.median(variants_per_product) if variants_per_product else None,
            "per_product_mean": round(statistics.mean(variants_per_product), 1) if variants_per_product else None,
            "per_product_max": max(variants_per_product) if variants_per_product else None,
            "out_of_stock_variants": variant_oos,
            "out_of_stock_variants_pct": pct(variant_oos, variant_total),
            "fully_sold_out_products": sold_out_products,
            "fully_sold_out_products_pct": pct(sold_out_products, len(products)),
        },
        "new_products": {
            "created_last_30_days": created_30,
            "created_last_90_days": created_90,
            "published_last_30_days": published_30,
            "published_last_90_days": published_90,
            "note": "published dates also change when a product is re-published, so created dates are the better measure of new launches",
        },
        "bundles": {
            "basis": "heuristic: product titles containing words like bundle, kit, set, pack, duo, trio",
            "count": len(bundles),
            "examples": bundles[:10],
        },
    }


def _tags(product):
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return [t for t in tags if t]


def product_price(product):
    prices = [to_float(v.get("price")) for v in product.get("variants") or []]
    prices = [x for x in prices if x is not None]
    compares = [to_float(v.get("compare_at_price")) for v in product.get("variants") or []]
    compares = [x for x in compares if x]
    return {
        "price_from": min(prices) if prices else None,
        "compare_at_max": max(compares) if compares else None,
        "available": any(v.get("available") for v in product.get("variants") or []),
    }


def best_sellers(fetcher, products, notes):
    res = fetcher.get("/collections/all?sort_by=best-selling", "best sellers")
    if res.get("status") != 200:
        reason = describe_failure(res)
        notes.append("Best sellers not detected: " + reason + ".")
        return {"status": "not detected", "reason": reason, "items": []}
    page = parse_page(res["text"])
    by_handle = {p.get("handle"): p for p in products}
    handles, titles = [], {}
    for href, text in page["links"]:
        m = re.search(r"/products/([a-z0-9][a-z0-9\-_%]*)", href, re.I)
        if m:
            handle = urllib.parse.unquote(m.group(1)).lower()
            if handle not in handles:
                handles.append(handle)
            if text and handle not in titles:
                titles[handle] = text[:120]
    items = []
    for rank, handle in enumerate(handles[:10], 1):
        p = by_handle.get(handle)
        item = {"rank": rank, "handle": handle,
                "title": (p or {}).get("title") or titles.get(handle) or handle}
        if p:
            item.update(product_price(p))
        items.append(item)
    if not items:
        notes.append("Best sellers page loaded but no products could be read from it.")
        return {"status": "not detected", "reason": "no products found on the page", "items": []}
    return {"status": "detected",
            "basis": "order of the store's own 'best selling' sort on its all-products page",
            "items": items}


# ------------------------------------------------------------------ store run

def _bare_host(host):
    return host[4:] if host.startswith("www.") else host


def normalize_origin(url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parts = urllib.parse.urlsplit(url)
    return f"https://{parts.netloc.lower()}"


def analyze_store(url, role, args, now):
    origin = normalize_origin(url)
    fetcher = Fetcher(origin, args.delay, args.max_wait)
    notes = []
    out = {"input_url": url, "role": role, "origin": origin}

    fetcher.load_robots()
    out["robots_txt"] = fetcher.robots_status

    home = fetcher.get("/", "homepage")
    if home.get("status") != 200:
        reason = describe_failure(home)
        notes.append("Homepage could not be read: " + reason + ". Nothing else was fetched.")
        out.update(platform={"type": "unknown"}, data_notes=notes, confidence="none",
                   requests={"made": fetcher.made, "log": fetcher.log})
        return out, None, False
    final = urllib.parse.urlsplit(home["url"])
    new_origin = f"{final.scheme}://{final.netloc}"
    if _bare_host(final.netloc) != _bare_host(urllib.parse.urlsplit(origin).netloc):
        notes.append(f"The site sent visitors to {final.netloc}, so results describe the store at that address.")
    if final.netloc != urllib.parse.urlsplit(fetcher.origin).netloc:
        # Another host has its own robots.txt: read it before anything else there.
        fetcher.origin = new_origin
        fetcher.load_robots()
        out["robots_txt"] = fetcher.robots_status + f" (for {final.netloc})"
        if not robots_allows(fetcher.rules, "/"):
            notes.append(f"The robots.txt of {final.netloc} asks tools not to read it. Nothing else was fetched.")
            out.update(origin=fetcher.origin, platform={"type": "unknown"}, data_notes=notes, confidence="none",
                       requests={"made": fetcher.made, "log": fetcher.log})
            return out, None, False
    fetcher.origin = new_origin
    out["origin"] = fetcher.origin
    if final.path.rstrip("/").endswith("/password"):
        notes.append("The store is password protected. Nothing else was fetched.")
        out.update(platform={"type": "shopify_password_protected"}, data_notes=notes, confidence="none",
                   requests={"made": fetcher.made, "log": fetcher.log})
        return out, None, False

    page = parse_page(home["text"])
    signals, theme = detect_platform(home)
    if len(page["links"]) < 10 or len(page["text"].split()) < 200:
        out["homepage_thin"] = True
        notes.append("The homepage returned very little content (possibly a bot check or a page that needs "
                     "JavaScript to load). Findings from the homepage are incomplete.")

    meta, products, capped = None, [], False
    if signals:
        meta = as_json(fetcher.get("/meta.json", "store info"))
        if not isinstance(meta, dict) or "myshopify_domain" not in meta:
            meta = None
        else:
            signals.append("meta.json answered like a Shopify store")

    products_failure = None
    if signals:
        for page_no in range(1, args.max_pages + 1):
            res = fetcher.get(f"/products.json?limit={PAGE_SIZE}&page={page_no}", f"products page {page_no}")
            data = as_json(res)
            if not isinstance(data, dict) or "products" not in data:
                products_failure = describe_failure(res) if res.get("status") != 200 else "did not return product data"
                if page_no > 1:
                    notes.append(f"Products page {page_no} could not be read ({products_failure}), so the product list is partial.")
                    capped = True
                break
            batch = data["products"]
            products.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            if page_no == args.max_pages:
                capped = True
                notes.append(f"Product list capped at {args.max_pages} pages ({len(products)} products). Numbers describe these products only.")

    if theme or products:
        platform_type = "shopify_online_store"
    elif signals:
        platform_type = "shopify_headless_or_custom"
    else:
        platform_type = "not_shopify"
    out["platform"] = {"type": platform_type, "evidence": signals, "theme": theme}
    if platform_type == "not_shopify":
        notes.append("No Shopify signals found. This is an HTML-only teardown of the homepage and any shipping or returns page linked from it.")
    elif not products:
        notes.append("Product data not available (" + (products_failure or "not attempted") + "). Catalog and pricing sections are not detected.")

    if meta:
        out["store"] = {
            "name": meta.get("name"),
            "currency": meta.get("currency"),
            "country": meta.get("country"),
            "published_products_count": meta.get("published_products_count"),
            "published_collections_count": meta.get("published_collections_count"),
            "ships_to_countries_count": len(meta.get("ships_to_countries") or []),
            "shop_pay_installments": meta.get("offers_shop_pay_installments"),
        }

    if products:
        out["catalog"] = catalog_metrics(products, now)
        out["catalog"]["capped"] = capped
        if meta and meta.get("published_products_count"):
            out["catalog"]["store_reported_product_count"] = meta["published_products_count"]

    if platform_type != "not_shopify":
        cols = as_json(fetcher.get(f"/collections.json?limit={PAGE_SIZE}", "collections"))
        if isinstance(cols, dict) and "collections" in cols:
            items = cols["collections"]
            seasonal = [{"title": c.get("title"), "products": c.get("products_count"),
                         "published_at": (c.get("published_at") or "")[:10]}
                        for c in items if SEASONAL_COLLECTION_RE.search(c.get("title") or "")]
            out["collections"] = {
                "fetched": len(items),
                "capped": len(items) >= PAGE_SIZE,
                "products_count_note": "collection product counts come from the store and can include products not visible online",
                "sale_or_seasonal": seasonal[:20],
                "empty_published": sum(1 for c in items if c.get("products_count") == 0),
            }
            if len(items) >= PAGE_SIZE:
                total = (meta or {}).get("published_collections_count")
                notes.append(f"Collections list capped at {PAGE_SIZE}" + (f" of {total}" if total else "") + ".")
        else:
            notes.append("Collections list not available.")

    if products:
        out["best_sellers"] = best_sellers(fetcher, products, notes)

    out["merchandising"] = merchandising(page)
    out["apps"] = {
        "detected": detect_apps(page["code"]),
        "note": "Only apps whose code loads on the homepage can be detected. Not detected does not mean not used.",
    }

    policies = fetch_policies(fetcher, page, platform_type, notes)
    shipping_text = policies.pop("_shipping_text", "")
    refund_text = policies.pop("_refund_text", "")
    out["policies"] = policies
    out["free_shipping"] = summarize_free_shipping(find_free_shipping([
        ("announcement bar", " | ".join(page["announcements"])),
        ("homepage", page["text"]),
        ("shipping policy", shipping_text),
    ]))
    out["return_window"] = find_return_window(refund_text)

    # Best sellers are left out on purpose: most stores' robots.txt disallows that page.
    policies_found = sum(1 for k in ("shipping", "refund") if policies[k]["status"] == "found")
    if not products:
        confidence = "low"
    elif capped or policies_found < 2:
        confidence = "medium"
    else:
        confidence = "high"
    out["confidence"] = confidence
    out["data_notes"] = notes
    out["requests"] = {"made": fetcher.made, "limit": MAX_REQUESTS, "log": fetcher.log}
    return out, products or None, capped


def merchandising(page):
    collection_links, seen = [], set()
    for href, text in page["links"]:
        m = re.search(r"/collections/([a-z0-9][a-z0-9\-_]*)/?(?:$|\?)", href, re.I)
        if m and m.group(1).lower() not in seen and text:
            seen.add(m.group(1).lower())
            collection_links.append({"text": text[:60], "handle": m.group(1).lower()})
    promos, promo_seen = [], set()
    for source, text in (("announcement bar", " | ".join(page["announcements"])), ("homepage", page["text"])):
        for m in PROMO_RE.finditer(text):
            key = m.group(0).lower()
            if key not in promo_seen:
                promo_seen.add(key)
                promos.append({"phrase": m.group(0), "source": source, "evidence": snippet(text, m.start(), m.end(), 50)})
    return {
        "announcement_bar": page["announcements"] or "not detected",
        "homepage_collection_links": collection_links[:20],
        "promo_phrases": promos[:10],
    }


def _main_text(raw_html):
    """Policy body only when the page marks it, else all visible text."""
    parsed = parse_page(raw_html)
    return parsed["policy_text"] if len(parsed["policy_text"].split()) >= 5 else parsed["text"]


POLICY_PATHS = {"shipping": "/policies/shipping-policy", "refund": "/policies/refund-policy"}
POLICY_LINK_WORDS = {"shipping": re.compile(r"shipping|delivery", re.I),
                     "refund": re.compile(r"return|refund|exchange", re.I)}


def fetch_policies(fetcher, page, platform_type, notes):
    result = {}
    for kind in ("shipping", "refund"):
        info, text = {"status": "not detected"}, ""
        if platform_type != "not_shopify":
            res = fetcher.get(POLICY_PATHS[kind], f"{kind} policy")
            if res.get("status") == 200:
                body = _main_text(res["text"])
                if len(body.split()) >= 5:
                    info = {"status": "found", "source": POLICY_PATHS[kind], "words": len(body.split())}
                    text = body
                else:
                    info["first_try"] = "page loaded but had no readable text (it may need JavaScript)"
            else:
                info["first_try"] = describe_failure(res)
        if not text:
            home_host = urllib.parse.urlsplit(fetcher.origin).netloc
            for href, label in page["links"]:
                parts = urllib.parse.urlsplit(urllib.parse.urljoin(fetcher.origin + "/", href))
                if parts.scheme not in ("http", "https"):
                    continue
                if not (POLICY_LINK_WORDS[kind].search(label or "") or POLICY_LINK_WORDS[kind].search(parts.path)):
                    continue
                path = parts.path or "/"
                if path in ("/", POLICY_PATHS[kind]) or "/products/" in path or "/collections/" in path:
                    continue
                if parts.netloc != home_host:
                    info.setdefault("linked_to_other_site", f"{parts.scheme}://{parts.netloc}{path}")
                    continue
                res = fetcher.get(path, f"{kind} page linked from homepage")
                if res.get("status") == 200:
                    body = _main_text(res["text"])
                    if len(body.split()) > 40:
                        info = {"status": "found", "source": path, "words": len(body.split())}
                        text = body
                break
        if not text and info.get("linked_to_other_site"):
            info["status"] = "not read"
            notes.append(f"{kind.capitalize()} information is on another site ({info['linked_to_other_site']}), which was not read.")
        elif not text:
            notes.append(f"{kind.capitalize()} policy not detected.")
        result[kind] = info
        result["_" + kind + "_text"] = text
    return result


# ------------------------------------------------------------------- tracking

def snapshot_of(products, origin, capped, now):
    return {
        "tool_version": VERSION,
        "store": origin,
        "taken_at": now.isoformat(timespec="seconds"),
        "capped": capped,
        "products": {
            str(p["id"]): {
                "handle": p.get("handle"),
                "title": p.get("title"),
                "variants": {
                    str(v["id"]): {
                        "title": v.get("title"),
                        "price": to_float(v.get("price")),
                        "compare_at_price": to_float(v.get("compare_at_price")),
                        "available": v.get("available"),
                    } for v in p.get("variants") or []
                },
            } for p in products if p.get("id") is not None
        },
    }


def _on_sale(variant):
    return bool(variant["compare_at_price"] and variant["price"] is not None
                and variant["compare_at_price"] > variant["price"])


def diff_snapshots(old, new, limit=25):
    old_p, new_p = old["products"], new["products"]
    added = [new_p[k] for k in new_p if k not in old_p]
    removed = [old_p[k] for k in old_p if k not in new_p]
    price_changes, compare_changes, stock_changes = [], [], []
    for pid in set(old_p) & set(new_p):
        for vid, nv in new_p[pid]["variants"].items():
            ov = old_p[pid]["variants"].get(vid)
            if not ov:
                continue
            label = new_p[pid]["title"] + ("" if nv["title"] in (None, "Default Title") else " (" + nv["title"] + ")")
            if ov["price"] != nv["price"] and None not in (ov["price"], nv["price"]):
                change = round(100 * (nv["price"] - ov["price"]) / ov["price"], 1) if ov["price"] else None
                price_changes.append({"item": label, "old": ov["price"], "new": nv["price"], "change_pct": change})
            if ov["compare_at_price"] != nv["compare_at_price"]:
                compare_changes.append({"item": label, "old": ov["compare_at_price"], "new": nv["compare_at_price"],
                                        "price_now": nv["price"],
                                        "was_on_sale": _on_sale(ov), "now_on_sale": _on_sale(nv)})
            if ov["available"] != nv["available"]:
                stock_changes.append({"item": label, "now": "available" if nv["available"] else "sold out"})
    sale_started = sum(1 for c in compare_changes if c["now_on_sale"] and not c["was_on_sale"])
    sale_ended = sum(1 for c in compare_changes if c["was_on_sale"] and not c["now_on_sale"])

    def first(items):
        return items[:limit]

    result = {
        "previous_snapshot_at": old["taken_at"],
        "current_snapshot_at": new["taken_at"],
        "counts": {
            "new_products": len(added),
            "removed_products": len(removed),
            "price_changes": len(price_changes),
            "price_increases": sum(1 for c in price_changes if c["new"] > c["old"]),
            "price_decreases": sum(1 for c in price_changes if c["new"] < c["old"]),
            "compare_at_changes": len(compare_changes),
            "sales_started": sale_started,
            "sales_ended": sale_ended,
            "availability_changes": len(stock_changes),
        },
        "new_products": first([{"title": p["title"], "price_from": min(
            [v["price"] for v in p["variants"].values() if v["price"] is not None], default=None)} for p in added]),
        "removed_products": first([{"title": p["title"]} for p in removed]),
        "price_changes": first(sorted(price_changes, key=lambda c: abs(c["change_pct"] or 0), reverse=True)),
        "compare_at_changes": first(compare_changes),
        "availability_changes": first(stock_changes),
    }
    if old.get("capped") or new.get("capped"):
        result["warning"] = ("At least one snapshot was capped, so some 'new' or 'removed' products may only "
                             "have moved in or out of the part of the catalog that was read.")
    return result


def handle_tracking(store_out, products, capped, args, now):
    if not products:
        store_out["track"] = {"status": "no snapshot: product data not available"}
        return
    snap = snapshot_of(products, store_out["origin"], capped, now)
    host = urllib.parse.urlsplit(store_out["origin"]).netloc
    folder = Path(args.snapshot_dir).expanduser() / host
    previous_path = None
    if args.previous:
        previous_path = Path(args.previous).expanduser()
    elif folder.is_dir():
        older = sorted(folder.glob("*.json"))
        previous_path = older[-1] if older else None
    track = {}
    if previous_path:
        try:
            old = json.loads(previous_path.read_text(encoding="utf-8"))
            if old.get("store") and urllib.parse.urlsplit(old["store"]).netloc != host:
                track["previous_ignored"] = f"{previous_path} is a snapshot of a different store"
            else:
                track["diff"] = diff_snapshots(old, snap)
                taken = parse_time(old.get("taken_at"))
                if taken:
                    track["diff"]["hours_since_previous"] = round((now - taken).total_seconds() / 3600, 1)
                track["previous_snapshot"] = str(previous_path)
        except (OSError, ValueError, KeyError) as err:
            track["previous_ignored"] = f"could not read {previous_path}: {err}"
    else:
        track["first_run"] = "No previous snapshot found. Run again later to see what changed."
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (now.strftime("%Y-%m-%dT%H%M%SZ") + ".json")
    path.write_text(json.dumps(snap, separators=(",", ":")), encoding="utf-8")
    track["snapshot_saved"] = str(path)
    store_out["track"] = track


# ------------------------------------------------------------------------ main

def bfcm_dates(today):
    """Black Friday is the day after US Thanksgiving (fourth Thursday of November)."""
    for year in (today.year, today.year + 1):
        nov1 = dt.date(year, 11, 1)
        thanksgiving = nov1 + dt.timedelta(days=(3 - nov1.weekday()) % 7 + 21)
        black_friday = thanksgiving + dt.timedelta(days=1)
        cyber_monday = black_friday + dt.timedelta(days=3)
        if cyber_monday >= today:
            return {"black_friday": black_friday.isoformat(), "cyber_monday": cyber_monday.isoformat(),
                    "days_until_black_friday": (black_friday - today).days}
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only public teardown of competitor stores.")
    ap.add_argument("urls", nargs="+", help="1 to 3 competitor store URLs")
    ap.add_argument("--own", help="your own store URL, for Compare mode")
    ap.add_argument("--track", action="store_true", help="save a dated snapshot and diff against the previous one")
    ap.add_argument("--snapshot-dir", default="competitor-snapshots", help="where Track snapshots are kept")
    ap.add_argument("--previous", help="explicit previous snapshot file (one competitor only)")
    ap.add_argument("--max-pages", type=int, default=4, help="product pages of 250 to read (max 4)")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests (min 1)")
    ap.add_argument("--max-wait", type=int, default=30, help="longest Retry-After wait to honor once, in seconds")
    args = ap.parse_args(argv)
    if len(args.urls) > 3:
        ap.error("at most 3 competitor URLs")
    if args.previous and len(args.urls) > 1:
        ap.error("--previous works with one competitor URL only")
    args.max_pages = max(1, min(args.max_pages, 4))
    args.delay = max(1.0, args.delay)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    report = {"tool": "junifia competitor-teardown", "tool_version": VERSION,
              "generated_at": now.isoformat(), "bfcm": bfcm_dates(now.date()), "stores": []}
    targets = [(u, "competitor") for u in args.urls] + ([(args.own, "own")] if args.own else [])
    for url, role in targets:
        print(f"Reading {url} ...", file=sys.stderr)
        try:
            result = analyze_store(url, role, args, now)
        except Exception as err:  # one bad store must not sink the others
            report["stores"].append({"input_url": url, "role": role, "confidence": "none",
                                     "data_notes": [f"Unexpected error while reading this store: {err}"]})
            continue
        store_out, products, capped = result
        if args.track and role == "competitor":
            handle_tracking(store_out, products, capped, args, now)
        report["stores"].append(store_out)
    json.dump(report, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
