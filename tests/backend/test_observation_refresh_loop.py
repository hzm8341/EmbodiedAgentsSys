import pytest

from agents.core.types import RobotObservation
from backend.services.agent_bridge import AgentBridge


class _FakeStream:
    def __init__(self):
        self.messages = []

    async def broadcast(self, message: dict):
        self.messages.append(message)


class _FakePlanning:
    async def generate_plan(self, task: str, action_sequence=None):
        return {"task": task, "action_sequence": [{"action": "move_arm_to", "params": {"arm": "left", "x": 0.1, "y": 0.2, "z": 0.3}}], "current_step": 0}


class _FakeReasoning:
    def __init__(self):
        self.observations = []

    async def generate_action(self, plan: dict, observation):
        self.observations.append(dict(observation.state))
        return {"action": "move_arm_to", "params": {"arm": "left", "x": 0.1, "y": 0.2, "z": 0.3}}


class _FakeLearning:
    async def improve(self, action: dict, feedback: dict):
        return action


class _FakeReceipt:
    class _Status:
        value = "success"

    status = _Status()
    result_message = "ok"
    result_data = {}


class _FakeSimService:
    def __init__(self):
        self.count = 0

    def execute_action(self, action: str, params: dict):
        return _FakeReceipt()

    def get_observation(self):
        self.count += 1
        return RobotObservation(state={"tick": float(self.count)})


@pytest.mark.asyncio
async def test_observation_is_refreshed_after_each_action(monkeypatch):
    stream = _FakeStream()
    reasoning = _FakeReasoning()
    bridge = AgentBridge(
        planning=_FakePlanning(),
        reasoning=reasoning,
        learning=_FakeLearning(),
        stream_manager=stream,
    )

    monkeypatch.setattr(
        "backend.services.simulation.simulation_service",
        _FakeSimService(),
    )

    await bridge.run_with_telemetry(
        task="pick",
        observation=RobotObservation(state={"tick": 0.0}),
        max_steps=2,
    )

    assert len(reasoning.observations) == 2
    assert reasoning.observations[0]["tick"] == 0.0
    assert reasoning.observations[1]["tick"] == 1.0

