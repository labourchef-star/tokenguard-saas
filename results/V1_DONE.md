# Loop Stop retail v0.1.0 — V1 DONE (local)

**Status:** Initial retail version complete under `/workspace/grok-dev/loop-stop-retail/`.  
**Not published.** No Gumroad / GitHub Release / Anthropic directory / paid spend.

## What is complete

- [x] Local FastAPI proxy + Impact dashboard (port **8788**)
- [x] `install.sh` / `run.sh` (venv + deps; `LOOP_STOP_NO_START=1` supported)
- [x] Demo seed → **~75%** estimated waste reduction (honest “estimate” labels)
- [x] Onboarding API (`GET`/`POST /api/onboarding`) + UI at `/`
- [x] Real Claude Code plugin tree under `claude-plugin/`
- [x] Marketplace manifests for `/plugin marketplace add` later
- [x] Release zip via `packaging/build_release.sh`
- [x] Unpack + `LOOP_STOP_NO_START=1 ./install.sh` verified from temp dir
- [x] Plugin hook smoke: 3rd identical Read → exit **2**
- [x] `VERSION` = `0.1.0`; README says ready to package; not published

## Local URL

http://127.0.0.1:8788/

- `GET /health` → `ok: true`, service `loop-stop-retail`
- `POST /api/demo/seed` → 3 simulated sessions
- `GET /api/impact` → `pct_waste_reduction_est: 75.0`

## Zip path

```
/workspace/grok-dev/loop-stop-retail/dist/loop-stop-CODING-AGENT-TOKEN-GUARD-v0.1.0.zip
```

Rebuild: `./packaging/build_release.sh`  
Excludes: `.venv`, `data/`, `*.db`, `__pycache__`, `.git`, `dist/`

## Claude plugin paths

| Path | Role |
|------|------|
| `claude-plugin/.claude-plugin/plugin.json` | Plugin manifest (`name: loop-stop`) |
| `claude-plugin/hooks/hooks.json` | PreToolUse → `${CLAUDE_PLUGIN_ROOT}/scripts/pre_tool_use.sh` |
| `claude-plugin/scripts/pre_tool_use.sh` | Invokes bundled `vendor/loop_stop` |
| `claude-plugin/vendor/loop_stop/` | Detector package |
| `.claude-plugin/marketplace.json` | Marketplace at retail root |
| `claude-marketplace/.claude-plugin/marketplace.json` | Sibling marketplace alt |

Install (local, no publish):

```bash
claude plugin marketplace add /absolute/path/to/loop-stop-retail
claude plugin install loop-stop@loop-stop-marketplace
# or: claude --plugin-dir /absolute/path/to/loop-stop-retail/claude-plugin
```

See `packaging/claude-code-plugin.md`.

## Smoke numbers (this run)

| Check | Result |
|-------|--------|
| Health | ok |
| Onboarding completed | true (via API) |
| Demo sessions | 3 |
| Tool calls baseline → with stop | 72 → 18 |
| Loops blocked | 3 |
| `pct_waste_reduction_est` | **75.0** |
| UI `/` | HTTP 200 |
| Hook 3× same Read | exit 0, 0, **2** |
| Unpack install | OK |

## Human-only leftover (do not automate)

1. **GitHub** — create repo + Release attaching the zip  
2. **Gumroad** — create listing + upload zip (see `packaging/gumroad.md`)  
3. **XAI API key** — optional live upstream (`export XAI_API_KEY=…`); Demo works without it  
4. **Anthropic plugin directory** — submit only with explicit human approval  

Money Engine Pass remains **Fail** (by design for this build).
