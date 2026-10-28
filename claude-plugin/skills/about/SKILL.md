---
description: Explain TokenGuard — how the PreToolUse hook works, that no base_url is needed, and optional SaaS dashboard.
---

Tell the user, in plain language:

1. TokenGuard is a PreToolUse hook that blocks sticky tool loops (same file read repeatedly, failing bash retries, A/B ping-pong).
2. The hook ships inside this Claude Code plugin; it needs **no API key**, **no base_url**, and **no ANTHROPIC_BASE_URL** / proxy pointing.
3. Install was one command: `claude plugin install tokenguard --marketplace labourchef-star/tokenguard-saas` (or `/plugin install tokenguard --marketplace labourchef-star/tokenguard-saas` in a session).
4. Optional later: open the hosted SaaS dashboard at https://tokenguard-saas.onrender.com for impact charts (sign up). That is separate from the local hook.
5. Savings shown on any dashboard are estimates unless a provider returns usage. Demo mode is simulated.
