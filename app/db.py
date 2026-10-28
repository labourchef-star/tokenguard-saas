"""SQLite persistence — multi-tenant sessions/events/impact scoped by user_id."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from .config import DATA_DIR, DB_PATH


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  mode TEXT NOT NULL DEFAULT 'proxy',
  model TEXT,
  title TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  tokens_source TEXT NOT NULL DEFAULT 'estimate',
  tool_call_count INTEGER NOT NULL DEFAULT 0,
  loop_events_blocked INTEGER NOT NULL DEFAULT 0,
  tokens_avoided_est INTEGER NOT NULL DEFAULT 0,
  baseline_tool_calls INTEGER,
  with_stop_tool_calls INTEGER,
  meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,
  tool TEXT,
  args_json TEXT,
  decision_json TEXT,
  tokens_est INTEGER DEFAULT 0,
  detail TEXT,
  allowed INTEGER
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""

AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,
  api_key TEXT UNIQUE,
  upstream_api_key_blob TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

CREATE TABLE IF NOT EXISTS user_settings (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  grok_api_key_blob TEXT NOT NULL DEFAULT '',
  openai_api_key_blob TEXT NOT NULL DEFAULT '',
  upstream_api_key_blob TEXT NOT NULL DEFAULT '',
  openai_base_url TEXT NOT NULL DEFAULT '',
  claude_hook_installed INTEGER NOT NULL DEFAULT 0,
  preferred_client TEXT,
  updated_at REAL NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for older retail schemas."""
    # sessions.user_id
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "user_id" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

    # users.api_key / upstream_api_key_blob
    ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "api_key" not in ucols:
        conn.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)")
    if "upstream_api_key_blob" not in ucols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN upstream_api_key_blob TEXT NOT NULL DEFAULT ''"
        )

    # user_settings.upstream_api_key_blob
    try:
        scols = {
            r["name"] for r in conn.execute("PRAGMA table_info(user_settings)").fetchall()
        }
        if "upstream_api_key_blob" not in scols:
            conn.execute(
                "ALTER TABLE user_settings ADD COLUMN upstream_api_key_blob TEXT NOT NULL DEFAULT ''"
            )
    except sqlite3.OperationalError:
        pass

    # Backfill missing api_keys
    for row in conn.execute(
        "SELECT id FROM users WHERE api_key IS NULL OR api_key = ''"
    ).fetchall():
        import secrets

        key = "tg_" + secrets.token_urlsafe(24)
        conn.execute("UPDATE users SET api_key = ? WHERE id = ?", (key, row["id"]))


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.executescript(AUTH_SCHEMA)
        _migrate(conn)


def new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def create_session(
    *,
    mode: str = "proxy",
    model: str | None = None,
    title: str | None = None,
    session_id: str | None = None,
    meta: Optional[Dict[str, Any]] = None,
    user_id: str | None = None,
) -> str:
    sid = session_id or new_session_id()
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sessions
              (id, user_id, created_at, updated_at, mode, model, title, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                user_id,
                now,
                now,
                mode,
                model,
                title or f"{mode} session",
                json.dumps(meta or {}),
            ),
        )
    return sid


def touch_session(session_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (time.time(), session_id),
        )


def update_session_metrics(
    session_id: str,
    *,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    tokens_source: Optional[str] = None,
    tool_call_delta: int = 0,
    blocked_delta: int = 0,
    tokens_avoided_delta: int = 0,
    baseline_tool_calls: Optional[int] = None,
    with_stop_tool_calls: Optional[int] = None,
    model: Optional[str] = None,
    title: Optional[str] = None,
) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return
        sets = ["updated_at = ?"]
        vals: list[Any] = [time.time()]
        if tokens_in is not None:
            sets.append("tokens_in = tokens_in + ?")
            vals.append(tokens_in)
        if tokens_out is not None:
            sets.append("tokens_out = tokens_out + ?")
            vals.append(tokens_out)
        if tokens_source is not None:
            sets.append("tokens_source = ?")
            vals.append(tokens_source)
        if tool_call_delta:
            sets.append("tool_call_count = tool_call_count + ?")
            vals.append(tool_call_delta)
        if blocked_delta:
            sets.append("loop_events_blocked = loop_events_blocked + ?")
            vals.append(blocked_delta)
        if tokens_avoided_delta:
            sets.append("tokens_avoided_est = tokens_avoided_est + ?")
            vals.append(tokens_avoided_delta)
        if baseline_tool_calls is not None:
            sets.append("baseline_tool_calls = ?")
            vals.append(baseline_tool_calls)
        if with_stop_tool_calls is not None:
            sets.append("with_stop_tool_calls = ?")
            vals.append(with_stop_tool_calls)
        if model is not None:
            sets.append("model = ?")
            vals.append(model)
        if title is not None:
            sets.append("title = ?")
            vals.append(title)
        vals.append(session_id)
        conn.execute(
            f"UPDATE sessions SET {', '.join(sets)} WHERE id = ?",
            vals,
        )


def add_event(
    session_id: str,
    *,
    kind: str,
    tool: str | None = None,
    args: Any = None,
    decision: Any = None,
    tokens_est: int = 0,
    detail: str | None = None,
    allowed: bool | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO events
              (session_id, ts, kind, tool, args_json, decision_json, tokens_est, detail, allowed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                time.time(),
                kind,
                tool,
                json.dumps(args, default=str) if args is not None else None,
                json.dumps(decision, default=str) if decision is not None else None,
                tokens_est,
                detail,
                None if allowed is None else (1 if allowed else 0),
            ),
        )
    touch_session(session_id)


def list_sessions(
    limit: int = 100, *, user_id: str | None = None
) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT * FROM sessions
                WHERE user_id = ? OR (user_id IS NULL AND mode = 'demo')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [_session_dict(r) for r in rows]


def get_session(
    session_id: str, *, user_id: str | None = None
) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        if user_id and row["user_id"] and row["user_id"] != user_id:
            return None
        events = conn.execute(
            """
            SELECT * FROM events WHERE session_id = ? ORDER BY ts ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
    out = _session_dict(row)
    out["events"] = [_event_dict(e) for e in events]
    return out


def impact_summary(*, user_id: str | None = None) -> Dict[str, Any]:
    where = ""
    params: tuple = ()
    if user_id:
        where = "WHERE user_id = ? OR (user_id IS NULL AND mode = 'demo')"
        params = (user_id,)
    with get_conn() as conn:
        agg = conn.execute(
            f"""
            SELECT
              COUNT(*) AS sessions_counted,
              COALESCE(SUM(tokens_in), 0) AS tokens_in,
              COALESCE(SUM(tokens_out), 0) AS tokens_out,
              COALESCE(SUM(tokens_in + tokens_out), 0) AS tokens_used,
              COALESCE(SUM(tokens_avoided_est), 0) AS tokens_saved_est,
              COALESCE(SUM(tool_call_count), 0) AS tool_calls,
              COALESCE(SUM(loop_events_blocked), 0) AS loops_blocked,
              COALESCE(SUM(baseline_tool_calls), 0) AS baseline_tool_calls,
              COALESCE(SUM(with_stop_tool_calls), 0) AS with_stop_tool_calls
            FROM sessions
            {where}
            """,
            params,
        ).fetchone()
        by_mode = conn.execute(
            f"""
            SELECT mode, COUNT(*) AS n,
                   COALESCE(SUM(tokens_in + tokens_out), 0) AS tokens_used,
                   COALESCE(SUM(tokens_avoided_est), 0) AS tokens_saved_est,
                   COALESCE(SUM(loop_events_blocked), 0) AS loops_blocked
            FROM sessions {where} GROUP BY mode
            """,
            params,
        ).fetchall()
        recent = conn.execute(
            f"""
            SELECT id, title, mode, tokens_in, tokens_out, tokens_avoided_est,
                   loop_events_blocked, tool_call_count, tokens_source, created_at, user_id
            FROM sessions {where} ORDER BY created_at DESC LIMIT 20
            """,
            params,
        ).fetchall()

    used = int(agg["tokens_used"] or 0)
    saved = int(agg["tokens_saved_est"] or 0)
    denom = used + saved
    pct = round(100.0 * saved / denom, 1) if denom > 0 else 0.0

    return {
        "sessions_counted": int(agg["sessions_counted"] or 0),
        "tokens_used": used,
        "tokens_in": int(agg["tokens_in"] or 0),
        "tokens_out": int(agg["tokens_out"] or 0),
        "tokens_saved_est": saved,
        "pct_waste_reduction_est": pct,
        "tool_calls": int(agg["tool_calls"] or 0),
        "loops_blocked": int(agg["loops_blocked"] or 0),
        "baseline_tool_calls": int(agg["baseline_tool_calls"] or 0),
        "with_stop_tool_calls": int(agg["with_stop_tool_calls"] or 0),
        "by_mode": [dict(r) for r in by_mode],
        "recent_sessions": [_session_dict(r) for r in recent],
        "honesty": {
            "tokens_saved_label": "estimate",
            "note": (
                "Tokens saved are estimates (blocked tool calls × heuristic "
                "or baseline−with_stop deltas). Provider-reported usage is "
                "labeled when present; otherwise tiktoken/heuristic estimates. "
                "Demo mode is simulated (~75% est.) — labeled simulated."
            ),
        },
    }


def clear_demo_sessions(*, user_id: str | None = None) -> int:
    with get_conn() as conn:
        if user_id:
            ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM sessions WHERE mode = 'demo' AND (user_id = ? OR user_id IS NULL)",
                    (user_id,),
                ).fetchall()
            ]
        else:
            ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM sessions WHERE mode = 'demo'"
                ).fetchall()
            ]
        for sid in ids:
            conn.execute("DELETE FROM events WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        return len(ids)


def _session_dict(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    if "meta_json" in d and d["meta_json"]:
        try:
            d["meta"] = json.loads(d["meta_json"])
        except json.JSONDecodeError:
            d["meta"] = {}
    d.pop("meta_json", None)
    return d


def _event_dict(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    for key, out in (("args_json", "args"), ("decision_json", "decision")):
        raw = d.pop(key, None)
        if raw:
            try:
                d[out] = json.loads(raw)
            except json.JSONDecodeError:
                d[out] = raw
        else:
            d[out] = None
    if d.get("allowed") is not None:
        d["allowed"] = bool(d["allowed"])
    return d


def create_user(
    *,
    email: str,
    password_hash: str,
    name: str = "",
    api_key: str | None = None,
) -> str:
    uid = uuid.uuid4().hex[:16]
    now = time.time()
    if not api_key:
        import secrets

        api_key = "tg_" + secrets.token_urlsafe(24)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, name, password_hash, api_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uid, email, name, password_hash, api_key, now),
        )
        conn.execute(
            """
            INSERT INTO user_settings (user_id, updated_at)
            VALUES (?, ?)
            """,
            (uid, now),
        )
    return uid


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE api_key = ?", (api_key,)
        ).fetchone()
    return dict(row) if row else None


def set_user_api_key(user_id: str, api_key: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET api_key = ? WHERE id = ?", (api_key, user_id)
        )


def set_user_upstream_blob(user_id: str, blob: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET upstream_api_key_blob = ? WHERE id = ?",
            (blob, user_id),
        )


def create_auth_session(*, token: str, user_id: str, expires_at: float) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, time.time(), expires_at),
        )


def get_auth_session(token: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM auth_sessions WHERE token = ?", (token,)
        ).fetchone()
    return dict(row) if row else None


def delete_auth_session(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))


def get_user_settings(user_id: str) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO user_settings (user_id, updated_at) VALUES (?, ?)",
                (user_id, time.time()),
            )
            row = conn.execute(
                "SELECT * FROM user_settings WHERE user_id = ?", (user_id,)
            ).fetchone()
    d = dict(row)
    if d.get("meta_json"):
        try:
            d["meta"] = json.loads(d["meta_json"])
        except json.JSONDecodeError:
            d["meta"] = {}
    d.pop("meta_json", None)
    d["claude_hook_installed"] = bool(d.get("claude_hook_installed"))
    return d


def update_user_settings(
    user_id: str,
    *,
    grok_api_key_blob: Optional[str] = None,
    openai_api_key_blob: Optional[str] = None,
    upstream_api_key_blob: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    claude_hook_installed: Optional[bool] = None,
    preferred_client: Optional[str] = None,
) -> Dict[str, Any]:
    get_user_settings(user_id)
    sets = ["updated_at = ?"]
    vals: list[Any] = [time.time()]
    if grok_api_key_blob is not None:
        sets.append("grok_api_key_blob = ?")
        vals.append(grok_api_key_blob)
    if openai_api_key_blob is not None:
        sets.append("openai_api_key_blob = ?")
        vals.append(openai_api_key_blob)
    if upstream_api_key_blob is not None:
        sets.append("upstream_api_key_blob = ?")
        vals.append(upstream_api_key_blob)
        set_user_upstream_blob(user_id, upstream_api_key_blob)
    if openai_base_url is not None:
        sets.append("openai_base_url = ?")
        vals.append(openai_base_url)
    if claude_hook_installed is not None:
        sets.append("claude_hook_installed = ?")
        vals.append(1 if claude_hook_installed else 0)
    if preferred_client is not None:
        sets.append("preferred_client = ?")
        vals.append(preferred_client)
    vals.append(user_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE user_settings SET {', '.join(sets)} WHERE user_id = ?",
            vals,
        )
    return get_user_settings(user_id)
