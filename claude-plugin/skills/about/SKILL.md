---
description: Explain Loop Stop — how the PreToolUse hook works and how to open the local impact dashboard.
---

Tell the user, in plain language:

1. Loop Stop is a PreToolUse hook that blocks sticky tool loops (same file read repeatedly, failing bash retries, A/B ping-pong).
2. The hook ships inside this Claude Code plugin; it needs no API key.
3. For charts of estimated token waste, they can also run the local dashboard from the Loop Stop retail folder: `./run.sh` then open http://127.0.0.1:8788/
4. Savings shown on the dashboard are estimates unless a provider returns usage. Demo mode is simulated.
