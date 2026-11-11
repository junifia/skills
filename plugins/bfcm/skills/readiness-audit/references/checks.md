# Checks and scoring rules

Apply these rules as written so results are consistent. When a rule does not fit a situation, use judgment and explain the call in one sentence in the report.

"Top products" means the list built in Step 2 of SKILL.md.

## 1. Stock on top products

### Forecast

For each variant of each top product (or the product itself if it has no variants):

1. **Daily sales rate.** Units sold in the last 30 days divided by 30. If fewer than 10 units sold in 30 days, use the last 90 days divided by 90 instead.
2. **Stock on Black Friday morning.** Current available stock minus (daily rate times days until Black Friday). Add any restock the merchant tells you is arriving before then. Ask once: "Do you have any restocks arriving before Black Friday?"
3. **Expected BFCM demand** (Black Friday to Cyber Monday, 4 days):
   - If the store has last year's BFCM sales for this product, use those units. If overall sales grew or shrank since then, adjust by the same percentage and say so.
   - Otherwise, use daily rate times 4 days times 3. The "times 3" assumes a BFCM day sells about three times a normal day. Say this assumption in the report and suggest raising it to 5 if the merchant plans a big discount or a large email send.
4. **Coverage** = stock on Black Friday morning divided by expected BFCM demand.

### Rules

| Status | When |
|---|---|
| 🔴 | A top product or one of its main variants is already sold out. Or coverage is under 50%. Or stock is at or below zero while "continue selling when out of stock" is on and the merchant has not said this is on purpose (pre-orders). |
| 🟡 | Coverage between 50% and 100%. Or "continue selling when out of stock" is on for a top product (risk of selling stock you do not have). Or stock is not tracked for a top product, so Shopify cannot stop overselling. Or one size or color of a top product is sold out while others are not. |
| 🟢 | Coverage of 100% or more, stock is tracked, and overselling is off (or on by choice for pre-orders). |
| ⚪ | No stock numbers available (for example Mode C). Still report anything already sold out as 🔴. |

Report each red or yellow variant with: current stock, daily rate, projected stock on Black Friday, expected BFCM demand, and the number of units short. Round to whole units.

**Bonus tip (no status):** if any active product has more than 180 days of stock at its current rate, list up to 5 of them as "good candidates for a BFCM offer, since you have plenty". Helpful for planning the offer.

**How to fix:** reorder or move stock between locations (Products > Inventory), or remove a nearly sold-out product from BFCM emails and ads. To turn off overselling: Products > open the product > open the variant > Inventory > untick "Continue selling when out of stock". To track stock: same place, tick "Track quantity".

## 2. Collections

Check every published collection, plus every collection or page linked from the main menu, footer menu and homepage.

| Status | When |
|---|---|
| 🔴 | A collection linked from the main menu or homepage is empty, has every product sold out or hidden, or the link leads to a "page not found". A main menu link of any kind leads to a "page not found". |
| 🟡 | A published collection has no products (even if not linked, shoppers can reach it from search or old links). A collection linked from anywhere has more than half its products sold out. A footer link leads to a "page not found". An automated (smart) collection matches zero products, which usually means its conditions are wrong. |
| 🟢 | Linked collections have available products and all menu links work. |

Ignore unpublished collections, but mention how many exist in one line if more than 5 are empty (tidy-up tip, no status).

**How to fix:** Products > Collections > open the collection to add products or fix conditions. For menu links: Content > Menus (in some admins: Online Store > Navigation) > open the menu > edit or remove the link.

## 3. Policies

Look for: refund policy, shipping policy, privacy policy, terms of service, contact information.

| Status | When |
|---|---|
| 🔴 | Refund, shipping or privacy policy is missing or empty. Any policy still contains template placeholders such as text in square brackets ("[INSERT ...]", "[your email]"), "XX days", or "lorem ipsum". |
| 🟡 | Terms of service or contact information is missing. Refund policy says nothing about holiday purchases (many stores extend returns on November and December orders into January). Shipping policy gives no processing time or no holiday order cut-off date. Policies are not linked in the store footer. |
| 🟢 | All five exist, are filled in, and the refund and shipping policies give clear time frames. |

Do not give legal advice. If something looks legally sensitive, suggest the merchant checks it with someone qualified in their country.

When useful, include a **ready-to-paste sentence** the merchant can add, written in the store's tone, for example a holiday returns line ("Orders placed between November 1 and December 24 can be returned until January 15.") or a holiday shipping cut-off line. Mark the dates as ones they should adjust.

**How to fix:** Settings > Policies. Shopify can generate a starting template, but the merchant must replace every placeholder. To add footer links: Content > Menus > Footer menu.

## 4. Images and alt text

Alt text is a short written description of an image. Screen readers read it aloud to people who cannot see the image, and search engines use it to understand the product.

| Status | When |
|---|---|
| 🔴 | A top product has no image at all. |
| 🟡 | A top product has only one image. Any top product image is missing alt text. More than 25% of all product images in the store are missing alt text. A top product has color options but no image linked to each color, so shoppers cannot see what they are picking. |
| 🟢 | Every top product has at least two images, and they all have alt text. |

For top products missing alt text, include **suggested alt text** for each image (up to 10 products), built from the product title, the variant and the image position, for example "Classic hoodie in black, front view". Keep each under 125 characters, describe what is in the picture, and do not start with "Image of". Say these are starting points to adjust if the picture shows something different.

For the rest of the store, give counts only ("142 of 380 images have no alt text").

**How to fix:** Products > open the product > click an image > "Add alt text". Shopify also offers bulk editing for many products at once (Products > select products > Bulk edit).

## 5. Checkout basics

Check what the data allows. Anything that cannot be checked goes into the self-test.

| Status | When |
|---|---|
| 🔴 | The store is password protected (shoppers cannot buy). No payment method is active. No shipping rate covers a country where the store sells or where most orders go. An active top product has a price of zero by mistake. |
| 🟡 | No store contact email is set. An active product's "compare at" price is lower than or equal to its price (the sale price display will look wrong). Active discounts exist that could stack with or clash with the BFCM offer, for example an old code with no end date or an automatic discount on the same products. A BFCM discount is already scheduled but its start or end date does not cover Black Friday through the end of Cyber Monday in the store's time zone. |
| 🟢 | Store open, payments and shipping set up for the main markets, no clashing discounts found. |

**How to fix:** password, Online Store > Preferences > Password protection. Payments, Settings > Payments. Shipping, Settings > Shipping and delivery. Discounts, Discounts (end or edit old codes before BFCM). Contact email, Settings > General.

### 5-minute checkout self-test

Include the steps that cover what could not be checked from data. The merchant does this on their own phone.

1. Open your store in a private browser window on your phone. You should see the store, not a password page.
2. Add one of your top products to the cart and go to checkout.
3. Enter a real address in your main country. Check that shipping options show up with the prices you expect.
4. Try your BFCM discount code if you have made it. Then try a made-up code to check it is refused.
5. Check that the payment options you expect appear (cards, and express options like Shop Pay, Apple Pay or PayPal if you use them).
6. You can stop before paying. If you want to test the full flow, place a real order and refund it right after (Orders > open the order > Refund).
7. Check that abandoned checkout emails are turned on (Marketing > Automations). On BFCM these bring back a lot of sales.
