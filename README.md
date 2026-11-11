# Junifia Skills for Shopify

Free skills that turn Claude into a helpful second pair of eyes for your Shopify store. Ask a question in plain English, get a plain-language report or a ready-to-paste draft back. No code, no setup beyond a click or two.

**Every skill is read-only.** It looks at stores, it never changes them.

<!-- Demo GIF placeholder: record a skill run, save it as docs/demo.gif, then uncomment the line below. -->
<!-- ![Demo](docs/demo.gif) -->

## Skills

### Store audits (`shopify-audits`)

| Skill | What it does | Status |
|---|---|---|
| **competitor-teardown** | Reads up to 3 competitors' public storefronts and tells you how they price, discount, merchandise and ship, which apps they run, and their return terms. Ends with 3 things to copy and 1 gap to exploit. Can compare them side by side with your store, or track their price and sale changes over time (great before and during Black Friday). | Available |
| **cro-audit** | Finds where shoppers drop off between landing and checkout, and what to fix first. | Coming soon |
| **agentic-readiness** | Checks whether AI shopping assistants can find, understand and recommend your products. | Coming soon |

### Black Friday and Cyber Monday kit (`bfcm`)

| Skill | What it does | Status |
|---|---|---|
| **readiness-audit** | Checks your store and gives you a red, yellow, green report: stock on your best sellers, empty or broken collections, store policies, images and alt text, checkout basics. Ends with a short "fix these first" list. | Available |
| **offer-planner** | Recommends the right type of BFCM offer for your margins, shows the math, and warns you before a sitewide discount eats your profit. | Coming soon |
| **email-sequence** | Drafts your teaser, launch, reminder, last chance and Cyber Monday emails, plus SMS, using your real products. | Coming soon |
| **war-room** | A launch-day runbook: what to check every hour, and what to do if a product sells out or a discount stops working. | Coming soon |

### Try it

Once installed, just ask:

> Do a competitor teardown of northwindcoffee.com

> Compare my store mystore.com to these two competitors: ...

> Track northwindcoffee.com's prices through Black Friday

> Is my store ready for Black Friday?

## How skills see your store

For skills about your own store, you choose how much access to give:

1. **Connected store (best results).** Connect Shopify in Claude under Settings > Connectors. The skill can then see your real sales and stock levels.
2. **A CSV export.** Export your products (and optionally orders) from your Shopify admin and upload the file. The skill will tell you exactly which buttons to click.
3. **Just your store's web address.** The skill reads your public storefront. Lighter, but needs nothing from you.

The competitor teardown only uses public pages, the same ones any shopper can see.

## Install

### In Claude.ai (web, desktop or mobile)

1. Download the skill you want from the [`dist`](dist) folder, for example [`competitor-teardown.zip`](https://github.com/junifia/skills/raw/main/dist/competitor-teardown.zip).
2. In Claude, open **Settings > Capabilities** and make sure code execution is turned on.
3. Under **Skills**, click **Upload skill** and choose the zip file.
4. Start a new chat and ask your question.

The competitor teardown reads other websites. If your Claude.ai code environment does not allow internet access, it falls back to a lighter method and says so in the report. For the full version, use Claude Code.

### In Claude Code

```
/plugin marketplace add junifia/skills
/plugin install shopify-audits@junifia
/plugin install bfcm@junifia
```

Then ask your question in any session.

## Good to know

- **Read-only, always.** The skills never edit products, discounts, collections or settings, even when connected to your store. When something needs fixing, they tell you where to click.
- **Polite with other sites.** The competitor teardown follows each site's robots.txt rules, reads at most 15 pages per store with a pause between each, and stops if a site says no. It never logs in or gets around a block.
- **Evidence, not guesses.** Numbers in reports are computed from data the skill actually read. When something can't be found, the report says "not detected" and why.
- **Your data stays in your conversation.** Nothing about your store is sent anywhere except to Claude, in the chat you are already using.
- **Not legal or financial advice.** Reports point out likely problems and opportunities. You make the call.

## Contributing

Found a bug, a wrong suggestion, or have an idea for a skill? [Open an issue](https://github.com/junifia/skills/issues). See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)

---

Built by [Junifia](https://junifia.ca). Want help acting on this? [junifia.ca](https://junifia.ca)
