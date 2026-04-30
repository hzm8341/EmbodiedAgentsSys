from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from itertools import count
from typing import Any

from backend.models.messages import EventEnvelope
from backend.services.event_bus import EventBus


@dataclass
class _Connection:
    websocket: Any
    backend: str | None
    event_types: frozenset[str] | None
    robot_ids: frozenset[str] | None
    message_format: str


class WebSocketHub:
    def __init__(self, bus: EventBus, default_backend: str = "agent") -> None:
        self.bus = bus
        self.default_backend = default_backend
        self._connections: dict[Any, _Connection] = {}
        self._subscriber_queue = self.bus.subscribe()
        self._delivery_task: asyncio.Task[None] | None = None
        self._seq = count(1)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(
        self,
        websocket: Any,
        *,
        backend: str | None = None,
        event_types: set[str] | None = None,
        robot_ids: set[str] | None = None,
        message_format: str = "envelope",
    ) -> None:
        await websocket.accept()
        self._ensure_delivery_task()
        self._connections[websocket] = _Connection(
            websocket=websocket,
            backend=backend,
            event_types=frozenset(event_types) if event_types else None,
            robot_ids=frozenset(robot_ids) if robot_ids else None,
            message_format=message_format,
        )

    def update_subscription(
        self,
        websocket: Any,
        *,
        backend: str | None = None,
        event_types: set[str] | None = None,
        robot_ids: set[str] | None = None,
    ) -> bool:
        existing = self._connections.get(websocket)
        if existing is None:
            return False

        self._connections[websocket] = _Connection(
            websocket=existing.websocket,
            backend=backend,
            event_types=frozenset(event_types) if event_types else None,
            robot_ids=frozenset(robot_ids) if robot_ids else None,
            message_format=existing.message_format,
        )
        return True

    def disconnect(self, websocket: Any) -> None:
        self._connections.pop(websocket, None)

    async def broadcast(self, message: dict[str, Any]) -> None:
        self._ensure_delivery_task()
        await self.bus.publish(self._coerce_message(message))

    def _coerce_message(self, message: dict[str, Any]) -> EventEnvelope:
        extensions = dict(message.get("extensions", {}))
        for field in ("status", "trace_id", "step", "error_code", "protocol_version"):
            if field in message:
                extensions.setdefault(field, message[field])

        return EventEnvelope(
            event=message.get("event") or message.get("type", "message"),
            backend=message.get("backend", self.default_backend),
            robot_id=message.get("robot_id"),
            ts=message.get("ts", message.get("timestamp", time.time())),
            seq=message.get("seq", next(self._seq)),
            task_id=message.get("task_id"),
            payload=message.get("payload", message.get("data", {})),
            extensions=extensions,
        )

    def _ensure_delivery_task(self) -> None:
        if self._delivery_task is None or self._delivery_task.done():
            loop = asyncio.get_running_loop()
            self._delivery_task = loop.create_task(self._delivery_loop())

    async def _delivery_loop(self) -> None:
        while True:
            event = await self._subscriber_queue.get()

            for connection in list(self._connections.values()):
                if not self._matches(connection, event):
                    continue

                try:
                    await connection.websocket.send_text(
                        self._serialize_for_connection(connection, event)
                    )
                except Exception:
                    self.disconnect(connection.websocket)

    def _serialize_for_connection(
        self, connection: _Connection, event: EventEnvelope
    ) -> str:
        if connection.message_format == "legacy":
            payload = {
                "type": event.event,
                "backend": event.backend,
                "robot_id": event.robot_id,
                "timestamp": event.ts,
                "seq": event.seq,
                "task_id": event.task_id,
                "step": event.extensions.get("step"),
                "payload": event.payload,
                "data": event.payload,  # legacy alias
            }
            payload.update(event.extensions)
            return json.dumps(payload)
        return event.model_dump_json()

    def _matches(self, connection: _Connection, event: EventEnvelope) -> bool:
        if connection.backend and connection.backend != event.backend:
            return False
        if connection.event_types and event.event not in connection.event_types:
            return False
        if connection.robot_ids and event.robot_id not in connection.robot_ids:
            return False
        return True
