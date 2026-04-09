"""State protocol types."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProtocolType(Enum):
    """Types of state protocols following PhyAgentOS pattern."""
    ACTION = "action"
    ENVIRONMENT = "environment"
    EMBODIED = "embodied"
    LESSONS = "lessons"


@dataclass
class StateEntry:
    """Single state entry with metadata for audit trail."""
    protocol_type: ProtocolType
    content: dict
    updated_by: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "protocol_type": self.protocol_type.value,
            "content": self.content,
            "updated_by": self.updated_by,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }
