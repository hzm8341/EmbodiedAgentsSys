from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import agent_ws


def test_real_mode_requires_operator_token(monkeypatch):
    called = {"value": False}

    async def _fake_start_task(*, session_id, request, downstream_stream_manager=None, operator=None):
        called["value"] = True

    monkeypatch.setattr(agent_ws.task_execution_service, "start_task", _fake_start_task)

    app = FastAPI()
    app.include_router(agent_ws.router)
    client = TestClient(app)

    with client.websocket_connect("/api/agent/ws?backend=real_robot") as ws:
        ws.send_json(
            {
                "type": "execute_task",
                "task": "move arm",
                "observation": {"state": {"gripper_open": 1.0}},
            }
        )
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert called["value"] is False

