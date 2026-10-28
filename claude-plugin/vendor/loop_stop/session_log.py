"""Append-only JSONL session log of tool events + detector decisions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class SessionLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(
        self,
        *,
        tool: str,
        args: Dict[str, Any],
        decision: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "ts": time.time(),
            "tool": tool,
            "args": args,
            "decision": decision,
        }
        if meta:
            record["meta"] = meta
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def read_all(self) -> list:
        rows = []
        if not self.path.exists():
            return rows
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
