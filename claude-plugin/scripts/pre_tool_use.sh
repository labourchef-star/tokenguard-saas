#!/usr/bin/env bash
# Loop Stop PreToolUse hook — blocks sticky tool loops (exit 2 = block).
# Invoked by Claude Code with tool JSON on stdin.
set -euo pipefail
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export PYTHONPATH="${ROOT}/vendor${PYTHONPATH:+:$PYTHONPATH}"
DATA_DIR="${CLAUDE_PLUGIN_DATA:-${ROOT}/.loop-stop-data}"
mkdir -p "$DATA_DIR"
STATE="${LOOP_STOP_STATE:-${DATA_DIR}/hook-state.json}"
LOG="${LOOP_STOP_LOG:-}"
N="${LOOP_STOP_N:-3}"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "loop-stop: python3 not found; allowing tool" >&2
  exit 0
fi

exec "$PY" -m loop_stop.hook_claude_code --state "$STATE" --n "$N" ${LOG:+--log "$LOG"}
