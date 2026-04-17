"""End-to-end tests for the interactive agent debugger.

Covers the full pipeline: WebSocket connection -> task execution through the
four cognition layers -> telemetry broadcast -> result. All 5 predefined
scenarios are exercised.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.scenarios import SCENARIOS


client = TestClient(app)

EXPECTED_SEQUENCE_PER_STEP = ["reasoning", "execution", "learning"]


def _drain_until_result(ws, safety_cap: int = 30) -> list[dict]:
    collected = []
    for _ in range(safety_cap):
        msg = ws.receive_json()
        collected.append(msg)
        if msg.get("type") == "result":
            break
    return collected


def test_scenarios_listed_via_rest():
    r = client.get("/api/agent/scenarios")
    assert r.status_code == 200
    body = r.json()
    names = {s["name"] for s in body}
    assert names == set(SCENARIOS.keys())


@pytest.mark.parametrize("scenario_name", list(SCENARIOS.keys()))
def test_scenario_executes_end_to_end(scenario_name):
    scenario = SCENARIOS[scenario_name]

    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json({
            "type": "execute_task",
            "task": scenario.task,
            "observation": {
                "state": scenario.initial_state,
                "gripper": scenario.initial_gripper,
            },
            "max_steps": 2,
        })
        messages = _drain_until_result(ws)

    types = [m["type"] for m in messages]
    # task_start + planning + 2 × (reasoning, execution, learning) + result = 9
    assert types[0] == "task_start"
    assert types[1] == "planning"
    assert types[-1] == "result"

    # Confirm every step emitted the full reasoning/execution/learning triplet
    step_blocks = types[2:-1]  # strip task_start, planning, result
    assert len(step_blocks) == 2 * len(EXPECTED_SEQUENCE_PER_STEP)
    for i in range(0, len(step_blocks), 3):
        assert step_blocks[i : i + 3] == EXPECTED_SEQUENCE_PER_STEP

    # Sanity-check result payload
    result_data = messages[-1]["data"]
    assert result_data["task_success"] is True
    assert result_data["steps_executed"] == 2


def test_task_start_echoes_task_text():
    scenario = SCENARIOS["single_grasp"]
    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json({
            "type": "execute_task",
            "task": scenario.task,
            "observation": {"state": scenario.initial_state},
            "max_steps": 1,
        })
        messages = _drain_until_result(ws, safety_cap=10)

    task_start = next(m for m in messages if m["type"] == "task_start")
    assert task_start["data"]["task"] == scenario.task


def test_planning_message_carries_plan_structure():
    with client.websocket_connect("/api/agent/ws") as ws:
        ws.send_json({
            "type": "execute_task",
            "task": "test plan structure",
            "observation": {"state": {"gripper_open": 1.0}},
            "max_steps": 1,
        })
        messages = _drain_until_result(ws, safety_cap=10)

    planning = next(m for m in messages if m["type"] == "planning")
    plan = planning["data"]["plan"]
    assert plan["task"] == "test plan structure"
    assert "steps" in plan


def test_multiple_tasks_on_same_connection():
    """A single WebSocket connection should handle sequential tasks."""
    with client.websocket_connect("/api/agent/ws") as ws:
        for task_text in ["first task", "second task"]:
            ws.send_json({
                "type": "execute_task",
                "task": task_text,
                "observation": {"state": {"gripper_open": 1.0}},
                "max_steps": 1,
            })
            messages = _drain_until_result(ws, safety_cap=10)
            assert messages[-1]["type"] == "result"
            assert messages[-1]["data"]["task_success"] is True
