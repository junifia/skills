# Gathering data

How to collect what the audit needs in each mode. Everything here is read-only. If a step would change the store, skip it.

## What you need (all modes)

| Data | Used for |
|---|---|
| Store name, currency, primary domain, markets or countries sold to | Report header, money formatting, shipping check |
| Active products with variants: title, price, stock, "continue selling when out of stock" setting, status | Stock check |
| Product images and their alt text | Images check |
| Sales by product for the last 90 days (and last year's BFCM week if available) | Top products and stock forecast |
| Collections: title, product count, published or not, how many products are available | Collections check |
| Main menu and footer menu links | Broken links check |
| Policies: refund, shipping, privacy, terms of service, contact information | Policies check |
| Password protection, payment setup, shipping zones, active discounts | Checkout check |

Collect only what you need. On large stores, fetch top products in full and use counts for the rest.

## Mode A: Connected store

Use whatever read tools the connected Shopify connector or MCP server offers. Tool names differ between connectors, so match by purpose:

- **Shop info** tool for name, currency, domain, contact email.
- **Product search or product lookup** tools for products, variants, images.
- **Inventory** tools for stock per variant and location.
- **Collection search or lookup** tools for collections and their products.
- **Orders or analytics** tools for sales by product. If an analytics query tool exists, ask it for net sales and units sold per product over the last 90 days, and separately for last year's Black Friday to Cyber Monday week.
- **Read-only GraphQL query** tool, if one exists, for anything else (policies, menus, discounts, shipping zones, payment settings). Look up the schema first, request only the fields you need, and paginate. Only ever run queries. Never run a mutation, even if the tool allows it.

Do not use any tool that writes, even "harmless" ones such as creating a draft, a tag or a test discount.

If a specific item is not available through the connector (for example payment settings), mark that finding "Not checked" and move it to the self-test.

## Mode B: CSV export

Walk the merchant through the export in plain steps. Ask only for the files you need.

**Products export (needed):**
1. In your Shopify admin, go to **Products**.
2. Click **Export** (top right).
3. Choose **All products** and **CSV for Excel, Numbers, or other spreadsheet programs**.
4. Click **Export products**. Small stores download right away. Larger stores get the file by email.
5. Upload the file here.

**Inventory export (recommended if the store has more than one location):**
Products > Inventory > Export. This gives stock per location.

**Orders export (recommended, for top sellers):**
Orders > Export > choose "Orders by date" and pick the last 90 days. If the store was open last November, a second export for last year's Black Friday to Cyber Monday week is very useful.

Reading the files:

- **Products CSV.** One row per variant. Rows with the same `Handle` belong to the same product. The first row of a product holds the title, status and description. Extra rows may hold more variants or only an extra image (`Image Src`, `Image Position`, `Image Alt Text`). Useful columns: `Title`, `Handle`, `Status`, `Published`, `Variant SKU`, `Option1 Value` (and 2, 3), `Variant Price`, `Variant Compare At Price`, `Variant Inventory Tracker`, `Variant Inventory Qty`, `Variant Inventory Policy` (`continue` means it keeps selling at zero stock), `Image Src`, `Image Alt Text`, `Variant Image`. Column names change over time, so match loosely by meaning.
- **Inventory CSV.** One row per variant per location, with available and on-hand quantities.
- **Orders CSV.** One row per line item. Use `Created at`, `Lineitem name`, `Lineitem quantity`, `Lineitem price`, `Lineitem sku` and `Financial Status` (skip refunded or voided orders). Group by product to find top sellers and daily sales rates.

CSV files cannot show policies, menus, payments or shipping. If the merchant also gives the store URL, use Mode C for those. Otherwise mark them "Not checked" and include the self-test.

Never repeat customer names, emails, addresses or phone numbers from an orders export in the report.

## Mode C: Store URL only

Use a web fetch or browsing tool if one is available. If none is, tell the merchant you need a connected store or a CSV export and stop there.

Be polite to the store's server: fetch only what you need, and no more than a few dozen pages in total.

Public places to look (on the store's own domain):

| URL | What it gives |
|---|---|
| `/` | Whether the store is password protected (redirects to `/password`), main menu and footer links |
| `/products.json?limit=250&page=1` (then page 2, 3 ...) | Products, variants, prices, whether each variant is available, image URLs |
| `/products/{handle}.js` | One product with media alt text and variant availability |
| `/collections.json?limit=250&page=1` | Collections and their product counts |
| `/collections/{handle}/products.json?limit=250` | Products in one collection, with availability |
| `/collections/all?sort_by=best-selling` | Best-selling order, if the theme supports it |
| `/policies/refund-policy`, `/policies/shipping-policy`, `/policies/privacy-policy`, `/policies/terms-of-service`, `/policies/contact-information` | Policy pages |

Limits of this mode, to state in the report:

- Stock shows only as available or sold out, not how many units are left. Mark the stock forecast "Not checked" and only report what is already sold out.
- There is no sales data. Top products come from the merchant or the best-selling sort.
- Some stores block the `.json` addresses. If so, read the normal HTML pages instead and say the check was lighter.
- Payments, shipping rates and discounts are not visible. Use the self-test.
