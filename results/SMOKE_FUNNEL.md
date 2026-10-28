# Smoke — marketing funnel (2026-10-28 Pacific/Auckland)

Server: `http://127.0.0.1:8788/`

| Step | Result |
| --- | --- |
| Landing `/` | 200 — Sign up / Try demo / 75% simulated |
| Signup POST | 303 → `/download` + session cookie |
| `/api/auth/me` | OK |
| Integrations save Grok key | masked opaque secret |
| Demo seed | 3 simulated sessions |
| Impact | **75.0%** est. waste reduction |
| `/v1/models` | OK (proxy intact) |
| `/download/zip` | zip available |

Open: **http://127.0.0.1:8788/**
