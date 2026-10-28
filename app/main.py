"""TokenGuard SaaS: signup → dashboard with base_url + tg_ key → hosted proxy."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth, db
from .config import (
    BILLING_MODE,
    PRODUCT_NAME,
    get_settings,
    has_api_key,
    load_onboarding,
    public_base_url,
    save_onboarding,
    update_settings,
)
from .demo_seed import seed_from_harness, seed_from_latest_json_only
from .proxy import forward_chat_completions, ingest_trace

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("tokenguard.saas")

STATIC_DIR = Path(__file__).resolve().parent / "static"
APP_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(
    title=PRODUCT_NAME,
    version="0.1.0",
    description=(
        "Hosted OpenAI-compatible proxy with loop-stop middleware "
        "and a token-waste impact dashboard. Sign up → get base_url + tg_ key."
    ),
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    log.info(
        "tokenguard-saas ready; billing=%s env_key=%s upstream=%s model=%s",
        BILLING_MODE,
        "configured" if has_api_key() else "missing",
        get_settings().upstream_base_url,
        get_settings().default_model,
    )


def _page(name: str) -> FileResponse:
    path = STATIC_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"missing page {name}")
    return FileResponse(path)


def _req_base(request: Request) -> str:
    return public_base_url(str(request.base_url).rstrip("/"))


# ----- pages -----

@app.get("/")
def landing() -> FileResponse:
    return _page("landing.html")


@app.get("/app")
@app.get("/dashboard")
def dashboard() -> FileResponse:
    return _page("index.html")


@app.get("/signup")
def signup_page() -> FileResponse:
    return _page("signup.html")


@app.get("/signin")
def signin_page() -> FileResponse:
    return _page("signin.html")


@app.get("/integrations")
def integrations_page() -> FileResponse:
    return _page("integrations.html")


@app.get("/account")
def account_page() -> FileResponse:
    return _page("account.html")


@app.get("/download")
def download_redirect() -> RedirectResponse:
    """Download zip is no longer primary CTA — send people to signup/dashboard."""
    return RedirectResponse(url="/signup", status_code=302)


# ----- auth -----

def _safe_next(next_url: Optional[str], default: str = "/app") -> str:
    if not next_url:
        return default
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return default


@app.post("/signup")
async def signup_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
    next: str = Form(""),
) -> RedirectResponse:
    try:
        user = auth.create_user(email=email, password=password, name=name)
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else "Signup failed"
        return RedirectResponse(
            url=f"/signup?error={quote(detail)}",
            status_code=303,
        )
    resp = RedirectResponse(url=_safe_next(next or "/app"), status_code=303)
    auth.start_session(resp, user["id"])
    save_onboarding({"step": "credentials", "completed": False})
    return resp


@app.post("/signin")
async def signin_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
) -> RedirectResponse:
    try:
        user = auth.authenticate(email=email, password=password)
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else "Sign in failed"
        nxt = quote(next or "/app")
        return RedirectResponse(
            url=f"/signin?error={quote(detail)}&next={nxt}",
            status_code=303,
        )
    resp = RedirectResponse(url=_safe_next(next or "/app"), status_code=303)
    auth.start_session(resp, user["id"])
    return resp


@app.post("/signout")
async def signout_form(request: Request) -> RedirectResponse:
    resp = RedirectResponse(url="/", status_code=303)
    auth.end_session(request, resp)
    return resp


class AuthBody(BaseModel):
    email: str
    password: str
    name: Optional[str] = ""


@app.post("/api/auth/signup")
def api_signup(body: AuthBody, request: Request) -> JSONResponse:
    user = auth.create_user(email=body.email, password=body.password, name=body.name or "")
    creds = auth.dashboard_credentials(user, request)
    payload = {
        "user": auth.public_user(user),
        "ok": True,
        "credentials": creds,
        "billing_mode": BILLING_MODE,
    }
    resp = JSONResponse(payload)
    auth.start_session(resp, user["id"])
    return resp


@app.post("/api/auth/signin")
def api_signin(body: AuthBody, request: Request) -> JSONResponse:
    user = auth.authenticate(email=body.email, password=body.password)
    creds = auth.dashboard_credentials(user, request)
    payload = {
        "user": auth.public_user(user),
        "ok": True,
        "credentials": creds,
    }
    resp = JSONResponse(payload)
    auth.start_session(resp, user["id"])
    return resp


@app.post("/api/auth/signout")
def api_signout(request: Request) -> JSONResponse:
    resp = JSONResponse({"ok": True})
    auth.end_session(request, resp)
    return resp


@app.get("/api/auth/me")
def api_me(request: Request) -> Dict[str, Any]:
    user = auth.current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    full = db.get_user(user["id"]) or user
    out = auth.public_user(full)
    out["credentials"] = auth.dashboard_credentials(full, request)
    out["billing_mode"] = BILLING_MODE
    return out


@app.post("/api/auth/rotate-key")
def api_rotate_key(request: Request) -> Dict[str, Any]:
    user = auth.require_user(request)
    new_key = auth.rotate_api_key(user["id"])
    full = db.get_user(user["id"])
    assert full
    return {
        "ok": True,
        "api_key": new_key,
        "credentials": auth.dashboard_credentials(full, request),
    }


# ----- integrations -----

class IntegrationsUpdate(BaseModel):
    grok_api_key: Optional[str] = None
    clear_grok: Optional[bool] = None
    openai_api_key: Optional[str] = None
    clear_openai: Optional[bool] = None
    upstream_api_key: Optional[str] = None
    clear_upstream: Optional[bool] = None
    openai_base_url: Optional[str] = None
    claude_hook_installed: Optional[bool] = None
    preferred_client: Optional[str] = None


def _integrations_public(user_id: str, request: Request) -> Dict[str, Any]:
    s = db.get_user_settings(user_id)
    user = db.get_user(user_id) or {}
    grok_plain = auth.decrypt_secret(s.get("grok_api_key_blob") or "")
    oa_plain = auth.decrypt_secret(s.get("openai_api_key_blob") or "")
    up_plain = auth.decrypt_secret(
        s.get("upstream_api_key_blob") or user.get("upstream_api_key_blob") or ""
    )
    base = _req_base(request)
    return {
        "grok_key_set": bool(grok_plain),
        "grok_key_masked": auth.mask_secret(grok_plain) if grok_plain else "",
        "openai_key_set": bool(oa_plain),
        "openai_key_masked": auth.mask_secret(oa_plain) if oa_plain else "",
        "upstream_key_set": bool(up_plain or grok_plain or oa_plain),
        "upstream_key_masked": auth.mask_secret(up_plain or grok_plain or oa_plain),
        "openai_base_url": s.get("openai_base_url") or "",
        "claude_hook_installed": bool(s.get("claude_hook_installed")),
        "preferred_client": s.get("preferred_client"),
        "proxy_base_url": f"{base}/v1",
        "public_base_url": base,
        "api_key": user.get("api_key") or "",
        "env_api_key_configured": has_api_key(),
        "billing_mode": BILLING_MODE,
        "note": "Upstream keys encrypted with TOKENGUARD_SECRET (Fernet). Never logged or returned in full.",
    }


@app.get("/api/integrations")
def api_integrations_get(request: Request) -> Dict[str, Any]:
    user = auth.require_user(request)
    return _integrations_public(user["id"], request)


@app.post("/api/integrations")
def api_integrations_post(body: IntegrationsUpdate, request: Request) -> Dict[str, Any]:
    user = auth.require_user(request)
    kwargs: Dict[str, Any] = {}
    if body.clear_grok:
        kwargs["grok_api_key_blob"] = ""
    elif body.grok_api_key is not None and body.grok_api_key.strip():
        kwargs["grok_api_key_blob"] = auth.encrypt_secret(body.grok_api_key.strip())
    if body.clear_openai:
        kwargs["openai_api_key_blob"] = ""
    elif body.openai_api_key is not None and body.openai_api_key.strip():
        kwargs["openai_api_key_blob"] = auth.encrypt_secret(body.openai_api_key.strip())
    if body.clear_upstream:
        kwargs["upstream_api_key_blob"] = ""
    elif body.upstream_api_key is not None and body.upstream_api_key.strip():
        kwargs["upstream_api_key_blob"] = auth.encrypt_secret(body.upstream_api_key.strip())
    if body.openai_base_url is not None:
        kwargs["openai_base_url"] = body.openai_base_url.strip()
    if body.claude_hook_installed is not None:
        kwargs["claude_hook_installed"] = body.claude_hook_installed
    if body.preferred_client is not None:
        kwargs["preferred_client"] = body.preferred_client
    if kwargs:
        db.update_user_settings(user["id"], **kwargs)
    return _integrations_public(user["id"], request)


# ----- health / settings / onboarding / impact -----

@app.get("/health")
def health(request: Request) -> Dict[str, Any]:
    ob = load_onboarding()
    user = auth.current_user(request)
    base = _req_base(request)
    return {
        "ok": True,
        "service": "tokenguard-saas",
        "product": PRODUCT_NAME,
        "billing_mode": BILLING_MODE,
        "api_key_configured": has_api_key(),
        "upstream": get_settings().upstream_base_url,
        "default_model": get_settings().default_model,
        "onboarding_completed": bool(ob.get("completed")),
        "signed_in": bool(user),
        "public_base_url": base,
        "routes": {
            "landing": "/",
            "signup": "/signup",
            "signin": "/signin",
            "integrations": "/integrations",
            "dashboard": "/app",
            "account": "/account",
            "proxy": "/v1",
            "health": "/health",
        },
    }


class SettingsUpdate(BaseModel):
    upstream_base_url: Optional[str] = None
    default_model: Optional[str] = None
    loop_n: Optional[int] = Field(default=None, ge=2, le=20)
    block_loops: Optional[bool] = None


@app.get("/api/settings")
def api_settings(request: Request) -> Dict[str, Any]:
    d = get_settings().to_public_dict()
    d["public_base_url"] = _req_base(request)
    user = auth.current_user(request)
    if user:
        d["credentials"] = auth.dashboard_credentials(
            db.get_user(user["id"]) or user, request
        )
    return d


@app.post("/api/settings")
def api_settings_update(body: SettingsUpdate, request: Request) -> Dict[str, Any]:
    # Settings are process-global for loop threshold; upstream override is per-user via integrations
    update_settings(**{k: v for k, v in body.model_dump().items() if v is not None})
    return api_settings(request)


class OnboardingUpdate(BaseModel):
    completed: Optional[bool] = None
    client: Optional[str] = None
    demo_mode: Optional[bool] = None
    step: Optional[str] = None


@app.get("/api/onboarding")
def api_onboarding_get() -> Dict[str, Any]:
    return load_onboarding()


@app.post("/api/onboarding")
def api_onboarding_post(body: OnboardingUpdate) -> Dict[str, Any]:
    return save_onboarding(body.model_dump(exclude_none=True))


@app.get("/api/impact")
def api_impact(request: Request) -> Dict[str, Any]:
    user = auth.current_user(request)
    return db.impact_summary(user_id=user["id"] if user else None)


@app.get("/api/sessions")
def api_sessions(request: Request, limit: int = 100) -> Dict[str, Any]:
    user = auth.current_user(request)
    return {"sessions": db.list_sessions(limit=limit, user_id=user["id"] if user else None)}


@app.get("/api/sessions/{session_id}")
def api_session_detail(session_id: str, request: Request) -> Dict[str, Any]:
    user = auth.current_user(request)
    s = db.get_session(session_id, user_id=user["id"] if user else None)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s


@app.get("/api/credentials")
def api_credentials(request: Request) -> Dict[str, Any]:
    user = auth.require_user(request)
    full = db.get_user(user["id"])
    assert full
    return auth.dashboard_credentials(full, request)


@app.post("/api/demo/seed")
def api_demo_seed(request: Request, replay: bool = True) -> Dict[str, Any]:
    """Replay simulated sticky sessions (~75% est.) — honest simulated labels."""
    user = auth.current_user(request)
    try:
        # Patch create_session via demo_seed which calls db.create_session —
        # we wrap by temporarily monkeypatching isn't needed; demo_seed updated
        # to accept user_id. Fallback: call then update.
        if replay:
            result = seed_from_harness(clear_previous=True)
        else:
            result = seed_from_latest_json_only()
        if user:
            # attribute freshly created demo sessions to this user
            with db.get_conn() as conn:
                for sid in result.get("sessions_created") or []:
                    conn.execute(
                        "UPDATE sessions SET user_id = ? WHERE id = ? AND (user_id IS NULL OR user_id = '')",
                        (user["id"], sid),
                    )
        return result
    except Exception as e:
        log.exception("demo seed failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Any:
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid JSON body") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    return await forward_chat_completions(request, body)


@app.post("/v1/trace")
async def v1_trace(request: Request) -> Dict[str, Any]:
    user, _ = auth.resolve_proxy_user(request)
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid JSON") from e
    return await ingest_trace(payload, user_id=user["id"] if user else None)


@app.post("/v1/trace/upload")
async def v1_trace_upload(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    user, _ = auth.resolve_proxy_user(request)
    raw = await file.read()
    try:
        import json

        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid JSON file: {e}") from e
    return await ingest_trace(payload, user_id=user["id"] if user else None)


@app.get("/v1/models")
def list_models(request: Request) -> Dict[str, Any]:
    # Soft-auth: prefer tg_ / session but allow listing for discovery
    m = get_settings().default_model
    return {
        "object": "list",
        "data": [
            {"id": m, "object": "model", "owned_by": "tokenguard"},
            {"id": "grok-4", "object": "model", "owned_by": "xai"},
            {"id": "grok-4.5", "object": "model", "owned_by": "xai"},
            {"id": "grok-4.6", "object": "model", "owned_by": "xai"},
            {"id": "grok-4.7", "object": "model", "owned_by": "xai"},
        ],
    }


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
