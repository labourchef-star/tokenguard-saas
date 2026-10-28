# Smoke results — loop-stop-retail

**When:** 2026-10-28 (Pacific/Auckland)  
**Command:** `LOOP_STOP_NO_START=1 ./install.sh` then `./run.sh` (PORT=8788)

## Results

| Check | Result |
| --- | --- |
| Install / venv | OK (uv + fastapi/uvicorn/httpx/tiktoken/pytest) |
| Server bind | `127.0.0.1:8788` |
| `GET /health` | `ok: true`, `service: loop-stop-retail`, `onboarding_completed: false` |
| `POST /api/demo/seed?replay=true` | 3 simulated sessions created |
| Impact % waste reduction (est.) | **75.0%** |
| Tokens used | 14400 (estimate) |
| Tokens saved (est.) | 43200 |
| Baseline → with-stop tool calls | 72 → 18 |
| Loops blocked | 3 |
| Sibling demos | Untouched (`loop-stop-app`, `loop-stop-demo`) |
| Vault / agent_rules | Not modified |

## Local URL

Open: **http://127.0.0.1:8788/**

First visit shows onboarding (Welcome → client → config). Use **Try Demo mode** or the dashboard **Demo mode** button.
