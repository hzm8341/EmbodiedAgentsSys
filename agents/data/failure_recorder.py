"""FailureDataRecorder — saves execution failure data for training pipeline."""
from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..components.scene_spec import SceneSpec


@dataclass
class FailureRecord:
    """All data captured at the moment of a skill execution failure."""
    scene_spec: SceneSpec
    plan_yaml: str
    failed_step_id: str
    error_type: str           # "hard_gap" | "execution_error" | "timeout"
    notes: str = ""
    failure_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # Optional raw data — not required in Phase 1
    rgb_frame_paths: list[str] = field(default_factory=list)
    state_log: list[dict] = field(default_factory=list)


class FailureDataRecorder:
    """Persists FailureRecord objects to disk under base_dir/<failure_id>/.

    Phase 1 saves: metadata.json, scene_spec.yaml, plan.yaml
    Phase 2 will add: rgb_frames/, state_log.jsonl
    """

    def __init__(self, base_dir: str, max_size_gb: float = 50.0):
        self._base = Path(base_dir)
        self._max_bytes = int(max_size_gb * 1024 ** 3)
        self._base.mkdir(parents=True, exist_ok=True)

    async def record(self, record: FailureRecord) -> str:
        """Save failure record to disk. Returns the directory path."""
        record_dir = self._base / record.failure_id
        record_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "failure_id": record.failure_id,
            "timestamp": record.timestamp,
            "failed_step_id": record.failed_step_id,
            "error_type": record.error_type,
            "notes": record.notes,
        }

        def _write_files() -> None:
            (record_dir / "metadata.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2)
            )
            (record_dir / "scene_spec.yaml").write_text(record.scene_spec.to_yaml())
            (record_dir / "plan.yaml").write_text(record.plan_yaml)

        await asyncio.to_thread(_write_files)
        return str(record_dir)

    def list_records(self) -> list[str]:
        """Return list of all recorded failure directory paths sorted by creation time (oldest first)."""
        if not self._base.exists():
            return []
        dirs = [p for p in self._base.iterdir() if p.is_dir()]
        return [str(p) for p in sorted(dirs, key=lambda p: p.stat().st_ctime)]

    def cleanup_old(self, keep_count: int = 1000) -> int:
        """Remove oldest records when count exceeds keep_count. Returns number deleted."""
        if keep_count <= 0:
            return 0
        records = self.list_records()
        to_delete = records[:-keep_count] if len(records) > keep_count else []
        for path in to_delete:
            shutil.rmtree(path, ignore_errors=True)
        return len(to_delete)
