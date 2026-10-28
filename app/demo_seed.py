"""Seed the dashboard from loop-stop-demo harness (simulated sticky sessions)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from . import db
from .config import DEMO_ROOT, TOKENS_PER_TOOL_ESTIMATE, get_settings

# Heuristic: each tool call in the simulated harness ≈ this many tokens of context churn
TOKENS_PER_SIM_CALL = TOKENS_PER_TOOL_ESTIMATE


def _ensure_demo_path() -> Path:
    root = Path(DEMO_ROOT)
    if not (root / "loop_stop").is_dir():
        raise FileNotFoundError(
            f"loop-stop-demo not found at {root}. Set LOOP_STOP_DEMO_ROOT."
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def seed_from_harness(*, clear_previous: bool = True, n: int | None = None, user_id: str | None = None) -> Dict[str, Any]:
    """Run FakeAgent before/after (or reuse latest.json) and write demo sessions."""
    root = _ensure_demo_path()
    from loop_stop.detector import LoopDetector
    from loop_stop.session_log import SessionLog
    from harness.fake_agent import FakeAgent, prepare_work_dir, list_task_ids

    if clear_previous:
        cleared = db.clear_demo_sessions(user_id=user_id)
    else:
        cleared = 0

    settings = get_settings()
    threshold = n or settings.loop_n
    tasks_dir = root / "harness" / "tasks"
    task_ids = list_task_ids()
    created: List[str] = []

    with tempfile.TemporaryDirectory(prefix="loop-stop-app-demo-") as tmp:
        tmp_path = Path(tmp)
        for task_id in task_ids:
            task_dir = tasks_dir / task_id
            meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))

            # baseline
            work_b = prepare_work_dir(task_id, tmp_path / "baseline")
            agent_b = FakeAgent(task_dir, work_b, detector=None, max_steps=24)
            res_b = agent_b.run()

            # with stop
            work_s = prepare_work_dir(task_id, tmp_path / "stop")
            det = LoopDetector(n=threshold)
            log_s = SessionLog(tmp_path / f"{task_id}_stop.jsonl")
            agent_s = FakeAgent(
                task_dir, work_s, detector=det, session_log=log_s, max_steps=24
            )
            res_s = agent_s.run()

            sid = db.create_session(
                mode="demo",
                model="simulated-fake-agent",
                title=f"demo:{task_id}",
                user_id=user_id,
                meta={
                    "task_id": task_id,
                    "sticky_mode": meta.get("sticky_mode"),
                    "simulated": True,
                    "task_pass_baseline": res_b.task_pass,
                    "task_pass_loop_stop": res_s.task_pass,
                },
            )

            # Tokens: estimate from tool-call counts (labeled estimate)
            tokens_used = res_s.tool_call_count * TOKENS_PER_SIM_CALL
            # "tokens avoided" ≈ calls we didn't make vs baseline
            avoided_calls = max(0, res_b.tool_call_count - res_s.tool_call_count)
            # Also credit blocked events directly
            avoided = max(
                avoided_calls * TOKENS_PER_SIM_CALL,
                res_s.loop_events_blocked * TOKENS_PER_SIM_CALL,
            )

            # Timeline from with-stop run
            for call in res_s.calls:
                db.add_event(
                    sid,
                    kind="tool_blocked" if not call.allowed else "tool_call",
                    tool=call.tool,
                    args=call.args,
                    decision={
                        "allowed": call.allowed,
                        "reason": call.reason,
                        "rule": call.rule,
                    },
                    tokens_est=TOKENS_PER_SIM_CALL if not call.allowed else TOKENS_PER_SIM_CALL // 4,
                    detail=call.reason or call.output,
                    allowed=call.allowed,
                )

            db.add_event(
                sid,
                kind="note",
                detail=(
                    f"SIMULATED before/after: baseline_calls={res_b.tool_call_count} "
                    f"with_stop_calls={res_s.tool_call_count} blocked={res_s.loop_events_blocked} "
                    f"pass_baseline={res_b.task_pass} pass_stop={res_s.task_pass}"
                ),
                allowed=True,
            )

            db.update_session_metrics(
                sid,
                tokens_in=tokens_used // 2,
                tokens_out=tokens_used - tokens_used // 2,
                tokens_source="estimate",
                tool_call_delta=res_s.tool_call_count,
                blocked_delta=res_s.loop_events_blocked,
                tokens_avoided_delta=avoided,
                baseline_tool_calls=res_b.tool_call_count,
                with_stop_tool_calls=res_s.tool_call_count,
                model="simulated-fake-agent",
            )
            created.append(sid)

    # Also try to attach summary from results/latest.json if present
    latest = root / "results" / "latest.json"
    summary = None
    if latest.exists():
        try:
            summary = json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = None

    return {
        "ok": True,
        "cleared_demo_sessions": cleared,
        "sessions_created": created,
        "n_threshold": threshold,
        "simulated": True,
        "note": (
            "Demo sessions are SIMULATED (FakeAgent, $0). Token figures are "
            "estimates labeled as such. Hosted SaaS demo — estimates labeled simulated."
        ),
        "harness_latest_summary": (summary or {}).get("summary"),
    }


def seed_from_latest_json_only(*, user_id: str | None = None) -> Dict[str, Any]:
    """Lighter seed: read results/latest.json + jsonl without re-running harness."""
    root = _ensure_demo_path()
    latest_path = root / "results" / "latest.json"
    if not latest_path.exists():
        return seed_from_harness(clear_previous=True)

    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    cleared = db.clear_demo_sessions()
    created = []
    for pair in latest.get("tasks") or []:
        b = pair.get("baseline") or {}
        s = pair.get("loop_stop") or {}
        task_id = s.get("task_id") or b.get("task_id") or "unknown"
        sid = db.create_session(
            mode="demo",
            model="simulated-fake-agent",
            title=f"demo:{task_id}",
            user_id=user_id,
            meta={"task_id": task_id, "simulated": True, "from": "latest.json"},
        )
        calls_s = int(s.get("tool_call_count") or 0)
        calls_b = int(b.get("tool_call_count") or 0)
        blocked = int(s.get("loop_events_blocked") or 0)
        avoided = max(0, calls_b - calls_s) * TOKENS_PER_SIM_CALL
        tokens_used = calls_s * TOKENS_PER_SIM_CALL

        # Prefer jsonl timeline if available
        jsonl = root / "results" / f"{task_id}_loop_stop.jsonl"
        if jsonl.exists():
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                dec = row.get("decision") or {}
                allowed = dec.get("allowed", True)
                db.add_event(
                    sid,
                    kind="tool_blocked" if not allowed else "tool_call",
                    tool=row.get("tool"),
                    args=row.get("args"),
                    decision=dec,
                    detail=dec.get("reason"),
                    allowed=allowed,
                    tokens_est=TOKENS_PER_SIM_CALL if not allowed else TOKENS_PER_SIM_CALL // 4,
                )
        else:
            db.add_event(
                sid,
                kind="note",
                detail=f"from latest.json only; blocked={blocked}",
                allowed=True,
            )

        db.update_session_metrics(
            sid,
            tokens_in=tokens_used // 2,
            tokens_out=tokens_used - tokens_used // 2,
            tokens_source="estimate",
            tool_call_delta=calls_s,
            blocked_delta=blocked,
            tokens_avoided_delta=avoided,
            baseline_tool_calls=calls_b,
            with_stop_tool_calls=calls_s,
        )
        created.append(sid)

    return {
        "ok": True,
        "cleared_demo_sessions": cleared,
        "sessions_created": created,
        "simulated": True,
        "source": str(latest_path),
        "note": "Seeded from results/latest.json (SIMULATED). Token figures are estimates.",
        "harness_latest_summary": latest.get("summary"),
    }
