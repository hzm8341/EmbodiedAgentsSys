from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import agent_ws


def test_agent_ws_control_messages(monkeypatch):
    states: dict[str, str] = {}

    async def _fake_start_task(*, session_id, request, downstream_stream_manager=None):
        states[session_id] = "running"

    def _fake_control_task(session_id: str, command: str):
        next_state = {
            "pause": "paused",
            "resume": "running",
            "abort": "aborted",
            "step": states.get(session_id, "idle"),
        }.get(command, "idle")
        states[session_id] = next_state
        return {"ok": True, "state": next_state}

    def _fake_get_task_state(session_id: str):
        return states.get(session_id, "idle")

    monkeypatch.setattr(agent_ws.task_execution_service, "start_task", _fake_start_task)
    monkeypatch.setattr(agent_ws.task_execution_service, "control_task", _fake_control_task)
    monkeypatch.setattr(agent_ws.task_execution_service, "get_task_state", _fake_get_task_state)

    app = FastAPI()
    app.include_router(agent_ws.router)
    client = TestClient(app)

    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json(
            {
                "type": "execute_task",
                "task": "pick cube",
                "observation": {"state": {"gripper_open": 1.0}},
            }
        )
        status = ws.receive_json()
        assert status["type"] == "execution_status"
        assert status["data"]["state"] == "running"

        ws.send_json({"type": "pause_task"})
        paused = ws.receive_json()
        assert paused["type"] == "execution_control"
        assert paused["data"]["state"] == "paused"

        ws.send_json({"type": "task_status"})
        state = ws.receive_json()
        assert state["type"] == "execution_status"
        assert state["data"]["state"] == "paused"

