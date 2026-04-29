from __future__ import annotations

import asyncio
import json

from backend.models.messages import EventEnvelope
from backend.services.event_bus import EventBus
from backend.services.websocket_hub import WebSocketHub


class FakeWebSocket:
    def __init__(self, fail_on_send: bool = False) -> None:
        self.accepted = False
        self.messages: list[str] = []
        self.fail_on_send = fail_on_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, payload: str) -> None:
        if self.fail_on_send:
            raise RuntimeError("send failed")
        self.messages.append(payload)


async def _await_messages() -> None:
    await asyncio.sleep(0)


def test_hub_delivers_only_matching_subscriptions() -> None:
    async def scenario() -> tuple[FakeWebSocket, FakeWebSocket]:
        bus = EventBus()
        hub = WebSocketHub(bus)
        matching = FakeWebSocket()
        non_matching = FakeWebSocket()

        await hub.connect(
            matching,
            backend="sim",
            event_types={"execution"},
            robot_ids={"robot-1"},
        )
        await hub.connect(
            non_matching,
            backend="real",
            event_types={"execution"},
            robot_ids={"robot-1"},
        )

        await bus.publish(
            EventEnvelope(
                event="execution",
                backend="sim",
                robot_id="robot-1",
                ts=123.0,
                seq=9,
                task_id="task-1",
                payload={"step": 1},
                extensions={"source": "agent"},
            )
        )
        await _await_messages()
        return matching, non_matching

    matching, non_matching = asyncio.run(scenario())

    assert matching.accepted is True
    assert non_matching.accepted is True
    delivered = json.loads(matching.messages[0])
    assert delivered["event"] == "execution"
    assert delivered["backend"] == "sim"
    assert delivered["robot_id"] == "robot-1"
    assert delivered["ts"] == 123.0
    assert delivered["seq"] == 9
    assert delivered["task_id"] == "task-1"
    assert delivered["payload"] == {"step": 1}
    assert delivered["extensions"] == {"source": "agent"}
    assert non_matching.messages == []


def test_hub_removes_failed_websocket_after_send_error() -> None:
    async def scenario() -> int:
        bus = EventBus()
        hub = WebSocketHub(bus)
        broken = FakeWebSocket(fail_on_send=True)

        await hub.connect(broken)
        await bus.publish(
            EventEnvelope(
                event="result",
                backend="sim",
                robot_id="robot-1",
                ts=123.0,
                seq=10,
                task_id="task-1",
                payload={},
            )
        )
        await _await_messages()
        return hub.connection_count

    assert asyncio.run(scenario()) == 0


def test_hub_broadcast_coerces_legacy_agent_messages_into_event_envelope() -> None:
    async def scenario() -> dict:
        bus = EventBus()
        hub = WebSocketHub(bus, default_backend="agent")
        socket = FakeWebSocket()

        await hub.connect(socket, event_types={"planning"})
        await hub.broadcast(
            {
                "type": "planning",
                "timestamp": 456.0,
                "status": "completed",
                "data": {"plan": ["move"]},
            }
        )
        await _await_messages()
        return json.loads(socket.messages[0])

    delivered = asyncio.run(scenario())

    assert delivered["event"] == "planning"
    assert delivered["backend"] == "agent"
    assert delivered["robot_id"] is None
    assert delivered["ts"] == 456.0
    assert delivered["seq"] == 1
    assert delivered["task_id"] is None
    assert delivered["payload"] == {"plan": ["move"]}
    assert delivered["extensions"] == {"status": "completed"}


def test_hub_legacy_format_and_runtime_subscription_update() -> None:
    async def scenario() -> list[dict]:
        bus = EventBus()
        hub = WebSocketHub(bus)
        socket = FakeWebSocket()

        await hub.connect(socket, backend="mujoco", message_format="legacy")
        assert hub.update_subscription(socket, backend="ros2_gazebo") is True

        await bus.publish(
            EventEnvelope(
                event="scene_snapshot",
                backend="ros2_gazebo",
                robot_id=None,
                ts=789.0,
                seq=11,
                task_id=None,
                payload={"backend": "ros2_gazebo", "robots": []},
            )
        )
        await _await_messages()
        return [json.loads(message) for message in socket.messages]

    delivered = asyncio.run(scenario())

    assert delivered[0]["type"] == "scene_snapshot"
    assert delivered[0]["backend"] == "ros2_gazebo"
    assert delivered[0]["data"]["backend"] == "ros2_gazebo"
