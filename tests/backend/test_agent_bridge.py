"""Tests for AgentBridge."""
import pytest
from typing import List
from agents.core.types import RobotObservation
from backend.services.agent_bridge import AgentBridge


class FakeStreamManager:
    def __init__(self):
        self.messages: List[dict] = []

    async def broadcast(self, message: dict) -> None:
        self.messages.append(message)


async def test_initializes_with_defaults():
    bridge = AgentBridge()
    assert bridge.planning is not None
    assert bridge.reasoning is not None
    assert bridge.learning is not None
    assert bridge.stream_manager is not None


async def test_run_broadcasts_task_start():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": True})

    await bridge.run_with_telemetry("pick cube", obs, max_steps=1)

    types = [m["type"] for m in stream.messages]
    assert types[0] == "task_start"
    assert stream.messages[0]["data"]["task"] == "pick cube"


async def test_run_broadcasts_planning_then_loop_then_result():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": True})

    result = await bridge.run_with_telemetry("pick cube", obs, max_steps=2)

    types = [m["type"] for m in stream.messages]
    # Expected order:
    # task_start, planning, (reasoning, execution, learning) x 2, result
    assert types == [
        "task_start",
        "planning",
        "reasoning", "execution", "learning",
        "reasoning", "execution", "learning",
        "result",
    ]
    assert result["task_success"] is True
    assert result["steps_executed"] == 2


async def test_planning_message_contains_plan():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": True})

    await bridge.run_with_telemetry("test", obs, max_steps=1)

    planning_msgs = [m for m in stream.messages if m["type"] == "planning"]
    assert len(planning_msgs) == 1
    assert "plan" in planning_msgs[0]["data"]
    assert planning_msgs[0]["data"]["plan"]["task"] == "test"


async def test_reasoning_message_contains_action():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": True})

    await bridge.run_with_telemetry("test", obs, max_steps=1)

    reasoning_msgs = [m for m in stream.messages if m["type"] == "reasoning"]
    assert len(reasoning_msgs) == 1
    assert "action" in reasoning_msgs[0]["data"]
    assert reasoning_msgs[0]["data"]["step"] == 0  # first iteration index


async def test_learning_message_contains_improved_action():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": False})

    await bridge.run_with_telemetry("test", obs, max_steps=1)

    learning_msgs = [m for m in stream.messages if m["type"] == "learning"]
    assert len(learning_msgs) == 1
    assert "improved_action" in learning_msgs[0]["data"]


async def test_all_messages_have_timestamp():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": True})

    await bridge.run_with_telemetry("test", obs, max_steps=1)

    for m in stream.messages:
        assert isinstance(m.get("timestamp"), float)
        assert m["timestamp"] > 0


async def test_singleton_instance_exists():
    from backend.services.agent_bridge import agent_bridge, AgentBridge
    assert isinstance(agent_bridge, AgentBridge)
