from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import traces
from backend.services.trace_store import TraceStore


def test_trace_replay_api_returns_trace_and_events(monkeypatch, tmp_path):
    store = TraceStore(root_dir=str(tmp_path))
    trace_id = "trace_api1"
    store.append_event(trace_id, {"type": "task_start", "payload": {"task": "pick"}})
    store.append_result(trace_id, task="pick", result={"success": True})

    monkeypatch.setattr(traces, "trace_store", store)

    app = FastAPI()
    app.include_router(traces.router)
    client = TestClient(app)

    details = client.get(f"/api/traces/{trace_id}")
    assert details.status_code == 200
    assert details.json()["trace_id"] == trace_id

    replay = client.get(f"/api/traces/{trace_id}/replay")
    assert replay.status_code == 200
    body = replay.json()
    assert body["trace_id"] == trace_id
    assert len(body["events"]) == 1
    assert body["events"][0]["type"] == "task_start"

