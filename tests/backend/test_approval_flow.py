from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import agent_ws


def test_high_risk_task_requires_approval(monkeypatch):
    started = {"value": False}

    async def _fake_start_task(*, session_id, request, downstream_stream_manager=None):
        started["value"] = True

    monkeypatch.setattr(agent_ws.task_execution_service, "start_task", _fake_start_task)

    app = FastAPI()
    app.include_router(agent_ws.router)
    client = TestClient(app)

    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json(
            {
                "type": "execute_task",
                "task": "real robot high speed force validation",
                "observation": {"state": {"gripper_open": 1.0}},
            }
        )
        approval = ws.receive_json()
        assert approval["type"] == "approval_required"
        assert approval["data"]["risk_level"] == "high"
        assert started["value"] is False

        ws.send_json({"type": "approve_task"})
        running = ws.receive_json()
        assert running["type"] == "execution_status"
        assert running["data"]["state"] == "running"
        assert started["value"] is True

