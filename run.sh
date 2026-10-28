#!/usr/bin/env bash
# Start TokenGuard SaaS locally
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export TOKENGUARD_DEMO_ROOT="${TOKENGUARD_DEMO_ROOT:-$ROOT/vendor}"
export TOKENGUARD_VENDOR_ROOT="${TOKENGUARD_VENDOR_ROOT:-$ROOT/vendor}"
export LOOP_STOP_DEMO_ROOT="${LOOP_STOP_DEMO_ROOT:-$TOKENGUARD_DEMO_ROOT}"
export LOOP_STOP_VENDOR_ROOT="${LOOP_STOP_VENDOR_ROOT:-$TOKENGUARD_VENDOR_ROOT}"
export DATA_DIR="${DATA_DIR:-$ROOT/data}"
export PYTHONPATH="${ROOT}:${ROOT}/vendor:${PYTHONPATH:-}"
export BILLING_MODE="${BILLING_MODE:-free}"

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
  uv pip install -p .venv/bin/python -r requirements.txt
else
  pip install -q -r requirements.txt
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://127.0.0.1:${PORT}}"

echo "TokenGuard SaaS"
echo "  Landing   → http://127.0.0.1:${PORT}/"
echo "  Dashboard → http://127.0.0.1:${PORT}/app"
echo "  Health    → http://127.0.0.1:${PORT}/health"
echo "  Proxy     → http://127.0.0.1:${PORT}/v1"
echo "  DATA_DIR  → ${DATA_DIR}"
exec .venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT"
