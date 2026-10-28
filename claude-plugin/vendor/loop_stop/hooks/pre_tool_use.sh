#!/usr/bin/env bash
# TokenGuard PreToolUse hook wrapper (bundled vendor copy).
# Reads tool-call JSON from stdin; exits 0=allow, 2=block (reason on stderr).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PYTHONPATH="${PKG_ROOT}${PYTHONPATH:+:$PYTHONPATH}"
STATE="${LOOP_STOP_STATE:-${TOKENGUARD_STATE:-/tmp/tokenguard-hook-state.json}}"
LOG="${LOOP_STOP_LOG:-${TOKENGUARD_LOG:-}}"
N="${LOOP_STOP_N:-${TOKENGUARD_N:-3}}"
exec python3 -m loop_stop.hook_claude_code --state "$STATE" --n "$N" ${LOG:+--log "$LOG"}
