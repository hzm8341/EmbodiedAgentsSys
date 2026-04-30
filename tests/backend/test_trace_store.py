from __future__ import annotations

from backend.services.trace_store import TraceStore


def test_trace_store_persists_events_and_result(tmp_path):
    store = TraceStore(root_dir=str(tmp_path))
    trace_id = "trace_abc123"

    store.append_event(trace_id, {"type": "task_start", "payload": {"task": "pick"}})
    store.append_event(trace_id, {"type": "result", "payload": {"task_success": True}})
    store.append_result(
        trace_id,
        task="pick",
        result={"success": True, "steps_executed": 1},
        operator="operator_a",
    )

    trace = store.get_trace(trace_id)
    assert trace is not None
    assert trace["trace_id"] == trace_id
    assert trace["task"] == "pick"
    assert trace["operator"] == "operator_a"
    assert len(trace["events"]) == 2
    assert trace["result"]["success"] is True


def test_trace_store_replay_returns_events_only(tmp_path):
    store = TraceStore(root_dir=str(tmp_path))
    trace_id = "trace_xyz"
    store.append_event(trace_id, {"type": "planning", "payload": {"plan": []}})

    replay = store.replay(trace_id)
    assert replay is not None
    assert len(replay) == 1
    assert replay[0]["type"] == "planning"

