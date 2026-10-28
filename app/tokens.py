"""Token counting: prefer provider usage, else tiktoken, else char heuristic.

Always label the source so the dashboard stays honest.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

_enc = None
_tiktoken_ok: Optional[bool] = None


def _get_encoder():
    global _enc, _tiktoken_ok
    if _tiktoken_ok is False:
        return None
    if _enc is not None:
        return _enc
    try:
        import tiktoken

        # cl100k_base is a reasonable OpenAI-compatible stand-in for estimates
        _enc = tiktoken.get_encoding("cl100k_base")
        _tiktoken_ok = True
        return _enc
    except Exception:
        _tiktoken_ok = False
        return None


def estimate_text_tokens(text: str) -> Tuple[int, str]:
    if not text:
        return 0, "estimate"
    enc = _get_encoder()
    if enc is not None:
        try:
            return len(enc.encode(text)), "estimate"  # tiktoken estimate
        except Exception:
            pass
    # ~4 chars per token heuristic
    return max(1, (len(text) + 3) // 4), "estimate"


def _content_to_str(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text") or part.get("content") or ""))
            else:
                parts.append(str(part))
        return "\n".join(parts)
    if isinstance(content, dict):
        return json.dumps(content, default=str)
    return str(content)


def estimate_messages_tokens(messages: List[Dict[str, Any]]) -> Tuple[int, str]:
    total = 0
    source = "estimate"
    for m in messages or []:
        total += 4  # role / framing overhead approx
        total += estimate_text_tokens(_content_to_str(m.get("content")))[0]
        if m.get("tool_calls"):
            total += estimate_text_tokens(json.dumps(m["tool_calls"], default=str))[0]
        if m.get("name"):
            total += estimate_text_tokens(str(m["name"]))[0]
    return total, source


def usage_from_response(resp: Dict[str, Any]) -> Tuple[int, int, str]:
    """Return (prompt_tokens, completion_tokens, source)."""
    usage = resp.get("usage") if isinstance(resp, dict) else None
    if isinstance(usage, dict):
        pin = usage.get("prompt_tokens")
        cout = usage.get("completion_tokens")
        if pin is not None or cout is not None:
            return int(pin or 0), int(cout or 0), "provider"
    return 0, 0, "estimate"


def estimate_completion_tokens(resp: Dict[str, Any]) -> Tuple[int, str]:
    choices = resp.get("choices") or []
    text_bits = []
    for c in choices:
        msg = (c or {}).get("message") or {}
        text_bits.append(_content_to_str(msg.get("content")))
        if msg.get("tool_calls"):
            text_bits.append(json.dumps(msg["tool_calls"], default=str))
    return estimate_text_tokens("\n".join(text_bits))
