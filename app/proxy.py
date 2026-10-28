"""OpenAI-compatible chat/completions proxy with multi-tenant TokenGuard auth."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import auth, db
from .config import TOKENS_PER_TOOL_ESTIMATE, get_settings
from .loop_bridge import (
    check_redundant_messages,
    extract_tool_calls_from_request,
    filter_response_tool_calls,
)
from .tokens import estimate_completion_tokens, estimate_messages_tokens, usage_from_response

log = logging.getLogger("tokenguard.proxy")


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    out = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            out[k] = "Bearer ***"
        else:
            out[k] = v
    return out


def resolve_session_id(
    request: Request, body: Dict[str, Any], *, user_id: str | None = None
) -> str:
    sid = (
        request.headers.get("x-tokenguard-session")
        or request.headers.get("x-loop-stop-session")
        or request.headers.get("x-session-id")
        or (body.get("user") if isinstance(body.get("user"), str) else None)
        or request.query_params.get("session_id")
    )
    if sid:
        existing = db.get_session(sid)
        if not existing:
            db.create_session(
                mode="proxy",
                model=body.get("model"),
                title=f"proxy {sid[:8]}",
                session_id=sid,
                user_id=user_id,
            )
        return sid
    return db.create_session(
        mode="proxy",
        model=body.get("model"),
        title="proxy chat",
        user_id=user_id,
    )


def _resolve_upstream_for_user(
    request: Request, user: Optional[Dict[str, Any]]
) -> tuple[str, str]:
    """
    Return (api_key, upstream_base_url) for this request.
    Priority:
      1. Per-user encrypted BYOK
      2. Incoming Authorization if it is NOT a tg_ key (forward xAI/OpenAI key)
      3. Process env fallback
    """
    settings = get_settings()
    upstream_url = settings.upstream_base_url
    if user:
        us = db.get_user_settings(user["id"])
        if us.get("openai_base_url"):
            upstream_url = us["openai_base_url"]
        key = auth.get_user_upstream_key(user["id"])
        if key:
            return key, upstream_url

    # Forward non-tg Bearer as upstream key (BYOK-via-header)
    auth_h = request.headers.get("authorization") or ""
    if auth_h.lower().startswith("bearer "):
        token = auth_h[7:].strip()
        if token and not token.startswith("tg_"):
            return token, upstream_url

    from .config import get_api_key

    env_key = get_api_key()
    if env_key:
        return env_key, upstream_url

    raise HTTPException(
        status_code=401,
        detail=(
            "No upstream provider key. Paste an xAI/OpenAI key in Integrations "
            "(encrypted with TOKENGUARD_SECRET), pass it as Authorization Bearer "
            "(non-tg_ key), set XAI_API_KEY on the server, or use Demo mode."
        ),
    )


async def forward_chat_completions(request: Request, body: Dict[str, Any]) -> Any:
    user, auth_mode = auth.resolve_proxy_user(request)
    # Allow anonymous only when process has a shared env key AND no tg_ was attempted;
    # otherwise require signup (tg_ or session) for multi-tenant attribution.
    attempted_tg = False
    raw_auth = request.headers.get("authorization") or ""
    if "tg_" in raw_auth:
        attempted_tg = True
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid TokenGuard API key. Sign up to get a tg_… key.",
            )

    settings = get_settings()
    user_id = user["id"] if user else None

    try:
        api_key, upstream = _resolve_upstream_for_user(request, user)
    except HTTPException:
        # Soft path: if cookie/session browser demo with no key, explain clearly
        raise

    session_id = resolve_session_id(request, body, user_id=user_id)
    model = body.get("model") or settings.default_model
    body = dict(body)
    body["model"] = model

    redundant, red_reason = check_redundant_messages(
        session_id, body.get("messages") or []
    )
    if redundant:
        db.add_event(
            session_id,
            kind="message_redundant",
            detail=red_reason,
            allowed=True,
        )

    prior_tools = extract_tool_calls_from_request(body)
    for name, args in prior_tools[-5:]:
        from .loop_bridge import get_detector

        get_detector(session_id).check(name, args, record=True)

    prompt_est, _ = estimate_messages_tokens(body.get("messages") or [])

    upstream = upstream.rstrip("/")
    url = f"{upstream}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for h in ("OpenAI-Organization", "OpenAI-Project"):
        if h.lower() in {k.lower() for k in request.headers.keys()}:
            headers[h] = request.headers.get(h)  # type: ignore

    stream = bool(body.get("stream"))
    log.info(
        "proxy chat/completions session=%s user=%s auth=%s model=%s stream=%s upstream=%s headers=%s",
        session_id,
        user_id or "anon",
        auth_mode,
        model,
        stream,
        upstream,
        _redact_headers(headers),
    )

    if stream:
        return await _stream_proxy(
            url, headers, body, session_id, model, prompt_est
        )

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            r = await client.post(url, headers=headers, json=body)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e}") from e

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    try:
        data = r.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail="Upstream returned non-JSON") from e

    data, decisions = filter_response_tool_calls(
        session_id, data, block=settings.block_loops
    )
    _record_proxy_result(session_id, model, body, data, decisions, prompt_est)

    return JSONResponse(
        content=data,
        headers={
            "X-TokenGuard-Session": session_id,
            "X-Loop-Stop-Session": session_id,
        },
    )


async def _stream_proxy(
    url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    session_id: str,
    model: str,
    prompt_est: int,
) -> StreamingResponse:
    async def gen():
        collected = ""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST", url, headers=headers, json=body
                ) as resp:
                    if resp.status_code >= 400:
                        err = await resp.aread()
                        yield f"data: {json.dumps({'error': err.decode('utf-8', 'replace')})}\n\n"
                        return
                    async for chunk in resp.aiter_bytes():
                        collected += chunk.decode("utf-8", "replace")
                        yield chunk
            except httpx.RequestError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

        out_est, _ = estimate_completion_tokens(
            {"choices": [{"message": {"content": collected}}]}
        )
        db.update_session_metrics(
            session_id,
            tokens_in=prompt_est,
            tokens_out=out_est,
            tokens_source="estimate",
            model=model,
        )
        db.add_event(
            session_id,
            kind="chat",
            detail="streamed completion (loop filter limited in stream mode)",
            tokens_est=prompt_est + out_est,
            allowed=True,
        )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "X-TokenGuard-Session": session_id,
            "X-Loop-Stop-Session": session_id,
        },
    )


def _record_proxy_result(
    session_id: str,
    model: str,
    body: Dict[str, Any],
    data: Dict[str, Any],
    decisions: list,
    prompt_est: int,
) -> None:
    pin, cout, source = usage_from_response(data)
    if source != "provider":
        pin = prompt_est
        cout, _ = estimate_completion_tokens(data)
        source = "estimate"

    tool_delta = 0
    blocked = 0
    avoided = 0
    for d in decisions:
        tool_delta += 1
        dec = d.get("decision") or {}
        allowed = dec.get("allowed", True)
        db.add_event(
            session_id,
            kind="tool_blocked" if not allowed else "tool_call",
            tool=d.get("tool"),
            args=d.get("args"),
            decision=dec,
            tokens_est=TOKENS_PER_TOOL_ESTIMATE if not allowed else 0,
            detail=dec.get("reason"),
            allowed=allowed,
        )
        if not allowed:
            blocked += 1
            avoided += TOKENS_PER_TOOL_ESTIMATE

    db.add_event(
        session_id,
        kind="chat",
        detail=f"chat/completions model={model} tokens_source={source}",
        tokens_est=pin + cout,
        allowed=True,
    )
    db.update_session_metrics(
        session_id,
        tokens_in=pin,
        tokens_out=cout,
        tokens_source=source,
        tool_call_delta=tool_delta,
        blocked_delta=blocked,
        tokens_avoided_delta=avoided,
        model=model,
    )


async def ingest_trace(
    payload: Dict[str, Any], *, user_id: str | None = None
) -> Dict[str, Any]:
    if isinstance(payload, list):
        results = []
        for item in payload:
            results.append(await ingest_trace(item, user_id=user_id))
        return {"ingested": len(results), "sessions": results}

    req = payload.get("request") or {}
    resp = payload.get("response") or payload.get("completion") or {}
    if not resp and payload.get("choices"):
        resp = payload
    if not req and payload.get("messages") and not payload.get("request"):
        req = {"messages": payload.get("messages"), "model": payload.get("model")}

    settings = get_settings()
    sid = payload.get("session_id") or db.new_session_id()
    model = (
        (req.get("model") if isinstance(req, dict) else None)
        or (resp.get("model") if isinstance(resp, dict) else None)
        or settings.default_model
    )
    title = payload.get("title") or f"trace {sid[:8]}"
    if not db.get_session(sid):
        db.create_session(
            mode="trace", model=model, title=title, session_id=sid, user_id=user_id
        )

    messages = (req.get("messages") if isinstance(req, dict) else None) or []
    redundant, red_reason = check_redundant_messages(sid, messages)
    if redundant:
        db.add_event(sid, kind="message_redundant", detail=red_reason, allowed=True)

    if isinstance(resp, dict) and resp.get("choices"):
        resp, decisions = filter_response_tool_calls(
            sid, resp, block=settings.block_loops
        )
    else:
        decisions = []
        for te in payload.get("tool_events") or []:
            name = te.get("tool") or te.get("name") or "tool"
            args = te.get("args") or te.get("arguments") or {}
            from .loop_bridge import check_tool

            decision = check_tool(sid, str(name), args if isinstance(args, dict) else {})
            decisions.append(
                {"tool": name, "args": args, "decision": decision.to_dict()}
            )

    prompt_est, _ = estimate_messages_tokens(messages)
    _record_proxy_result(
        sid,
        model,
        req if isinstance(req, dict) else {},
        resp if isinstance(resp, dict) else {},
        decisions,
        prompt_est,
    )

    return {"session_id": sid, "decisions": len(decisions), "ok": True}
