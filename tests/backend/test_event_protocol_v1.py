"""Contract tests for unified execution event protocol v1."""
from __future__ import annotations

from typing import List

from agents.core.types import RobotObservation
from backend.services.agent_bridge import AgentBridge


class FakeStreamManager:
    def __init__(self) -> None:
        self.messages: List[dict] = []

    async def broadcast(self, message: dict) -> None:
        self.messages.append(message)


async def test_event_protocol_v1_fields_and_legacy_alias():
    stream = FakeStreamManager()
    bridge = AgentBridge(stream_manager=stream)
    obs = RobotObservation(state={"gripper_open": True})

    await bridge.run_with_telemetry("pick cube", obs, max_steps=1)

    assert len(stream.messages) >= 5
    trace_ids = {m.get("trace_id") for m in stream.messages}
    assert len(trace_ids) == 1
    trace_id = next(iter(trace_ids))
    assert isinstance(trace_id, str)
    assert trace_id.startswith("trace_")

    for message in stream.messages:
        assert message["protocol_version"] == "v1"
        assert message["status"] == "completed"
        assert message.get("error_code") is None
        assert isinstance(message.get("timestamp"), float)
        assert message["payload"] == message["data"]

    step_types = {"reasoning", "execution", "learning"}
    for message in stream.messages:
        if message["type"] in step_types:
            assert message.get("step") == 0
            assert message["payload"].get("step") == 0
        else:
            assert message.get("step") is None

