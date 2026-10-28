"""Runtime settings for TokenGuard hosted SaaS."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent

# Persist SQLite on volume in production (DATA_DIR=/data); local default ./data
DATA_DIR = Path(os.environ.get("DATA_DIR") or os.environ.get("TOKENGUARD_DATA") or str(APP_ROOT / "data"))
DB_PATH = DATA_DIR / "tokenguard.db"
ONBOARDING_PATH = DATA_DIR / "onboarding.json"

VENDOR_ROOT = Path(
    os.environ.get(
        "TOKENGUARD_VENDOR_ROOT",
        os.environ.get("LOOP_STOP_VENDOR_ROOT", str(APP_ROOT / "vendor")),
    )
)
_sibling = APP_ROOT.parent / "loop-stop-demo"
DEMO_ROOT = Path(
    os.environ.get(
        "TOKENGUARD_DEMO_ROOT",
        os.environ.get(
            "LOOP_STOP_DEMO_ROOT",
            str(VENDOR_ROOT if (VENDOR_ROOT / "loop_stop").is_dir() else _sibling),
        ),
    )
)

DEFAULT_UPSTREAM = os.environ.get("DEFAULT_UPSTREAM", "https://api.x.ai/v1")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "grok-4.7")
DEFAULT_HOST = os.environ.get("HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("PORT", "8080"))
TOKENS_PER_TOOL_ESTIMATE = 800
TOKENS_PER_MESSAGE_CHAR = 0.25

PRODUCT_NAME = "TokenGuard"
PRODUCT_SLUG = "tokenguard"
BILLING_MODE = os.environ.get("BILLING_MODE", "free")

# Public URL used in UI copy-paste snippets (no trailing slash)
PUBLIC_BASE_URL = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")


def public_base_url(request_base: str | None = None) -> str:
    """Prefer PUBLIC_BASE_URL env; fall back to request-derived base."""
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    if request_base:
        return request_base.rstrip("/")
    return f"http://127.0.0.1:{DEFAULT_PORT}"


def get_api_key() -> str | None:
    """Process-level fallback upstream key (optional shared BYOK for demos)."""
    for name in ("XAI_API_KEY", "GROK_API_KEY", "OPENAI_API_KEY"):
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return None


def has_api_key() -> bool:
    return get_api_key() is not None


def is_production() -> bool:
    return (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "").lower() in (
        "prod",
        "production",
    )


@dataclass
class Settings:
    upstream_base_url: str = DEFAULT_UPSTREAM
    default_model: str = DEFAULT_MODEL
    loop_n: int = 3
    block_loops: bool = True
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    def to_public_dict(self) -> dict:
        return {
            "upstream_base_url": self.upstream_base_url,
            "default_model": self.default_model,
            "loop_n": self.loop_n,
            "block_loops": self.block_loops,
            "host": self.host,
            "port": self.port,
            "api_key_configured": has_api_key(),
            "api_key_source": (
                "XAI_API_KEY"
                if (os.environ.get("XAI_API_KEY") or "").strip()
                else (
                    "GROK_API_KEY"
                    if (os.environ.get("GROK_API_KEY") or "").strip()
                    else (
                        "OPENAI_API_KEY"
                        if (os.environ.get("OPENAI_API_KEY") or "").strip()
                        else None
                    )
                )
            ),
            "product_name": PRODUCT_NAME,
            "billing_mode": BILLING_MODE,
            "public_base_url": PUBLIC_BASE_URL or None,
            "note": "Per-user upstream keys are encrypted at rest. Process env keys are optional fallback.",
        }


_settings = Settings()


def get_settings() -> Settings:
    return _settings


def update_settings(**kwargs) -> Settings:
    global _settings
    for k, v in kwargs.items():
        if hasattr(_settings, k) and v is not None:
            setattr(_settings, k, v)
    return _settings


def load_onboarding() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ONBOARDING_PATH.exists():
        return {
            "completed": False,
            "client": None,
            "demo_mode": False,
            "step": "welcome",
        }
    try:
        return json.loads(ONBOARDING_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"completed": False, "client": None, "demo_mode": False, "step": "welcome"}


def save_onboarding(data: dict) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = load_onboarding()
    current.update({k: v for k, v in data.items() if v is not None})
    ONBOARDING_PATH.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return current
