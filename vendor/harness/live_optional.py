"""OPTIONAL live-API harness stub — NOT used by the default demo.

v1 ships simulated-only (FakeAgent). This module is a placeholder for a
future run that would drive a real coding agent behind the PreToolUse hook.

Policy:
  - Do not run unless ANTHROPIC_API_KEY or OPENAI_API_KEY is already present
    in the environment or a known config file on the box.
  - Never invent keys; never prompt a human to paste keys into chat.
  - Cap spend: refuse to start if estimated cost > $5 without an explicit
    note in results. Hard ceiling for this repo: $40 total across all runs.
  - Always label live results as mode="live" separately from simulated.

Usage (when a key exists and you intentionally opt in):
  LOOP_STOP_LIVE=1 python -m harness.live_optional

This stub only checks for keys and exits; it does not call any API.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _key_present() -> str | None:
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(name):
            return name
    # Known on-disk locations (read presence only; do not print secrets)
    candidates = [
        Path.home() / ".anthropic" / "api_key",
        Path.home() / ".config" / "anthropic" / "api_key",
        Path.home() / ".openai" / "api_key",
        Path.home() / ".config" / "openai" / "api_key",
    ]
    for p in candidates:
        if p.is_file() and p.stat().st_size > 0:
            return str(p)
    return None


def main() -> int:
    if os.environ.get("LOOP_STOP_LIVE") != "1":
        print(
            "live_optional: disabled (set LOOP_STOP_LIVE=1 to opt in). "
            "Default demo is simulated — use: python -m harness.run_before_after"
        )
        return 0
    found = _key_present()
    if not found:
        print(
            "live_optional: no Anthropic/OpenAI key found in env or ~/.config. "
            "Refusing to invent a key. Stick with the simulated harness."
        )
        return 2
    print(
        f"live_optional: key source detected ({found!r}) but live runner is "
        f"not implemented in v1 (prefer simulation; avoid >$5 unattended spend). "
        f"Exiting without API calls. api_spend_usd=0.00"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
