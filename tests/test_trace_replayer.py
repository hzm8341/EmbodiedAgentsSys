import json
import pytest
from pathlib import Path
from agents.harness.core.trace_replayer import TraceReplayer
from agents.harness.core.tracer import TaskStatus


def test_replayer_loads_trace(tmp_path):
    trace_data = {
        "task_id": "test_001",
        "session_id": "sess_001",
        "mode": "hardware_mock",
        "start_time": "2026-03-30T10:00:00",
        "tool_calls": [],
        "skill_calls": ["manipulation.grasp"],
        "final_status": "completed",
    }
    (tmp_path / "trace_test_001.json").write_text(json.dumps(trace_data))
    replayer = TraceReplayer()
    trace = replayer.replay_from_file(tmp_path / "trace_test_001.json")
    assert trace.task_id == "test_001"
    assert trace.final_status == TaskStatus.COMPLETED
    assert "manipulation.grasp" in trace.skill_calls


def test_replayer_loads_dir(tmp_path):
    for i in range(3):
        (tmp_path / f"trace_{i}.json").write_text(json.dumps({
            "task_id": f"t{i}", "session_id": "s", "mode": "real",
            "start_time": "2026-03-30T10:00:00", "tool_calls": [],
            "skill_calls": [], "final_status": "completed",
        }))
    replayer = TraceReplayer()
    traces = replayer.replay_from_dir(tmp_path)
    assert len(traces) == 3
