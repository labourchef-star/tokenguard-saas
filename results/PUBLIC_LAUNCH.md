# Public launch — options for strangers

**Product:** Loop Stop — Coding Agent Token Guard (local-first)  
**Status:** App funnel + marketing site ready locally. **Not** published to Gumroad / GitHub Releases / Anthropic. Bot did not spend money or run ads.

---

## Option A — Host the FastAPI app (recommended for “sign up anywhere”)

Anyone on the internet hits your VPS; accounts stay SQLite on that box (not multi-tenant SaaS billing).

```bash
# On a VPS you control:
export HOST=0.0.0.0
export PORT=8788
# optional: XAI_API_KEY=… for live proxy default
./run.sh
```

Put **HTTPS** in front (Caddy or nginx → `127.0.0.1:8788`).  
Point `marketing-site/config.js` `APP_ORIGIN` at `https://your-domain`.

| Pros | Cons |
| --- | --- |
| Real signup → download → integrations path | You operate a server; SQLite is single-node |
| Demo works without keys | No built-in billing / team seats |
| Same codebase | Harden auth before wide exposure (rate limits, backups) |

**Human next steps**

1. Provision VPS + DNS + TLS  
2. `HOST=0.0.0.0 ./run.sh` under systemd  
3. Deploy `marketing-site/` to Netlify/Pages with `APP_ORIGIN` set  
4. Rebuild zip: `./packaging/build_release.sh` so `/download/zip` serves current bits  
5. Optionally add rate limiting / fail2ban (not in v0.1)

---

## Option B — Gumroad paid zip + local accounts

Sell `dist/loop-stop-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip`. Buyers unpack, run locally, sign up on **localhost**.

| Pros | Cons |
| --- | --- |
| No always-on app host | Marketing CTAs must explain “download then open localhost” |
| Matches Money Engine local margin story | Signup on marketing site can’t create their local DB until they install |

**Human next steps**

1. Follow `packaging/gumroad.md` (do not publish from bot)  
2. Link Gumroad from `marketing-site/pricing.html`  
3. Keep Demo narrative honest (simulated 75%)

---

## Option C — Hybrid

Marketing site public → CTA “Buy zip” (Gumroad) **and** “Try hosted demo” (Option A read-only Demo).  
Live API keys only on buyer’s machine (Option B) or their own VPS.

---

## Still human (do not automate without explicit ask)

- [ ] Real `XAI_API_KEY` for live proxy demos  
- [ ] Gumroad product publish  
- [ ] GitHub Release upload  
- [ ] Anthropic / Claude plugin directory submit  
- [ ] Paid ads / Postiz publish  
- [ ] Custom domain + TLS for Option A  
- [ ] Edit `marketing-site/config.js` APP_ORIGIN for production  

## Already built

- App routes: `/` landing, `/signup`, `/signin`, `/download`, `/integrations`, `/app`, `/account`  
- Local auth (SQLite users + session cookie)  
- `marketing-site/` static public pages  
- `marketing/` angles + funnel + copy  
- Demo ~75% est. waste reduction (simulated)
