# junifia/skills

Public Claude Code plugin marketplace of free skills for Shopify merchants. Readers are non-technical, global, English speaking.

## Layout

- `.claude-plugin/marketplace.json`: marketplace `junifia`, one entry per plugin
- `plugins/<theme>/.claude-plugin/plugin.json`: one plugin per theme (`bfcm`, `shopify-audits`)
- `plugins/<theme>/skills/<skill>/SKILL.md`, with optional `scripts/` and `references/`
- `dist/<skill>.zip`: Claude.ai upload bundles, built by `python3 scripts/build-dist.py` (rebuild after any skill change; it also lints)
- `README.md` is the landing page; keep its skill table in sync with the plugins

## Rules for every skill

- Strictly read-only. Never modify a store, never call write tools or mutations, never add to cart or start checkout.
- Works with a connected Shopify store when relevant, with a fallback (CSV export or public store URL).
- Output is a plain-language report or ready-to-paste draft, never code.
- Evidence-based: every number comes from data that was fetched and computed by a script, not estimated by the model. Missing data is "not detected", never guessed.
- Scripts are Python standard library only, so they run anywhere without installs.
- Refer to connector actions by purpose ("the product search tool"), never by a hardcoded tool ID.
- Public web data: respect robots.txt, never bypass blocks, captchas or logins, keep request counts low with a delay, summarize instead of copying text or images.
- No em dashes anywhere in public text (the build fails on them).
- No internal references: pricing, service tiers, client names, internal tools or processes.
- Reports end with exactly: `Built by Junifia. Want help acting on this? junifia.ca`
- SKILL.md body under about 300 lines; details go in `references/`.
