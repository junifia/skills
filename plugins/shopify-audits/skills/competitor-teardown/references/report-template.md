# Report template

How to turn the script's JSON into the report. Examples use a fictional store, "Northwind Coffee".

## Reading the JSON

Each entry in `stores` is one store. `role` is `competitor` or `own`.

| Field | Meaning | Watch out for |
|---|---|---|
| `bfcm` | This year's Black Friday and Cyber Monday dates, days until Black Friday | Use these dates, do not compute your own. |
| `platform.type` | `shopify_online_store`, `shopify_headless_or_custom` (Shopify behind a custom front end), `not_shopify`, `shopify_password_protected`, `unknown` | Headless and non-Shopify stores have no catalog data. Say so once, do not repeat "not detected" in every section. |
| `platform.theme.base_theme` | The theme the store is built on (for example Dawn). `name` is what the store called its copy. | No base theme, or a base theme that carries the store's own name or an unfamiliar code name, usually means a custom-built theme. Say "custom-built theme" rather than guessing. |
| `store` | Name, currency, country, how many products and collections the store says it publishes | `published_products_count` is the store's own total and can be higher than what was read. |
| `catalog.capped` | True when only the first 1,000 products were read | Then every catalog number describes those products, not the whole store. Say it in the snapshot. |
| `catalog.product_types.top` | Main product types with count and `share` (percent of products read) | |
| `catalog.tags` | Tag counts | Do not report tags. Stores use them for internal filters, so they rarely mean what they say. |
| `catalog.price` | Lowest variant price per product: min, p25, median, p75, max, and bands | "Half their products cost under {median}." |
| `catalog.discounts` | Share of products with a compare-at price above the price, median and max discount | Read `deep_discount_outliers`: 70%+ off is often a subscription or multi-pack value, not a real sale. Mention it if outliers exist. |
| `catalog.variants` | Variants per product, share of variants sold out, fully sold-out products | A high sold-out share can mean stock problems or a deliberate "limited drop" model. Present the number, do not assume which. |
| `catalog.new_products` | Products created or published in the last 30 and 90 days | Prefer `created_*` for "new launches". |
| `catalog.bundles` | Titles that look like bundles, kits, sets or packs | Always call it "products that look like bundles (based on their names)". |
| `collections.capped` | True when only the first 250 collections were read | Mention it in Data notes. |
| `collections.sale_or_seasonal` | Collections with sale, holiday, gift or Black Friday style names, with their publish date | Publish dates show when past campaigns went live. Product counts can include hidden products, so do not quote them as visible counts. |
| `best_sellers` | The store's own "best selling" order, when allowed | Usually `not detected` because Shopify stores' robots.txt asks tools not to read sorted pages by default. Say that plainly, once. |
| `merchandising` | Announcement bar lines, collections linked from the homepage, promo phrases found | Promo phrases are what the homepage says today, with the line they came from. The announcement list can also catch hero banner text: quote only lines that read like an offer or message. |
| `apps.detected` | Apps whose code loads on the homepage, with evidence | Not detected does not mean not used. |
| `policies` | Shipping and refund policy: found, not detected, not read (hosted on another site), with source. `first_try` says why the standard page did not work. | Very short policies (under about 50 `words`) are worth a mention: shoppers get few details. |
| `store.ships_to_countries_count`, `store.shop_pay_installments` | How many countries the store ships to, and whether it offers Shop Pay Installments (pay later) | Put them under Trust and policies. |
| `free_shipping` | Threshold and where it was found | `free shipping mentioned, no threshold detected` means the words appear without a clear amount. If the evidence also shows a temporary free shipping code, mention both. |
| `return_window` | Days, or `no returns stated`, plus `terms` such as free returns, final sale, return fee | Quote the evidence only as a short phrase. |
| `track.diff` | Changes since the previous snapshot. `hours_since_previous` says how long ago that was. | Read `warning` if present. Under 24 hours, say that little time has passed, so few changes are expected. |
| `track.snapshot_saved` | Where today's snapshot was saved | Tell the merchant the folder and file name in plain words. |
| `confidence` | `high`, `medium`, `low`, `none` | Show it in the snapshot table. |
| `data_notes` | Everything that was blocked, capped, skipped or missing | Goes into the Data notes section, in plain words. |
| `homepage_thin` | The homepage returned almost nothing (bot check or JavaScript-only page) | Treat homepage findings (apps, promos, announcement) as incomplete. Do not call it a block: the store answered, it just showed little. |
| `data_notes` mentioning "sent visitors to" | The site redirected to another address, often a regional store | Say which store the results describe (for example the US store). |
| `storefront` | The exact storefront that was read, including a regional path such as `/en-ca` | When it has a regional path, say in the snapshot which region the prices and policies are for. |
| `page_language` | The language the store's homepage declares | Used to pick the report language for the merchant's own store. Not a finding. |
| `input_product` | The product page the merchant pasted: name, price range, currency, availability counts from the page's product data, promo lines, and `catalog` facts when the product was also in the product list | Put it first in Offer and pricing ("The product you asked about..."). `structured_data: not detected` means the page had no machine-readable price, so do not state one. |
| `fetch_error` | `network`: this environment could not connect to the store | Not a block by the store. Switch to the fallback in SKILL.md for this store. |

## Report structure (Teardown)

```
# Competitor teardown: {store name or domain}

{If fallback mode: **Lower confidence: partial data.** One line on why.}

## Snapshot
| | |
|---|---|
| Platform and theme | Shopify, Dawn theme |
| Products | 165 (all read), or 1,828 (first 1,000 read) |
| Price range | $5 to $90, half cost $29.98 or less |
| On sale right now | 16% of products, typically about 29% off |
| Free shipping | Over $50 (announcement bar) |
| Returns | 30 days, free exchanges (if no window: the terms found, for example "$10 returns, free exchanges, 30%+ off is final sale") |
| Data read on | November 9, 2026 |
| Confidence | High |

## Offer and pricing
3 to 5 bullets: price positioning (median, bands), how much is discounted and how deep, sale or seasonal collections and when they went live, promo lines on the homepage today.

## Catalog strategy
3 to 5 bullets: size of catalog, main product types and their share, variants per product, sold-out share, new launches in the last 30 and 90 days, products that look like bundles.

## Merchandising
2 to 4 bullets: announcement bar offers, what the homepage pushes (collections linked from it), best sellers if detected.

## Tech stack
Theme, then detected apps grouped by the category given in the script output, with one plain line on what that kind of app does (based on the category name only, no claims about how this store uses it). End with: "Apps that load only on product or cart pages are not detected."

## Trust and policies
Shipping policy, free shipping threshold, return window and terms, anything notable (no returns, final sale rules, money-back guarantee).

## 3 things to copy
1. **{Short action for the merchant}.** {The data point that shows it, in one sentence.} {Why it works, in one sentence.}
2. ...
3. ...

## 1 gap to exploit
**{Short action}.** {The data point.} {How the merchant can use it.}

## Data notes
- What was read and when.
- Anything blocked, capped, skipped or not detected, with the reason in plain words.
- Confidence level and why.

{When several stores are in one answer, repeat the sections above for each store, separated by a horizontal rule. The lines below appear once, at the very end.}

{Optional one-sentence next step (see "When it is BFCM season" in SKILL.md).}

Built by Junifia. Want help acting on this? junifia.ca
```

## Compare mode

Title: `# Competitor comparison: {your store} vs {competitor names}`.

Start with a side-by-side table, own store first:

```
## Side by side
| | Your store | Northwind Coffee | ... |
|---|---|---|---|
| Products | ... | ... | |
| Median price | ... | ... | |
| On sale now | ... | ... | |
| Typical discount | ... | ... | |
| Free shipping | ... | ... | |
| Returns | ... | ... | |
| New products, last 90 days | ... | ... | |
| Sold-out variants | ... | ... | |
| Apps detected | ... | ... | |
| Confidence | ... | ... | |
```

If the stores sell different kinds of products, say so in one line under the table: the comparison shows positioning, not a like-for-like price match.

Then a short `## About your store` section (3 bullets max) for anything notable about the merchant's own data, such as deep discount outliers that make their sale numbers misleading, or a missing free shipping amount.

Then one `##` section per competitor with bold labels (Offer and pricing, Catalog, Merchandising, Tech stack, Trust and policies, 3 bullets max each). Say the "apps on other pages" caveat once under the table, not in every section. Then "3 things to copy" and "1 gap to exploit" across all competitors, written for the merchant's store. When several gaps qualify, pick the one where the merchant's own store is strongest against the most competitors. Then Data notes for every store, with each store's confidence.

## Track mode

Start with:

```
## What changed since {previous snapshot date}
| | Count |
|---|---|
| New products | ... |
| Removed products | ... |
| Price increases | ... |
| Price decreases | ... |
| Sales started | ... |
| Sales ended | ... |
| Compare-at price changes | ... |
| Back in stock or sold out | ... |
```

Then list the most notable changes (biggest price moves, new products with prices, sales started) in plain sentences. If `track.diff.warning` is present, say it. On a first run, say there is nothing to compare yet and when to run it again. Then continue with the normal Teardown sections, shortened to the essentials.

## Phrasing

- Lead with the takeaway, then the number: "Most of their range is affordable: half their products cost $29.98 or less."
- The range from p25 to p75 is "the middle half" of their products, not "most".
- Round shares to whole percents everywhere (prose and tables), halves round up. Prices: drop a trailing ".0" ($90, not $90.0), keep real cents ($29.98).
- Report numbers without labels like "healthy", "patchy", "strong" or "weak" unless the template asks for an interpretation. Let the merchant judge.
- When 0% of products have a compare-at price but the homepage promotes discount codes (`promo_phrases`), say "no crossed-out sale prices; discounts run through codes", with the promo line as evidence.
- Say "not detected" with the reason, never "they don't have": "No free shipping offer detected on their homepage or shipping policy."
- Do not repeat the same caveat in several sections. Put it once where it matters and once in Data notes.
- No em dashes. Use commas, parentheses or a new sentence.
- In a report that is not in English, these rules still apply, translated. Use the number format of that language (for example "29,98 $" in French) and keep the closing line in English.
