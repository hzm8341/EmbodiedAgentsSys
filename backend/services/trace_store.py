"""Append-only trace storage with replay helpers."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class TraceStore:
    def __init__(self, root_dir: str | None = None) -> None:
        base_dir = root_dir or os.getenv("TRACE_STORE_DIR", "backend/runtime/traces")
        self.root = Path(base_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def _trace_path(self, trace_id: str) -> Path:
        return self.root / f"{trace_id}.jsonl"

    def append_event(
        self, trace_id: str, event: dict[str, Any], operator: str | None = None
    ) -> None:
        line = json.dumps(
            {
                "kind": "event",
                "trace_id": trace_id,
                "recorded_at": time.time(),
                "operator": operator,
                **event,
            },
            ensure_ascii=False,
        )
        with self._trace_path(trace_id).open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def append_result(
        self,
        trace_id: str,
        *,
        task: str,
        result: dict[str, Any],
        operator: str | None = None,
    ) -> None:
        line = json.dumps(
            {
                "kind": "result",
                "trace_id": trace_id,
                "recorded_at": time.time(),
                "task": task,
                "operator": operator,
                "result": result,
            },
            ensure_ascii=False,
        )
        with self._trace_path(trace_id).open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        path = self._trace_path(trace_id)
        if not path.exists():
            return None
        events: list[dict[str, Any]] = []
        result: dict[str, Any] | None = None
        task: str | None = None
        operator: str | None = None
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                if row.get("kind") == "event":
                    events.append(row)
                elif row.get("kind") == "result":
                    result = row.get("result", {})
                    task = row.get("task")
                    operator = row.get("operator")
        return {
            "trace_id": trace_id,
            "task": task,
            "operator": operator,
            "events": events,
            "result": result,
        }

    def replay(self, trace_id: str) -> list[dict[str, Any]] | None:
        trace = self.get_trace(trace_id)
        if trace is None:
            return None
        return trace["events"]


trace_store = TraceStore()
