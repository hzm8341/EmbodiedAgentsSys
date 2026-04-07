"""MockEventBus for test use."""
from collections import defaultdict
from typing import Any, Callable


class MockEventBus:
    """Mock event bus for testing event-driven components."""

    def __init__(self):
        """Initialize mock event bus."""
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self.published_events: list[tuple[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to.
            handler: Callable to invoke when event is published.
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, event: Any) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event being published.
            event: Event data to pass to subscribers.
        """
        self.published_events.append((event_type, event))
        for handler in self._subscribers.get(event_type, []):
            handler(event)
