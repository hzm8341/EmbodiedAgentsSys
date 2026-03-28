"""Event types for the robot agent message bus.

Ported from RoboClaw/roboclaw/bus/events.py.
Extended with robot-specific fields (task_id, priority).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """Message received from a channel (human operator, UI, or test harness)."""

    channel: str          # "cli", "rest", "ros", "test"
    sender_id: str        # user/system identifier
    chat_id: str          # conversation/session identifier
    content: str          # command text or serialized action
    timestamp: datetime = field(default_factory=datetime.now)
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    session_key_override: str | None = None

    # Robot-specific extensions
    task_id: str | None = None      # associate with a running task
    priority: int = 0               # higher = more urgent (e.g., emergency stop = 99)

    @property
    def session_key(self) -> str:
        """Unique key for session/conversation identification."""
        return self.session_key_override or f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """Message sent back to a channel."""

    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Robot-specific extensions
    task_id: str | None = None
    status: str = "ok"  # "ok" | "error" | "in_progress" | "complete"
