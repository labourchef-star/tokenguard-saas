#!/usr/bin/env python3
"""Claude Code–style PreToolUse hook entrypoint.

Reads tool JSON from stdin (or --json / --file). Calls LoopDetector.
Exits 0 to allow; exits 2 with reason on stderr to block
(Claude Code PreToolUse convention: non-zero blocks the tool call).

Usage:
  echo '{"tool_name":"Read","tool_input":{"path":"foo.py"}}' \\
    | python -m loop_stop.hook_claude_code
  python -m loop_stop.hook_claude_code \\
    --json '{"tool_name":"Bash","tool_input":{"command":"pytest"}}'
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .detector import LoopDetector, DecisionKind, ToolEvent, decision_from_tool_json
from .session_log import SessionLog


def _load_state(path: Path, n: int, window: int) -> LoopDetector:
    det = LoopDetector(n=n, window=window)
    if not path.exists():
        return det
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("history", []):
            det.history.append(
                ToolEvent(
                    tool=item["tool"],
                    args=item.get("args", {}),
                    fingerprint=item["fingerprint"],
                    exit_code=item.get("exit_code"),
                    ok=item.get("ok"),
                )
            )
    except Exception:
        return LoopDetector(n=n, window=window)
    return det


def _save_state(path: Path, det: LoopDetector) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "history": [
            {
                "tool": ev.tool,
                "args": ev.args,
                "fingerprint": ev.fingerprint,
                "exit_code": ev.exit_code,
                "ok": ev.ok,
            }
            for ev in det.history
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="loop-stop PreToolUse hook")
    parser.add_argument("--json", dest="json_str", default=None)
    parser.add_argument("--file", dest="json_file", default=None)
    parser.add_argument(
        "--state",
        default=os.environ.get("LOOP_STOP_STATE", "/tmp/loop-stop-state.json"),
    )
    parser.add_argument("--log", default=os.environ.get("LOOP_STOP_LOG", ""))
    parser.add_argument("--n", type=int, default=int(os.environ.get("LOOP_STOP_N", "3")))
    parser.add_argument(
        "--window", type=int, default=int(os.environ.get("LOOP_STOP_WINDOW", "40"))
    )
    args = parser.parse_args(argv)

    if args.json_str:
        raw = args.json_str
    elif args.json_file:
        raw = Path(args.json_file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("loop-stop: empty input; allowing", file=sys.stderr)
        return 0

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"loop-stop: invalid JSON ({e}); allowing", file=sys.stderr)
        return 0

    det = _load_state(Path(args.state), n=args.n, window=args.window)
    decision = decision_from_tool_json(payload, det)
    _save_state(Path(args.state), det)

    tool = (
        payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or ""
    )
    tool_args = (
        payload.get("tool_input")
        or payload.get("arguments")
        or payload.get("args")
        or payload.get("input")
        or {}
    )

    if args.log:
        SessionLog(args.log).append(
            tool=str(tool),
            args=tool_args if isinstance(tool_args, dict) else {"raw": tool_args},
            decision=decision.to_dict(),
        )

    if decision.kind == DecisionKind.BLOCK:
        print(decision.reason, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
