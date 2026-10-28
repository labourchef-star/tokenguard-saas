# Claude Code plugin — exact paths and install commands

**Do not submit to Anthropic’s directory without human approval.**

## Layout (ships in this retail tree)

```
loop-stop-retail/
  claude-plugin/                         # the plugin
    .claude-plugin/plugin.json           # name: loop-stop, v0.1.0
    hooks/hooks.json                     # PreToolUse → scripts/pre_tool_use.sh
    scripts/pre_tool_use.sh              # invokes vendor/loop_stop detector
    vendor/loop_stop/                    # bundled detector (self-contained)
    skills/about/SKILL.md
  .claude-plugin/marketplace.json        # marketplace root = this retail folder
  claude-marketplace/.claude-plugin/marketplace.json   # sibling alt (source ../claude-plugin)
```

Standalone retail hook (dashboard install path, not the plugin): `hooks/pre_tool_use.sh`.

## Install from a local checkout (no publish needed)

Prefer adding the **retail repo root** as the marketplace (it contains `.claude-plugin/marketplace.json`):

```bash
# From any shell where `claude` CLI is available:
claude plugin marketplace add /absolute/path/to/loop-stop-retail
claude plugin install loop-stop@loop-stop-marketplace

# Or enable from inside a Claude Code session:
# /plugin marketplace add /absolute/path/to/loop-stop-retail
# /plugin install loop-stop@loop-stop-marketplace
```

Sibling marketplace folder (same plugin):

```bash
claude plugin marketplace add /absolute/path/to/loop-stop-retail/claude-marketplace
claude plugin install loop-stop@loop-stop-marketplace
```

Load without a marketplace (dev):

```bash
claude --plugin-dir /absolute/path/to/loop-stop-retail/claude-plugin
```

## Settings.json fallback (no plugin system)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Read|Bash|Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "/absolute/path/to/loop-stop-retail/hooks/pre_tool_use.sh"
      }]
    }]
  }
}
```

## Verify hook

```bash
export CLAUDE_PLUGIN_ROOT=/absolute/path/to/loop-stop-retail/claude-plugin
echo '{"tool_name":"Read","tool_input":{"path":"/tmp/x.py"}}' | \
  "$CLAUDE_PLUGIN_ROOT/scripts/pre_tool_use.sh"
# exit 0 = allow; exit 2 = block (reason on stderr). Repeating the same Read ≥ N times blocks.
```

## Dashboard

The plugin hook does not start the Impact dashboard. For charts:

```bash
cd /path/to/loop-stop-retail && ./run.sh
# open http://127.0.0.1:8788/
```
