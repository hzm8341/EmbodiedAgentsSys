from __future__ import annotations

import asyncio

from backend.models.messages import EventEnvelope


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[EventEnvelope]] = []

    def subscribe(self) -> asyncio.Queue[EventEnvelope]:
        subscriber: asyncio.Queue[EventEnvelope] = asyncio.Queue()
        self._subscribers.append(subscriber)
        return subscriber

    async def publish(self, event: EventEnvelope) -> None:
        for subscriber in list(self._subscribers):
            await subscriber.put(event)
