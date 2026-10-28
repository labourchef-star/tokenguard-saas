# Funnel done — Loop Stop retail

**When:** 2026-10-28 (Pacific/Auckland)  
**Path:** `/workspace/grok-dev/loop-stop-retail/`

## Routes (app on :8788)

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8788/` | Marketing landing (in-app) |
| `http://127.0.0.1:8788/signup` | Create local account → `/download` |
| `http://127.0.0.1:8788/signin` | Sign in → `/integrations` |
| `http://127.0.0.1:8788/download` | Zip + install steps |
| `http://127.0.0.1:8788/download/zip` | Serve release zip |
| `http://127.0.0.1:8788/integrations` | Grok / Claude Code / OpenAI-compatible (auth) |
| `http://127.0.0.1:8788/app` (alias `/dashboard`) | Impact dashboard + Demo |
| `http://127.0.0.1:8788/account` | Account stub |
| `http://127.0.0.1:8788/v1/*` | Proxy (unchanged) |
| `http://127.0.0.1:8788/api/impact` | Impact JSON |
| `http://127.0.0.1:8788/api/demo/seed` | Simulated seed |

## Auth (local only)

- SQLite `users` + `auth_sessions` + `user_settings`  
- Passwords: PBKDF2-SHA256 (stdlib)  
- Session: httpOnly cookie `loop_stop_session`  
- API keys: opaque local obfuscation; never logged; masked in API  
- No internet required for signup  

## How to test signup → integrations → demo

```bash
./run.sh   # http://127.0.0.1:8788/

# Browser: / → Sign up → Download → Integrations → Demo
# Or curl:
EMAIL=you@local.test
curl -c /tmp/ls.txt -X POST http://127.0.0.1:8788/api/auth/signup \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"testpass123\",\"name\":\"You\"}"
curl -b /tmp/ls.txt http://127.0.0.1:8788/api/integrations
curl -X POST 'http://127.0.0.1:8788/api/demo/seed?replay=true'
curl -s http://127.0.0.1:8788/api/impact | jq .pct_waste_reduction_est
# expect 75.0
```

## Smoke checklist (2026-10-28)

| Check | Result |
| --- | --- |
| GET `/` landing | 200 |
| GET `/signup` `/signin` `/integrations` `/download` `/app` | 200 |
| POST `/signup` → 303 `/download` + session cookie | OK |
| GET `/api/auth/me` | signed-in user |
| POST `/api/integrations` grok key | masked, `grok_key_set: true` |
| POST `/api/demo/seed` | 3 simulated sessions |
| Impact `%` waste reduction (est.) | **75.0** |
| GET `/v1/models` | grok-4.7 |
| Download zip available | yes (`dist/…v0.1.0.zip`) |
| Proxy/dashboard unbroken | OK |

## Public marketing

| Path | Role |
| --- | --- |
| `marketing-site/` | Static site for Netlify/Pages/Gumroad paste |
| `marketing/ANGLES.md` | 8 pattern-interruption angles |
| `marketing/FUNNEL.md` | Full funnel diagram |
| `marketing/copy/*` | Heroes, signup microcopy, email 3-touch, social |
| `results/PUBLIC_LAUNCH.md` | HOST=0.0.0.0 vs Gumroad options |

## Still human

Real XAI key · Gumroad/GitHub/Anthropic publish · paid ads · Postiz · public TLS domain
