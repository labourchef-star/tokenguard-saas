# TokenGuard — market live status

**Updated:** 2026-10-28 17:11 Pacific/Auckland (UTC+13)

## Product

| Field | Value |
| --- | --- |
| Display name | **TokenGuard** |
| Subtitle | Coding Agent Token Guard |
| Version | 0.1.0 |
| Price | **$19** (1900 USD cents) |
| Zip | `/workspace/grok-dev/loop-stop-retail/dist/tokenguard-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip` (~296 KiB) |

## Gumroad

| Field | Value |
| --- | --- |
| Short URL | https://labourchef.gumroad.com/l/tokenguard |
| Permalink | `tokenguard` |
| Product id | `myj0lqRCvm3YcbWqkstXdA==` |
| Published | **false** (draft) |
| Enable blocker | `You must connect at least one payment method before you can publish this product for sale.` |

File upload + product create succeeded via API. `PUT /v2/products/:id/enable` failed for missing payout method. Draft listing URL still resolves for preview; sales need a connected payment/payout method in the Gumroad seller account (`labourchef`).

No leftover "TokenGuard probe" products found.

## Netlify marketing landing

| Field | Value |
| --- | --- |
| Site URL | https://lively-pithivier-ef47f9.netlify.app/ |
| Password | `[REDACTED]` |
| Site id | `b8b591a5-bea3-4ce3-ad2c-220e9d813e43` |
| Claim (browser) | https://app.netlify.com/drop/lively-pithivier-ef47f9#drop_token=[REDACTED] |
| Claim (CLI) | `netlify claim --site b8b591a5-bea3-4ce3-ad2c-220e9d813e43 --token [REDACTED]` |

Anonymous Drop deploy — **claim within 60 minutes** or the site can expire.

Live checks: brand = TokenGuard; primary CTAs → Gumroad URL via `config.js`; footer no longer says “not on Gumroad yet”; FAQ = buy on Gumroad → unpack → `./install.sh` → `http://127.0.0.1:8788`.

## What the buyer does

1. Open Gumroad (or Netlify CTA) → buy TokenGuard ($19 once published).
2. Download `tokenguard-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip`.
3. Unpack → `./install.sh` → open `http://127.0.0.1:8788`.
4. Connect Integrations (Grok / Claude Code / OpenAI-compatible) or try Demo mode (~75% est. waste reduction, **simulated**).

## Remaining human-only

1. **Gumroad payout / payment method** — connect so `enable` succeeds and `published=true`.
2. **Claim Netlify** site (link above) before the anonymous Drop expires.
3. Anthropic directory / Claude marketplace public listing — optional later.
4. GitHub Release of the same zip — optional later.
5. Ads — **still frozen**; do not touch Adspirer.

## Honest marketing notes

- Local-first, not hosted SaaS.
- Savings labeled **estimate** unless provider returns usage.
- Demo ~75% is **simulated** FakeAgent sessions ($0).
- No invented metrics beyond that known demo.
