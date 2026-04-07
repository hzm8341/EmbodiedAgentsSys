"""Execution feedback data structures for tool runtime monitoring.

Provides async generator feedback during tool execution, allowing
the system to track progress and detect issues in real-time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict


class FeedbackStage(str, Enum):
    """Enum of execution stages for feedback tracking."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExecutionFeedback:
    """Execution feedback from tool during runtime.

    Represents a single feedback event during tool execution,
    tracking progress, state, and any errors encountered.
    """

    stage: FeedbackStage
    progress: float = 0.0
    current_state: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    has_error: bool = False
    error_message: str = ""
    error_type: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate feedback data types and ranges."""
        # Convert stage to enum if it's a string
        if isinstance(self.stage, str):
            self.stage = FeedbackStage(self.stage)

        # Validate progress is between 0.0 and 1.0
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError("progress must be between 0.0 and 1.0")

        # Validate boolean field
        if not isinstance(self.has_error, bool):
            raise TypeError("has_error must be a boolean")

    @property
    def is_terminal(self) -> bool:
        """Check if execution has reached a terminal state.

        Terminal states are COMPLETED or FAILED, indicating execution finished.

        Returns:
            True if stage is COMPLETED or FAILED, False otherwise
        """
        return self.stage in (FeedbackStage.COMPLETED, FeedbackStage.FAILED)

    @property
    def is_recoverable(self) -> bool:
        """Check if execution can be resumed from current state.

        Only PAUSED stages are recoverable - execution can resume from pause.

        Returns:
            True if stage is PAUSED, False otherwise
        """
        return self.stage == FeedbackStage.PAUSED

    def to_dict(self) -> Dict[str, Any]:
        """Convert ExecutionFeedback to dictionary for serialization.

        Returns:
            Dictionary representation of the feedback
        """
        return {
            "stage": self.stage.value,
            "progress": self.progress,
            "current_state": self.current_state,
            "message": self.message,
            "has_error": self.has_error,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
            "is_terminal": self.is_terminal,
            "is_recoverable": self.is_recoverable,
        }
