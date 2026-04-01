from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.mode import HarnessMode

logger = logging.getLogger(__name__)


class TraceReplayer:
    def replay_from_file(self, trace_path: Path | str) -> HarnessTrace:
        data = json.loads(Path(trace_path).read_text())
        start = data.get("start_time")
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start)
            except ValueError:
                start = datetime.now()

        end_time = None
        raw_end = data.get("end_time")
        if isinstance(raw_end, str):
            try:
                end_time = datetime.fromisoformat(raw_end)
            except ValueError:
                pass

        trace = HarnessTrace(
            task_id=data.get("task_id", ""),
            session_id=data.get("session_id", ""),
            mode=HarnessMode.from_string(data.get("mode", "real")),
            start_time=start,
            end_time=end_time,
            duration_ms=data.get("duration_ms"),
            final_status=data.get("final_status", TaskStatus.FAILED),
            skill_calls=data.get("skill_calls", []),
        )
        return trace

    def replay_from_dir(self, dir_path: Path | str) -> list[HarnessTrace]:
        traces = []
        for f in sorted(Path(dir_path).glob("*.json")):
            try:
                traces.append(self.replay_from_file(f))
            except Exception as exc:
                logger.warning("Skipping trace file %s: %s", f, exc)
                continue
        return traces
