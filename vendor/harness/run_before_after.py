"""Run each mini-task twice: baseline (detector off) vs loop-stop on.

Records tool_call_count, loop_events_blocked, task_pass, wall_ms.
Writes results/latest.json and results/latest.md.

Falsifier: if pass_rate_with_stop < pass_rate_baseline - 0.10 → DEMO_FAIL_QUALITY.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

from loop_stop.detector import LoopDetector
from loop_stop.session_log import SessionLog
from harness.fake_agent import FakeAgent, prepare_work_dir, list_task_ids, RunResult

RESULTS_DIR = PKG_ROOT / "results"
TASKS_DIR = PKG_ROOT / "harness" / "tasks"


def _row(res: RunResult) -> dict:
    return {
        "task_id": res.task_id,
        "mode": res.mode,
        "tool_call_count": res.tool_call_count,
        "loop_events_blocked": res.loop_events_blocked,
        "task_pass": res.task_pass,
        "wall_ms": res.wall_ms,
        "simulated": res.simulated,
    }


def run_suite(n: int = 3, max_steps: int = 24) -> dict:
    task_ids = list_task_ids()
    if not task_ids:
        raise RuntimeError("no tasks found under harness/tasks/")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    with tempfile.TemporaryDirectory(prefix="loop-stop-demo-") as tmp:
        tmp_path = Path(tmp)
        for task_id in task_ids:
            task_dir = TASKS_DIR / task_id

            # --- baseline (detector off) ---
            work_b = prepare_work_dir(task_id, tmp_path / "baseline")
            log_b = SessionLog(RESULTS_DIR / f"{task_id}_baseline.jsonl")
            log_b.path.write_text("", encoding="utf-8")
            agent_b = FakeAgent(
                task_dir,
                work_b,
                detector=None,
                session_log=log_b,
                max_steps=max_steps,
            )
            res_b = agent_b.run()

            # --- loop_stop on ---
            work_s = prepare_work_dir(task_id, tmp_path / "stop")
            log_s = SessionLog(RESULTS_DIR / f"{task_id}_loop_stop.jsonl")
            log_s.path.write_text("", encoding="utf-8")
            det = LoopDetector(n=n)
            agent_s = FakeAgent(
                task_dir,
                work_s,
                detector=det,
                session_log=log_s,
                max_steps=max_steps,
            )
            res_s = agent_s.run()

            rows.append({"baseline": _row(res_b), "loop_stop": _row(res_s)})

    baseline_passes = sum(1 for r in rows if r["baseline"]["task_pass"])
    stop_passes = sum(1 for r in rows if r["loop_stop"]["task_pass"])
    n_tasks = len(rows)
    pass_rate_baseline = baseline_passes / n_tasks
    pass_rate_stop = stop_passes / n_tasks
    quality_fail = pass_rate_stop < (pass_rate_baseline - 0.10)
    falsifier = "DEMO_FAIL_QUALITY" if quality_fail else "OK"

    return {
        "mode": "simulated",
        "api_spend_usd": 0.0,
        "n_threshold": n,
        "tasks": rows,
        "summary": {
            "n_tasks": n_tasks,
            "baseline_passes": baseline_passes,
            "loop_stop_passes": stop_passes,
            "pass_rate_baseline": round(pass_rate_baseline, 4),
            "pass_rate_loop_stop": round(pass_rate_stop, 4),
            "total_tool_calls_baseline": sum(
                r["baseline"]["tool_call_count"] for r in rows
            ),
            "total_tool_calls_loop_stop": sum(
                r["loop_stop"]["tool_call_count"] for r in rows
            ),
            "total_loop_events_blocked": sum(
                r["loop_stop"]["loop_events_blocked"] for r in rows
            ),
            "falsifier": falsifier,
            "quality_falsifier_tripped": quality_fail,
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": (
            "SIMULATED results from FakeAgent (no LLM API). "
            "Do not invent savings %. Label as simulated when presenting."
        ),
    }


def _to_markdown(data: dict) -> str:
    s = data["summary"]
    lines = [
        "# loop-stop-demo before/after results",
        "",
        f"**Mode:** `{data['mode']}` (not live API)",
        f"**API spend:** ${data['api_spend_usd']:.2f}",
        f"**Threshold N:** {data['n_threshold']}",
        f"**Falsifier:** `{s['falsifier']}`"
        + (
            " — QUALITY REGRESSION"
            if s["quality_falsifier_tripped"]
            else " — no quality regression"
        ),
        "",
        "## Summary",
        "",
        "| Metric | Baseline | Loop-stop |",
        "| --- | ---: | ---: |",
        f"| Tasks passed | {s['baseline_passes']}/{s['n_tasks']} | {s['loop_stop_passes']}/{s['n_tasks']} |",
        f"| Pass rate | {s['pass_rate_baseline']:.0%} | {s['pass_rate_loop_stop']:.0%} |",
        f"| Total tool calls | {s['total_tool_calls_baseline']} | {s['total_tool_calls_loop_stop']} |",
        f"| Loop events blocked | 0 | {s['total_loop_events_blocked']} |",
        "",
        "## Per-task",
        "",
        "| Task | Baseline calls | Baseline pass | Stop calls | Stop blocked | Stop pass |",
        "| --- | ---: | :---: | ---: | ---: | :---: |",
    ]
    for pair in data["tasks"]:
        b, st = pair["baseline"], pair["loop_stop"]
        lines.append(
            f"| {b['task_id']} | {b['tool_call_count']} | "
            f"{'yes' if b['task_pass'] else 'no'} | "
            f"{st['tool_call_count']} | {st['loop_events_blocked']} | "
            f"{'yes' if st['task_pass'] else 'no'} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        data["note"],
        "",
        "Money Engine Pass is still **Fail**. This package is off-engine R&D.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(data: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / "latest.json"
    md_path = RESULTS_DIR / "latest.md"
    json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(data), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


def main() -> int:
    data = run_suite()
    write_outputs(data)
    print(json.dumps(data["summary"], indent=2))
    return 0 if not data["summary"]["quality_falsifier_tripped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
