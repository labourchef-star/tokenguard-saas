"""Deterministic coding-agent simulator that intentionally loops.

No LLM API keys required. Sticky failure modes reproduce the loops that
loop_stop is designed to catch; when the detector blocks, the agent
switches to a correct recovery action so tasks can still pass with
the stopper enabled.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loop_stop.detector import LoopDetector, Decision, DecisionKind
from loop_stop.session_log import SessionLog


TASKS_ROOT = Path(__file__).resolve().parent / "tasks"
PKG_ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = PKG_ROOT / ".venv" / "bin"


def _run_env() -> dict:
    """Prefer package .venv so `python -m pytest` works without global pytest."""
    env = os.environ.copy()
    if VENV_BIN.is_dir():
        env["PATH"] = str(VENV_BIN) + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(PKG_ROOT / ".venv")
    return env



@dataclass
class ToolCallRecord:
    tool: str
    args: Dict[str, Any]
    allowed: bool
    reason: str = ""
    rule: str = ""
    exit_code: Optional[int] = None
    output: str = ""


@dataclass
class RunResult:
    task_id: str
    mode: str  # "baseline" | "loop_stop"
    tool_call_count: int
    loop_events_blocked: int
    task_pass: bool
    wall_ms: int
    calls: List[ToolCallRecord] = field(default_factory=list)
    log_path: str = ""
    simulated: bool = True


class FakeAgent:
    """Scripted agent with sticky loops + recovery after a detector block."""

    def __init__(
        self,
        task_dir: Path,
        work_dir: Path,
        *,
        detector: Optional[LoopDetector] = None,
        session_log: Optional[SessionLog] = None,
        max_steps: int = 24,
    ) -> None:
        self.task_dir = Path(task_dir)
        self.work_dir = Path(work_dir)
        self.detector = detector
        self.session_log = session_log
        self.max_steps = max_steps
        self.meta = json.loads((self.task_dir / "task.json").read_text(encoding="utf-8"))
        self.calls: List[ToolCallRecord] = []
        self.blocked = 0
        self._recovered = False

    def _decide(self, tool: str, args: Dict[str, Any]) -> Decision:
        if self.detector is None:
            return Decision(kind=DecisionKind.ALLOW, reason="detector_off")
        return self.detector.check(tool, args)

    def _log(self, tool: str, args: Dict[str, Any], decision: Decision) -> None:
        if self.session_log:
            self.session_log.append(
                tool=tool,
                args=args,
                decision=decision.to_dict(),
                meta={"task": self.meta["id"]},
            )

    def _tool(self, tool: str, args: Dict[str, Any]) -> ToolCallRecord:
        decision = self._decide(tool, args)
        self._log(tool, args, decision)
        if not decision.allowed:
            self.blocked += 1
            rec = ToolCallRecord(
                tool=tool,
                args=args,
                allowed=False,
                reason=decision.reason,
                rule=decision.rule,
            )
            self.calls.append(rec)
            return rec

        exit_code = 0
        output = ""
        if tool.lower() == "read":
            path = self.work_dir / args["path"]
            try:
                output = path.read_text(encoding="utf-8")
            except FileNotFoundError:
                exit_code = 1
                output = f"ENOENT: {path}"
        elif tool.lower() == "bash":
            cmd = args["command"]
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                env=_run_env(),
            )
            exit_code = proc.returncode
            output = (proc.stdout or "") + (proc.stderr or "")
            if self.detector is not None:
                self.detector.record_outcome("Bash", args, exit_code, ok=(exit_code == 0))
        elif tool.lower() == "edit":
            path = self.work_dir / args["path"]
            path.write_text(args["content"], encoding="utf-8")
            output = f"wrote {args['path']}"
        else:
            exit_code = 1
            output = f"unknown tool {tool}"

        rec = ToolCallRecord(
            tool=tool,
            args=args,
            allowed=True,
            reason=decision.reason,
            exit_code=exit_code,
            output=output[:500],
        )
        self.calls.append(rec)
        return rec

    def _acceptance_pass(self) -> bool:
        proc = subprocess.run(
            self.meta["acceptance"],
            shell=True,
            cwd=str(self.work_dir),
            capture_output=True,
            text=True,
            env=_run_env(),
        )
        return proc.returncode == 0

    def _write_source(self, text: str) -> None:
        src = self.meta["source_file"]
        (self.work_dir / src).write_text(text, encoding="utf-8")
        self._tool("Edit", {"path": src, "content": text})

    def _apply_correct_fix(self) -> None:
        src = self.meta["source_file"]
        path = self.work_dir / src
        text = path.read_text(encoding="utf-8")
        sticky = self.meta["sticky_mode"]
        if sticky == "reread_then_wrong_edit":
            text = text.replace("for i in range(1, n):", "for i in range(1, n+1):")
            text = text.replace("for i in range(1, n):  # attempted fix", "for i in range(1, n+1):")
        elif sticky == "failing_pytest_retry":
            # Replace any wrong clamp or append the correct one
            if "def clamp" in text:
                # strip existing clamp definitions
                lines = text.splitlines()
                out = []
                skip = False
                for line in lines:
                    if line.startswith("def clamp"):
                        skip = True
                        continue
                    if skip:
                        if line.startswith("def ") or (
                            line.strip() and not line.startswith(" ") and not line.startswith("\t")
                        ):
                            skip = False
                            out.append(line)
                        continue
                    out.append(line)
                text = "\n".join(out).rstrip() + "\n\n" + self.meta["fix_snippet"] + "\n"
            else:
                text = text.rstrip() + "\n\n" + self.meta["fix_snippet"] + "\n"
        elif sticky == "ping_pong_read_run":
            text = text.replace("from mathy_typo import square", "from mathy import square")
            text = text.replace("from mathy_wrong import square", "from mathy import square")
        self._write_source(text)
        self._recovered = True

    def run(self) -> RunResult:
        t0 = time.perf_counter()
        sticky = self.meta["sticky_mode"]
        src = self.meta["source_file"]
        test_cmd = self.meta["acceptance"]

        if sticky == "reread_then_wrong_edit":
            # Sticky: re-read the same file forever; never fix unless blocked.
            for _ in range(self.max_steps):
                rec = self._tool("Read", {"path": src})
                if not rec.allowed:
                    self._apply_correct_fix()
                    self._tool("Bash", {"command": test_cmd})
                    break

        elif sticky == "failing_pytest_retry":
            # Sticky: retry the same failing pytest; never fix unless blocked.
            for _ in range(self.max_steps):
                rec = self._tool("Bash", {"command": test_cmd})
                if not rec.allowed:
                    self._apply_correct_fix()
                    self._tool("Bash", {"command": test_cmd})
                    break
                if rec.exit_code == 0:
                    break

        elif sticky == "ping_pong_read_run":
            # Sticky: alternate two benign Bash commands so fingerprints
            # ping-pong (rule fires at 2N) without tripping repeated_read /
            # failing_bash first; never fix unless blocked.
            for i in range(self.max_steps):
                cmd = "echo ping" if i % 2 == 0 else "echo pong"
                rec = self._tool("Bash", {"command": cmd})
                if not rec.allowed:
                    self._apply_correct_fix()
                    self._tool("Bash", {"command": test_cmd})
                    break

        else:
            raise ValueError(f"unknown sticky_mode {sticky}")

        passed = self._acceptance_pass()
        wall_ms = int((time.perf_counter() - t0) * 1000)
        return RunResult(
            task_id=self.meta["id"],
            mode="loop_stop" if self.detector is not None else "baseline",
            tool_call_count=len(self.calls),
            loop_events_blocked=self.blocked,
            task_pass=passed,
            wall_ms=wall_ms,
            calls=self.calls,
            simulated=True,
        )


def prepare_work_dir(task_id: str, parent: Path) -> Path:
    src = TASKS_ROOT / task_id
    if not src.is_dir():
        raise FileNotFoundError(f"unknown task {task_id}")
    dest = parent / task_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def list_task_ids() -> List[str]:
    return sorted(
        p.name
        for p in TASKS_ROOT.iterdir()
        if p.is_dir() and (p / "task.json").exists()
    )
