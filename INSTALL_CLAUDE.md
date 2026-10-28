# Install TokenGuard for Claude Code

## One command

In a Claude Code session:

```text
/plugin install tokenguard --marketplace labourchef-star/tokenguard-saas
```

Or from your shell:

```bash
claude plugin install tokenguard --marketplace labourchef-star/tokenguard-saas
```

## What happens

1. Claude Code registers the GitHub marketplace (`labourchef-star/tokenguard-saas`).
2. The **tokenguard** plugin installs with a local **PreToolUse** hook.
3. Sticky tool loops (repeated reads, failing bash, ping-pong) are blocked before they burn tokens.

**No URL config.** You do **not** set `ANTHROPIC_BASE_URL`, OpenAI `base_url`, or any proxy for Claude Code.

## Optional later

- Hosted SaaS dashboard (impact charts): https://tokenguard-saas.onrender.com — sign up when you want numbers; not required for the hook.
- Cursor / OpenAI-compatible clients: use the hosted proxy `base_url` path (advanced) — see the Integrations page after signup.

## Official Anthropic directory

Submitting to Anthropic’s official plugin directory needs a human approval step. Until then, the GitHub marketplace command above is the supported one-shot install.
