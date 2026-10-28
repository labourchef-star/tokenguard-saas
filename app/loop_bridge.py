"""Import LoopDetector from sibling loop-stop-demo and keep per-session state."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from .config import DEMO_ROOT, get_settings

# Ensure sibling package is importable
_demo = str(DEMO_ROOT)
if _demo not in sys.path:
    sys.path.insert(0, _demo)

from loop_stop.detector import (  # noqa: E402
    Decision,
    DecisionKind,
    LoopDetector,
    fingerprint_args,
)


# session_id -> LoopDetector
_detectors: Dict[str, LoopDetector] = {}
# session_id -> recent message fingerprints for chat-only redundancy
_msg_hist: Dict[str, Deque[str]] = {}


def get_detector(session_id: str) -> LoopDetector:
    det = _detectors.get(session_id)
    if det is None:
        det = LoopDetector(n=get_settings().loop_n)
        _detectors[session_id] = det
    return det


def reset_detector(session_id: str) -> None:
    _detectors.pop(session_id, None)
    _msg_hist.pop(session_id, None)


def check_tool(
    session_id: str, tool: str, args: Optional[Dict[str, Any]] = None
) -> Decision:
    return get_detector(session_id).check(tool, args or {})


def record_tool_outcome(
    session_id: str, tool: str, args: Dict[str, Any], exit_code: int, ok: bool
) -> None:
    get_detector(session_id).record_outcome(tool, args, exit_code, ok)


def _msg_fp(role: str, content: Any) -> str:
    blob = json.dumps({"role": role, "content": content}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def check_redundant_messages(
    session_id: str, messages: List[Dict[str, Any]], n: Optional[int] = None
) -> Tuple[bool, str]:
    """Flag when the last user/assistant message repeats >= N times recently."""
    threshold = n or get_settings().loop_n
    hist = _msg_hist.setdefault(session_id, deque(maxlen=40))
    if not messages:
        return False, ""
    last = messages[-1]
    fp = _msg_fp(str(last.get("role") or ""), last.get("content"))
    count = sum(1 for h in hist if h == fp)
    hist.append(fp)
    if count + 1 >= threshold and last.get("role") in ("user", "assistant"):
        return True, (
            f"Redundant chat pattern: same {last.get('role')} message fingerprint "
            f"seen {count + 1} times (threshold N={threshold})."
        )
    return False, ""


def extract_tool_calls_from_request(body: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """Pull tool calls the *client* is submitting as assistant tool_calls / tool results.

    For OpenAI chat: messages may include assistant messages with tool_calls, and
    subsequent tool-role messages. We treat each tool_call as a prospective event
    when the latest message asks the model to continue after tools — but the main
    place we intervene is when the *model response* proposes tool_calls (post-proxy)
    or when a client sends a dedicated tool invocation via our annotate path.

    Also inspects body['tools'] presence; actual blocking happens on proposed calls
    found in the assistant message being built — see filter_response_tool_calls.
    """
    out: List[Tuple[str, Dict[str, Any]]] = []
    for m in body.get("messages") or []:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            fn = (tc.get("function") or {})
            name = fn.get("name") or tc.get("name") or "tool"
            raw = fn.get("arguments") or tc.get("arguments") or {}
            if isinstance(raw, str):
                try:
                    args = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    args = {"raw": raw}
            elif isinstance(raw, dict):
                args = raw
            else:
                args = {"raw": str(raw)}
            out.append((str(name), args))
    return out


def filter_response_tool_calls(
    session_id: str, resp: Dict[str, Any], *, block: bool
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Inspect model-proposed tool_calls; block/annotate per LoopDetector.

    Returns (possibly modified response, list of decision records).
    """
    decisions: List[Dict[str, Any]] = []
    if not isinstance(resp, dict):
        return resp, decisions
    choices = resp.get("choices") or []
    for choice in choices:
        msg = (choice or {}).get("message") or {}
        tcs = msg.get("tool_calls") or []
        if not tcs:
            continue
        kept = []
        blocked_notes = []
        for tc in tcs:
            fn = (tc.get("function") or {})
            name = fn.get("name") or tc.get("name") or "tool"
            raw = fn.get("arguments") or {}
            if isinstance(raw, str):
                try:
                    args = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    args = {"raw": raw}
            elif isinstance(raw, dict):
                args = raw
            else:
                args = {"raw": str(raw)}
            decision = check_tool(session_id, str(name), args)
            rec = {
                "tool": name,
                "args": args,
                "decision": decision.to_dict(),
            }
            decisions.append(rec)
            if decision.allowed or not block:
                kept.append(tc)
                if not decision.allowed:
                    # annotate-only mode: keep call but note
                    blocked_notes.append(f"[loop-stop annotate] {decision.reason}")
            else:
                blocked_notes.append(f"[loop-stop blocked] {decision.reason}")
        msg["tool_calls"] = kept if kept else None
        if not kept:
            # Convert to a plain assistant message so clients don't hang on empty tool_calls
            choice["finish_reason"] = "stop"
            existing = msg.get("content") or ""
            note = "\n".join(blocked_notes)
            msg["content"] = (existing + ("\n\n" if existing else "") + note).strip()
            msg.pop("tool_calls", None)
        elif blocked_notes and not block:
            existing = msg.get("content") or ""
            note = "\n".join(blocked_notes)
            msg["content"] = (existing + ("\n\n" if existing else "") + note).strip()
        choice["message"] = msg
    return resp, decisions


__all__ = [
    "Decision",
    "DecisionKind",
    "LoopDetector",
    "fingerprint_args",
    "get_detector",
    "reset_detector",
    "check_tool",
    "record_tool_outcome",
    "check_redundant_messages",
    "extract_tool_calls_from_request",
    "filter_response_tool_calls",
]
