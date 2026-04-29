from __future__ import annotations

import asyncio

from backend.models.messages import EventEnvelope
from backend.services.event_bus import EventBus


def test_subscribe_returns_queue_and_publish_fanouts_to_all_subscribers() -> None:
    bus = EventBus()
    subscriber_one = bus.subscribe()
    subscriber_two = bus.subscribe()

    event = EventEnvelope(
        event="execution",
        backend="sim",
        robot_id="robot-1",
        ts=123.0,
        seq=7,
        task_id="task-1",
        payload={"step": 1},
    )

    asyncio.run(bus.publish(event))

    assert isinstance(subscriber_one, asyncio.Queue)
    assert isinstance(subscriber_two, asyncio.Queue)
    assert subscriber_one.get_nowait() == event
    assert subscriber_two.get_nowait() == event


def test_publish_preserves_event_order_per_subscriber_queue() -> None:
    bus = EventBus()
    subscriber = bus.subscribe()

    first = EventEnvelope(
        event="planning",
        backend="sim",
        robot_id="robot-1",
        ts=1.0,
        seq=1,
        task_id="task-1",
        payload={"step": 1},
    )
    second = EventEnvelope(
        event="result",
        backend="sim",
        robot_id="robot-1",
        ts=2.0,
        seq=2,
        task_id="task-1",
        payload={"task_success": True},
    )

    asyncio.run(bus.publish(first))
    asyncio.run(bus.publish(second))

    assert subscriber.get_nowait() == first
    assert subscriber.get_nowait() == second
