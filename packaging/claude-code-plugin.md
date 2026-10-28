# Claude Code plugin — one-command install

**Do not submit to Anthropic’s directory without human approval.**

## Primary install (GitHub marketplace)

One command. No `base_url`, no `ANTHROPIC_BASE_URL`, no proxy pointing.

In a Claude Code session:

```text
/plugin install tokenguard --marketplace labourchef-star/tokenguard-saas
```

From your shell (Claude Code CLI v2.1.292+):

```bash
claude plugin install tokenguard --marketplace labourchef-star/tokenguard-saas
```

What happens: Claude Code adds the GitHub marketplace (repo root `.claude-plugin/marketplace.json`), installs the `tokenguard` plugin, and enables the PreToolUse hook. Sticky Read/Bash/Edit loops are blocked locally.

## Layout (this repo = marketplace root)

```
tokenguard-saas/                         # GitHub: labourchef-star/tokenguard-saas
  .claude-plugin/marketplace.json        # name: tokenguard-marketplace; source ./claude-plugin
  claude-plugin/                         # the plugin
    .claude-plugin/plugin.json           # name: tokenguard
    hooks/hooks.json                     # PreToolUse → scripts/pre_tool_use.sh
    scripts/pre_tool_use.sh              # invokes vendor/loop_stop detector
    vendor/loop_stop/                    # bundled detector (internal module name unchanged)
    skills/about/SKILL.md
  claude-marketplace/                    # optional sibling; prefer repo root
  INSTALL_CLAUDE.md
```

## Local checkout (dev)

```bash
claude plugin marketplace add /absolute/path/to/tokenguard-saas
claude plugin install tokenguard@tokenguard-marketplace

# Or load without marketplace:
claude --plugin-dir /absolute/path/to/tokenguard-saas/claude-plugin
```

## Settings.json fallback (no plugin system)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Read|Bash|Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "/absolute/path/to/tokenguard-saas/hooks/pre_tool_use.sh"
      }]
    }]
  }
}
```

## Verify hook

```bash
export CLAUDE_PLUGIN_ROOT=/absolute/path/to/tokenguard-saas/claude-plugin
echo '{"tool_name":"Read","tool_input":{"path":"/tmp/x.py"}}' | \
  "$CLAUDE_PLUGIN_ROOT/scripts/pre_tool_use.sh"
# exit 0 = allow; exit 2 = block (reason on stderr). Repeating the same Read ≥ N times blocks.
```

## Optional SaaS dashboard (not required for Claude)

Hosted impact charts: https://tokenguard-saas.onrender.com — sign up later if you want. Claude protection does **not** need that URL.

OpenAI-compatible / Cursor clients that cannot use PreToolUse may still point `base_url` at the hosted proxy — that path is secondary/advanced.
