"""System mode definitions and state machine for embodied agents."""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone


class SystemMode(str, Enum):
    """Operational modes for the robot system."""

    AUTOMATIC = "automatic"
    MANUAL_OVERRIDE = "manual_override"
    PAUSED = "paused"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class ModeTransition:
    """Record of a mode transition for audit trail."""

    from_mode: SystemMode
    to_mode: SystemMode
    reason: str
    timestamp: datetime = None
    triggered_by: str = ""  # "user", "safety_system", "timeout"

    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
