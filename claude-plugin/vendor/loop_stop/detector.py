"""Quality-preserving loop detector for coding-agent tool calls.

Tracks recent tool calls (type + normalized args fingerprint) and fires when:
  - same Read path appears >= N times in the window
  - same Bash command fails >= N times with identical exit code
  - alternating ping-pong patterns (A,B,A,B,...) of length >= 2N

Returns Decision(allow | block_with_reason).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple


class DecisionKind(str, Enum):
    ALLOW = "allow"
    BLOCK = "block_with_reason"


@dataclass
class Decision:
    kind: DecisionKind
    reason: str = ""
    rule: str = ""

    @property
    def allowed(self) -> bool:
        return self.kind == DecisionKind.ALLOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "reason": self.reason,
            "rule": self.rule,
            "allowed": self.allowed,
        }


@dataclass
class ToolEvent:
    tool: str
    args: Dict[str, Any]
    fingerprint: str
    exit_code: Optional[int] = None
    ok: Optional[bool] = None


def _normalize_path(path: str) -> str:
    p = (path or "").strip().replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    return p


def _normalize_cmd(cmd: str) -> str:
    c = (cmd or "").strip()
    c = re.sub(r"\s+", " ", c)
    return c


def _ordinal(k: int) -> str:
    if 10 <= k % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th")
    return f"{k}{suffix}"


def fingerprint_args(tool: str, args: Dict[str, Any]) -> str:
    """Stable fingerprint of tool + normalized args."""
    tool_l = (tool or "").strip().lower()
    norm: Dict[str, Any] = {}
    if tool_l in ("read", "read_file", "view", "cat"):
        path = args.get("path") or args.get("file_path") or args.get("file") or ""
        norm["path"] = _normalize_path(str(path))
    elif tool_l in ("bash", "shell", "run", "terminal"):
        cmd = args.get("command") or args.get("cmd") or args.get("script") or ""
        norm["command"] = _normalize_cmd(str(cmd))
    else:
        # Generic: sorted JSON of args with string normalization
        try:
            norm = json.loads(json.dumps(args, sort_keys=True, default=str))
        except Exception:
            norm = {"raw": str(args)}
    blob = json.dumps({"tool": tool_l, "args": norm}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


@dataclass
class LoopDetector:
    """Sliding-window loop detector.

    Defaults: N=3 (same Read path thrice, same failing Bash thrice,
    or ping-pong of length >= 2N).
    """

    n: int = 3
    window: int = 40
    history: Deque[ToolEvent] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.n < 2:
            raise ValueError("n must be >= 2")
        if self.window < self.n:
            self.window = self.n * 4
        self.history = deque(maxlen=self.window)

    def reset(self) -> None:
        self.history.clear()

    def check(
        self,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        *,
        exit_code: Optional[int] = None,
        ok: Optional[bool] = None,
        record: bool = True,
    ) -> Decision:
        """Evaluate a prospective (or completed) tool call.

        For PreToolUse hooks, call with args only (exit_code/ok None).
        For post-tool feedback of Bash failures, call again with exit_code
        and record=True so the failure streak is counted.
        """
        args = args or {}
        fp = fingerprint_args(tool, args)
        event = ToolEvent(
            tool=(tool or "").strip(),
            args=dict(args),
            fingerprint=fp,
            exit_code=exit_code,
            ok=ok,
        )

        # Evaluate against current history BEFORE recording the new event
        decision = self._evaluate(event)

        # After a failing-bash block, clear that command's failure streak so a
        # post-fix retry of the same test command is allowed (escape hatch).
        if (
            decision.kind == DecisionKind.BLOCK
            and decision.rule == "repeated_failing_bash"
        ):
            self._purge_command(event)
            # Do not append the blocked attempt — streak already spent.
            return decision

        if record:
            self.history.append(event)

        return decision

    def record_outcome(
        self, tool: str, args: Dict[str, Any], exit_code: int, ok: bool
    ) -> None:
        """Update the most recent matching event's outcome, or append."""
        fp = fingerprint_args(tool, args)
        for ev in reversed(self.history):
            if ev.fingerprint == fp and ev.exit_code is None:
                ev.exit_code = exit_code
                ev.ok = ok
                return
        self.history.append(
            ToolEvent(
                tool=tool,
                args=dict(args),
                fingerprint=fp,
                exit_code=exit_code,
                ok=ok,
            )
        )

    def _purge_command(self, event: ToolEvent) -> None:
        """Remove history entries that share this Bash command fingerprint."""
        kept = [ev for ev in self.history if ev.fingerprint != event.fingerprint]
        self.history.clear()
        self.history.extend(kept)

    def _evaluate(self, incoming: ToolEvent) -> Decision:
        tool_l = incoming.tool.lower()

        # Rule 1 (checked first): alternating ping-pong A,B,A,B,... length >= 2N
        fps = [ev.fingerprint for ev in self.history] + [incoming.fingerprint]
        need = 2 * self.n
        if len(fps) >= need:
            tail = fps[-need:]
            a, b = tail[0], tail[1]
            if a != b and all(
                (tail[i] == a if i % 2 == 0 else tail[i] == b) for i in range(need)
            ):
                return Decision(
                    kind=DecisionKind.BLOCK,
                    rule="ping_pong",
                    reason=(
                        f"Loop detected: alternating ping-pong pattern of length "
                        f"{need} (threshold 2N={need}). Two tool calls are "
                        f"oscillating; break the cycle with a new strategy."
                    ),
                )

        # Rule 2: same Read path >= N times in window
        if tool_l in ("read", "read_file", "view", "cat"):
            path = _normalize_path(
                str(
                    incoming.args.get("path")
                    or incoming.args.get("file_path")
                    or incoming.args.get("file")
                    or ""
                )
            )
            if path:
                count = sum(
                    1
                    for ev in self.history
                    if ev.tool.lower() in ("read", "read_file", "view", "cat")
                    and _normalize_path(
                        str(
                            ev.args.get("path")
                            or ev.args.get("file_path")
                            or ev.args.get("file")
                            or ""
                        )
                    )
                    == path
                )
                # Incoming would make it count+1
                if count + 1 >= self.n:
                    return Decision(
                        kind=DecisionKind.BLOCK,
                        rule="repeated_read",
                        reason=(
                            f"Loop detected: Read of '{path}' would be the "
                            f"{_ordinal(count + 1)} time in the last {len(self.history) + 1} "
                            f"tool calls (threshold N={self.n}). Try a different "
                            f"approach instead of re-reading the same file."
                        ),
                    )

        # Rule 3: same Bash command failing >= N times with identical exit
        if tool_l in ("bash", "shell", "run", "terminal"):
            cmd = _normalize_cmd(
                str(
                    incoming.args.get("command")
                    or incoming.args.get("cmd")
                    or incoming.args.get("script")
                    or ""
                )
            )
            if cmd:
                # Count prior failures of this exact command with same exit
                # If incoming already has exit_code, use that; else look at
                # prior failures and block the Nth *attempt* when prior
                # failures already hit N-1 (i.e. about to retry again).
                fail_exits: List[int] = []
                for ev in self.history:
                    if ev.tool.lower() not in ("bash", "shell", "run", "terminal"):
                        continue
                    ev_cmd = _normalize_cmd(
                        str(
                            ev.args.get("command")
                            or ev.args.get("cmd")
                            or ev.args.get("script")
                            or ""
                        )
                    )
                    if ev_cmd != cmd:
                        continue
                    if ev.ok is False or (ev.exit_code is not None and ev.exit_code != 0):
                        fail_exits.append(ev.exit_code if ev.exit_code is not None else -1)

                if fail_exits:
                    # Group by exit code
                    from collections import Counter

                    counts = Counter(fail_exits)
                    # Most common failing exit
                    top_exit, top_count = counts.most_common(1)[0]
                    # Block when we already have >= N-1 failures and this is another attempt
                    # (PreToolUse: no exit yet) OR when recording the Nth failure.
                    if top_count >= self.n - 1 and incoming.exit_code is None:
                        return Decision(
                            kind=DecisionKind.BLOCK,
                            rule="repeated_failing_bash",
                            reason=(
                                f"Loop detected: Bash command failed {top_count} time(s) "
                                f"with exit={top_exit}: `{cmd}`. Blocking retry "
                                f"(threshold N={self.n}). Inspect the error and change "
                                f"the command or fix the underlying issue."
                            ),
                        )
                    if (
                        incoming.exit_code is not None
                        and incoming.exit_code != 0
                        and top_count + 1 >= self.n
                        and (incoming.exit_code == top_exit or top_exit == -1)
                    ):
                        return Decision(
                            kind=DecisionKind.BLOCK,
                            rule="repeated_failing_bash",
                            reason=(
                                f"Loop detected: Bash command failed {top_count + 1} "
                                f"times with exit={incoming.exit_code}: `{cmd}` "
                                f"(threshold N={self.n})."
                            ),
                        )

        return Decision(kind=DecisionKind.ALLOW, reason="ok")


def decision_from_tool_json(payload: Dict[str, Any], detector: LoopDetector) -> Decision:
    """Parse a Claude-Code-style PreToolUse JSON payload and decide."""
    tool = (
        payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or ""
    )
    args = (
        payload.get("tool_input")
        or payload.get("arguments")
        or payload.get("args")
        or payload.get("input")
        or {}
    )
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"raw": args}
    return detector.check(str(tool), dict(args) if isinstance(args, dict) else {})
