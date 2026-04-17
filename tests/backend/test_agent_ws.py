"""Integration tests for /api/agent/ws endpoint."""
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


def _drain_until_result(ws, timeout_messages: int = 20):
    """Collect messages until a 'result' type arrives (or safety cap)."""
    collected = []
    for _ in range(timeout_messages):
        msg = ws.receive_json()
        collected.append(msg)
        if msg.get("type") == "result":
            break
    return collected


def test_scenarios_endpoint():
    r = client.get("/api/agent/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 5
    names = {s["name"] for s in data}
    assert "single_grasp" in names


def test_health_still_works():
    """Regression: existing /health endpoint must still respond."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_agent_ws_happy_path():
    """Full round-trip: send execute_task, receive full telemetry sequence."""
    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json({
            "type": "execute_task",
            "task": "pick up the red cube",
            "observation": {"state": {"gripper_open": 1.0}},
            "max_steps": 2,
        })
        messages = _drain_until_result(ws)

    types = [m["type"] for m in messages]
    assert types == [
        "task_start",
        "planning",
        "reasoning", "execution", "learning",
        "reasoning", "execution", "learning",
        "result",
    ]
    assert messages[-1]["data"]["task_success"] is True
    assert messages[-1]["data"]["steps_executed"] == 2


def test_agent_ws_invalid_json_returns_error():
    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_text("not a json")
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_agent_ws_unsupported_type_returns_error():
    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json({"type": "unknown"})
        msg = ws.receive_json()
        assert msg["type"] == "error"


def test_agent_ws_default_max_steps_is_three():
    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json({
            "type": "execute_task",
            "task": "default task",
            "observation": {"state": {"gripper_open": 1.0}},
        })
        messages = _drain_until_result(ws, timeout_messages=30)
    assert messages[-1]["data"]["steps_executed"] == 3
