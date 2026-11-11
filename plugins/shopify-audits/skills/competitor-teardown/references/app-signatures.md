# App signatures

Used by `scripts/teardown.py` to detect apps on a store's homepage. The script reads the table below directly, so this file is the single source of truth.

How detection works:

- The script looks only at code on the homepage: script and stylesheet addresses, inline scripts, and element class names. Visible text is ignored, so a blog post that mentions an app does not count.
- A match is evidence that the app's code is loaded on the homepage. Report the app with the matched signature as evidence.
- No match does not mean the store does not use the app. Some apps only load on product pages, in the cart, or after the page has finished loading. Say "not detected on the homepage", never "does not use".

To add an app, add a row. Signatures are lowercase text in backticks, separated by commas. Prefer the app's own script or CDN domain, which is specific and rarely appears by accident.

| App | Category | Signatures |
|---|---|---|
| Klaviyo | Email and SMS marketing | `static.klaviyo.com`, `static-tracking.klaviyo.com`, `klaviyo.com/onsite` |
| Omnisend | Email and SMS marketing | `omnisnippet1.com`, `omnisrc.com`, `omnisend.com` |
| Privy | Pop-ups and email capture | `privy.com` |
| Attentive | SMS marketing | `attn.tv`, `attentivemobile.com` |
| Postscript | SMS marketing | `postscript.io` |
| Judge.me | Product reviews | `judge.me`, `judgeme`, `jdgm-` |
| Yotpo | Reviews and loyalty | `yotpo.com` |
| Okendo | Product reviews | `okendo.io` |
| Loox | Photo reviews | `loox.io` |
| Stamped | Reviews and loyalty | `stamped.io` |
| Rebuy | Upsells and personalization | `rebuyengine.com` |
| ReCharge | Subscriptions | `rechargecdn.com`, `rechargepayments.com`, `rechargeapps.com` |
| Bold | Subscriptions and pricing tools | `boldapps.net`, `boldcommerce.com` |
| Gorgias | Customer support chat | `gorgias.chat`, `gorgias.io` |
| Smile.io | Loyalty and rewards | `smile.io`, `sweettooth.io` |
