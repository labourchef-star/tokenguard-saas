#!/usr/bin/env bash
# One-command install + first start for Loop Stop retail.
# Usage:
#   ./install.sh
#   curl -fsSL https://example.com/loop-stop/install.sh | bash   # after GitHub Release
set -euo pipefail

# If piped from curl without a checkout, clone then re-exec.
if [[ "${BASH_SOURCE[0]:-}" == "/dev/stdin" ]] || [[ ! -f "${BASH_SOURCE[0]:-}/../pyproject.toml" && ! -f "$(dirname "${BASH_SOURCE[0]:-$0}")/pyproject.toml" ]]; then
  : # fall through; support both local and cloned layouts
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [[ -n "${SCRIPT_DIR}" && -f "${SCRIPT_DIR}/pyproject.toml" ]]; then
  ROOT="${SCRIPT_DIR}"
else
  DEST="${LOOP_STOP_HOME:-$HOME/loop-stop}"
  REPO="${LOOP_STOP_REPO:-}"
  echo "No local checkout found."
  if [[ -z "${REPO}" ]]; then
    echo "Set LOOP_STOP_REPO to a git URL, or run install.sh from the unpacked folder."
    echo "Example: LOOP_STOP_REPO=https://github.com/YOU/loop-stop.git ./install.sh"
    exit 1
  fi
  if [[ ! -d "$DEST/.git" ]]; then
    git clone "$REPO" "$DEST"
  fi
  ROOT="$DEST"
fi

cd "$ROOT"
echo "==> Installing Loop Stop into ${ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required."
  exit 1
fi

chmod +x "$ROOT/run.sh" "$ROOT/hooks/pre_tool_use.sh" 2>/dev/null || true

# Create venv + deps without starting a long-lived server if LOOP_STOP_NO_START=1
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8788}"

if [[ ! -d .venv ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv
  else
    python3 -m venv .venv
  fi
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if command -v uv >/dev/null 2>&1; then
  uv pip install -p .venv/bin/python fastapi "uvicorn[standard]" httpx tiktoken python-multipart pytest
else
  pip install -q fastapi "uvicorn[standard]" httpx tiktoken python-multipart pytest
fi

echo ""
echo "Install complete."
echo "  Dashboard will be at: http://${HOST}:${PORT}/"
echo "  Optional: export XAI_API_KEY=… before starting (or use Demo mode in the UI)."
echo ""

if [[ "${LOOP_STOP_NO_START:-}" == "1" ]]; then
  echo "LOOP_STOP_NO_START=1 — skipping server start. Run: ${ROOT}/run.sh"
  exit 0
fi

exec "$ROOT/run.sh"
