"""HAL event bus for P2主动上报异常."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Awaitable, Optional
from collections import defaultdict


class HALEvent(Enum):
    """HAL event types for async notification."""
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    EMERGENCY_STOP_TRIGGERED = "emergency_stop_triggered"
    HEALTH_CHECK_FAILED = "health_check_failed"
    DRIVER_DISCONNECTED = "driver_disconnected"


@dataclass
class HALEventData:
    """Event payload."""
    event: HALEvent
    timestamp: datetime = datetime.now()
    driver_name: Optional[str] = None
    receipt_id: Optional[str] = None
    details: Optional[dict] = None


class HALEventBus:
    """Event bus for HAL events.

    Following P2可控接管层:
    - 主动上报异常: 系统检测到异常须立即告警
    - 不得静默失败
    """

    def __init__(self):
        self._subscribers: dict[HALEvent, list[Callable[[HALEventData], Awaitable[None]]]] = defaultdict(list)

    def subscribe(
        self,
        event: HALEvent,
        handler: Callable[[HALEventData], Awaitable[None]]
    ) -> None:
        """Subscribe to event type."""
        self._subscribers[event].append(handler)

    def unsubscribe(
        self,
        event: HALEvent,
        handler: Callable[[HALEventData], Awaitable[None]]
    ) -> None:
        """Unsubscribe from event type."""
        if handler in self._subscribers[event]:
            self._subscribers[event].remove(handler)

    async def publish(self, event_data: HALEventData) -> None:
        """Publish event to all subscribers."""
        handlers = self._subscribers.get(event_data.event, [])
        for handler in handlers:
            try:
                await handler(event_data)
            except Exception:
                # Log but don't fail - event delivery should be resilient
                pass
