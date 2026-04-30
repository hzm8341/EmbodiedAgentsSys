"""Integration test for unified task execution entry across REST and WebSocket."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import agent_ws, chat
from backend.models.task_protocol import TaskResult


def _drain_until_result(ws, timeout_messages: int = 30):
    collected = []
    for _ in range(timeout_messages):
        msg = ws.receive_json()
        collected.append(msg)
        if msg.get("type") == "result":
            break
    return collected


def test_unified_rest_and_ws_task_result_parity(monkeypatch):
    app = FastAPI()
    app.include_router(chat.router, prefix="/api")
    app.include_router(agent_ws.router)

    async def _fake_execute_task(request, downstream_stream_manager=None):
        if downstream_stream_manager is not None:
            await downstream_stream_manager.broadcast(
                {
                    "type": "task_start",
                    "timestamp": 1.0,
                    "status": "completed",
                    "data": {"task": request.task},
                }
            )
            await downstream_stream_manager.broadcast(
                {
                    "type": "result",
                    "timestamp": 2.0,
                    "status": "completed",
                    "data": {"task_success": True, "steps_executed": 2},
                }
            )
        return TaskResult(
            task=request.task,
            success=True,
            steps_executed=2,
            message="ok",
            events=[],
            scene_state={"stub": True},
        )

    monkeypatch.setattr(chat.task_execution_service, "execute_task", _fake_execute_task)
    monkeypatch.setattr(
        agent_ws.task_execution_service, "execute_task", _fake_execute_task
    )

    client = TestClient(app)

    task = "pick up the red cube"
    observation = {"state": {"gripper_open": 1.0}}

    rest_resp = client.post(
        "/api/chat/execute_task",
        json={
            "task": task,
            "observation": observation,
            "max_steps": 2,
        },
    )
    assert rest_resp.status_code == 200
    rest_data = rest_resp.json()

    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json(
            {
                "type": "execute_task",
                "task": task,
                "observation": observation,
                "max_steps": 2,
            }
        )
        messages = _drain_until_result(ws)

    ws_result = messages[-1]
    assert ws_result["type"] == "result"

    assert rest_data["success"] == ws_result["data"]["task_success"]
    assert rest_data["steps_executed"] == ws_result["data"]["steps_executed"]
