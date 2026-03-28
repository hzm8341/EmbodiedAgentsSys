"""Persistent failure log — append-only file store for task execution failures.

Separate from RobotMemoryState (which is in-memory per task). This log
persists across sessions and feeds future planning and training.

Records are stored as newline-delimited JSON (NDJSON) for easy streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_LOG_PATH = Path("logs/failure_log.ndjson")


@dataclass
class FailureRecord:
    """A single task execution failure record."""
    timestamp: str          # ISO-8601 UTC
    task_description: str   # global task
    subtask_id: str         # which subtask failed
    subtask_description: str
    skill_id: str | None    # skill that was running (if any)
    error_type: str         # e.g. "grasp_failure", "timeout", "collision"
    error_detail: str       # full error message
    robot_type: str = ""
    scene_context: dict[str, Any] = None  # type: ignore  # env snapshot at failure

    def __post_init__(self):
        if self.scene_context is None:
            self.scene_context = {}

    @classmethod
    def create(
        cls,
        task_description: str,
        subtask_id: str,
        subtask_description: str,
        error_type: str,
        error_detail: str,
        skill_id: str | None = None,
        robot_type: str = "",
        scene_context: dict[str, Any] | None = None,
    ) -> "FailureRecord":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_description=task_description,
            subtask_id=subtask_id,
            subtask_description=subtask_description,
            skill_id=skill_id,
            error_type=error_type,
            error_detail=error_detail,
            robot_type=robot_type,
            scene_context=scene_context or {},
        )


class FailureLog:
    """Append-only NDJSON failure log.

    Thread-safe via asyncio lock. Each record is one JSON line.
    """

    def __init__(self, log_path: Path | str = _DEFAULT_LOG_PATH):
        self._path = Path(log_path)
        self._lock = asyncio.Lock()

    async def append(self, record: FailureRecord) -> None:
        """Append a failure record to the log file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(record), ensure_ascii=False)
        async with self._lock:
            await asyncio.to_thread(self._write_line, line)

    def _write_line(self, line: str) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def read_all(self) -> list[FailureRecord]:
        """Read all records from the log (for analysis / planning context)."""
        if not self._path.exists():
            return []
        lines = await asyncio.to_thread(self._path.read_text, "utf-8")
        records = []
        for line in lines.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(FailureRecord(**data))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Skipping malformed failure log entry: %s", e)
        return records

    async def read_recent(self, n: int = 10) -> list[FailureRecord]:
        """Return the N most recent failure records."""
        all_records = await self.read_all()
        return all_records[-n:]

    async def summary_for_prompt(self, n: int = 5) -> str:
        """Build a concise failure summary string for LLM context."""
        recent = await self.read_recent(n)
        if not recent:
            return ""
        lines = ["[Recent Failures]"]
        for r in recent:
            lines.append(
                f"  [{r.timestamp[:10]}] {r.subtask_description} "
                f"— {r.error_type}: {r.error_detail[:60]}"
            )
        return "\n".join(lines)
