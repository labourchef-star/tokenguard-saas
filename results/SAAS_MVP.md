# TokenGuard SaaS MVP

Built from `loop-stop-retail` → multi-tenant hosted SaaS under `/workspace/grok-dev/tokenguard-saas/`.

## One-click user path

1. Stranger opens public HTTPS URL (`PUBLIC_BASE_URL`)
2. **Sign up** (email + password) → session cookie → `/app` dashboard
3. Dashboard shows:
   - Personal OpenAI-compatible **base_url**: `{PUBLIC_BASE_URL}/v1`
   - **TokenGuard API key**: `tg_…` (generated on signup)
4. Optional: paste upstream provider key (xAI/OpenAI BYOK) on Integrations — Fernet-encrypted with `TOKENGUARD_SECRET`
5. Point Claude Code / Continue / OpenAI SDK: `base_url` + `Authorization: Bearer tg_…`
6. Demo mode works without provider key (simulated ~75% est. — honest labels)
7. Integrations page copy-paste snippets use **hosted** URL (not localhost)

## Routes

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/` | public | Landing |
| GET/POST | `/signup` | public | Signup form |
| GET/POST | `/signin` | public | Signin form |
| POST | `/signout` | session | Sign out |
| GET | `/app` `/dashboard` | public UI | Impact dashboard |
| GET | `/integrations` | UI | BYOK + snippets |
| GET | `/account` | UI | Profile + rotate key |
| GET | `/health` | public | `{ok, service: tokenguard-saas}` |
| POST | `/api/auth/signup` | public | JSON signup → cookie + credentials |
| POST | `/api/auth/signin` | public | JSON signin |
| GET | `/api/auth/me` | session | User + credentials |
| POST | `/api/auth/rotate-key` | session | New `tg_` key |
| GET/POST | `/api/integrations` | session | Encrypted BYOK |
| GET | `/api/credentials` | session | base_url + api_key |
| GET | `/api/impact` | session-scoped | Impact summary |
| GET | `/api/sessions` | session-scoped | Session list |
| POST | `/api/demo/seed` | optional session | Simulated demo |
| POST | `/v1/chat/completions` | `Bearer tg_…` or session | Proxy |
| GET | `/v1/models` | public | Model list |
| POST | `/v1/trace` | tg_ or session | Trace ingest |

## Multi-tenant model

- `users`: email, password_hash, `api_key` (`tg_…`), `upstream_api_key_blob`
- `user_settings`: Fernet blobs for grok/openai/upstream keys
- `sessions.user_id` scopes impact/events to the tenant
- Proxy resolves tenant via `Authorization: Bearer tg_…` **or** session cookie

## Env vars

See README. Critical for deploy:

- `TOKENGUARD_SECRET` (required when `ENV=production`)
- `PUBLIC_BASE_URL`
- `DATA_DIR=/data` (+ volume)
- `HOST=0.0.0.0` `PORT=8080`
- `BILLING_MODE=free`

## Deploy targets

- `Dockerfile` + `docker-compose.yml`
- `railway.json`
- `render.yaml`
- `fly.toml`

**Next human sign-in:** Railway (`railway login`) or Render dashboard — app is ready for `docker build` / `uvicorn` without credentials.

## Honesty

- Token savings labeled **estimate**
- Demo labeled **simulated** (~75% from FakeAgent before/after)
- Provider usage labeled **provider** when present

## Smoke results (local, 2026-10-28 Pacific/Auckland)

```
GET  /health                     → 200  service=tokenguard-saas ok=true
POST /api/auth/signup            → 200  api_key=tg_… credentials.base_url=…/v1
GET  /v1/models  Bearer tg_…     → 200  model list
POST /v1/chat/completions        → 401  (honest: no upstream key — use Integrations/Demo)
GET  /api/credentials (session)  → 200  base_url + tg_ key
POST /api/demo/seed              → 200  simulated=true 3 sessions
GET  /api/impact                 → 200  pct_waste_reduction_est=75.0 tokens_source=estimate
```

Commands:

```bash
./run.sh   # or: uvicorn app.main:app --host 0.0.0.0 --port 8080
curl -s localhost:8080/health
curl -s -X POST localhost:8080/api/auth/signup -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"pass1234","name":"You"}'
```
