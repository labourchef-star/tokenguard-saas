"""TokenGuard auth: password hashing, session cookies, Fernet secrets, tg_ API keys."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, Response

from . import db
from .config import DATA_DIR, is_production, public_base_url

SESSION_COOKIE = "tg_session"
SESSION_DAYS = 30
PBKDF2_ITERATIONS = 120_000


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a url-safe 32-byte Fernet key from an arbitrary secret string."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _token_guard_secret() -> str:
    """
    TOKENGUARD_SECRET from env.
    Local/dev: auto-generate and persist under DATA_DIR if missing.
    Production: required via env (no auto-create).
    """
    env = (os.environ.get("TOKENGUARD_SECRET") or "").strip()
    if env:
        return env
    if is_production():
        raise RuntimeError(
            "TOKENGUARD_SECRET is required in production. "
            "Set a long random secret before starting the server."
        )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "token_guard_secret.key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raw = secrets.token_urlsafe(48)
    path.write_text(raw + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return raw


def _fernet() -> Fernet:
    return Fernet(_derive_fernet_key(_token_guard_secret()))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def encrypt_secret(plain: str) -> str:
    """Encrypt a user upstream API key with Fernet(TOKENGUARD_SECRET)."""
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(blob: str) -> str:
    if not blob:
        return ""
    try:
        return _fernet().decrypt(blob.encode("ascii")).decode("utf-8")
    except (InvalidToken, Exception):
        return ""


# Back-compat aliases used by older retail call sites
def obfuscate_secret(plain: str) -> str:
    return encrypt_secret(plain)


def deobfuscate_secret(blob: str) -> str:
    return decrypt_secret(blob)


def mask_secret(plain: str) -> str:
    if not plain:
        return ""
    if len(plain) <= 8:
        return "••••••••"
    return plain[:4] + "…" + plain[-4:]


def generate_api_key() -> str:
    """Hosted TokenGuard API key: tg_<urlsafe>."""
    return "tg_" + secrets.token_urlsafe(24)


def create_user(email: str, password: str, name: str = "") -> Dict[str, Any]:
    email = (email or "").strip().lower()
    name = (name or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(password or "") < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    api_key = generate_api_key()
    uid = db.create_user(
        email=email,
        password_hash=hash_password(password),
        name=name,
        api_key=api_key,
    )
    user = db.get_user(uid)
    assert user is not None
    return user


def authenticate(email: str, password: str) -> Dict[str, Any]:
    email = (email or "").strip().lower()
    user = db.get_user_by_email(email)
    if not user or not verify_password(password or "", user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return user


def start_session(response: Response, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = time.time() + SESSION_DAYS * 86400
    db.create_auth_session(token=token, user_id=user_id, expires_at=expires)
    secure = is_production() or (os.environ.get("PUBLIC_BASE_URL") or "").startswith("https://")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_DAYS * 86400,
        path="/",
        secure=secure,
    )
    return token


def end_session(request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.delete_auth_session(token)
    response.delete_cookie(SESSION_COOKIE, path="/")


def current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = db.get_auth_session(token)
    if not row:
        return None
    if float(row["expires_at"]) < time.time():
        db.delete_auth_session(token)
        return None
    user = db.get_user(row["user_id"])
    if not user:
        return None
    return public_user(user)


def require_user(request: Request) -> Dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def public_user(user: Dict[str, Any], *, include_api_key: bool = True) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name") or "",
        "created_at": user.get("created_at"),
    }
    if include_api_key and user.get("api_key"):
        out["api_key"] = user["api_key"]
    return out


def resolve_bearer_user(request: Request) -> Optional[Dict[str, Any]]:
    """Authenticate via Authorization: Bearer tg_... (or raw tg_...)."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    elif auth.startswith("tg_"):
        token = auth.strip()
    if not token.startswith("tg_"):
        return None
    user = db.get_user_by_api_key(token)
    if not user:
        return None
    return public_user(user)


def resolve_proxy_user(request: Request) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Resolve tenant for /v1 routes.
    Prefer Bearer tg_..., else session cookie (browser demo).
    Returns (user_public_or_none, auth_mode).
    """
    bearer = resolve_bearer_user(request)
    if bearer:
        return bearer, "api_key"
    cookie_user = current_user(request)
    if cookie_user:
        return cookie_user, "session"
    return None, "none"


def get_user_upstream_key(user_id: str) -> Optional[str]:
    """Decrypt per-user BYOK (grok/openai blob), else process env fallback."""
    s = db.get_user_settings(user_id)
    for blob_key in ("grok_api_key_blob", "openai_api_key_blob", "upstream_api_key_blob"):
        plain = decrypt_secret(s.get(blob_key) or "")
        if plain:
            return plain
    # also check users.upstream_api_key_blob if present
    user = db.get_user(user_id)
    if user:
        plain = decrypt_secret(user.get("upstream_api_key_blob") or "")
        if plain:
            return plain
    from .config import get_api_key

    return get_api_key()


def rotate_api_key(user_id: str) -> str:
    new_key = generate_api_key()
    db.set_user_api_key(user_id, new_key)
    return new_key


def dashboard_credentials(user: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """base_url + api_key shown after signup."""
    base = public_base_url(str(request.base_url).rstrip("/"))
    full = db.get_user(user["id"]) or user
    return {
        "base_url": f"{base}/v1",
        "api_key": full.get("api_key") or "",
        "public_base_url": base,
        "authorization_header": f"Bearer {full.get('api_key') or ''}",
    }
