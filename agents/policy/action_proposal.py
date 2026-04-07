"""Core data structures for policy validation layer.

Defines action proposals, execution feedback, and validation results used
across the three-layer policy validation architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ActionType(str, Enum):
    """Enum of valid action types for the robotic system."""

    MOVE_TO = "move_to"
    GRIPPER_OPEN = "gripper_open"
    GRIPPER_CLOSE = "gripper_close"
    VISION_CAPTURE = "vision_capture"
    EMERGENCY_STOP = "emergency_stop"


class ExpectedOutcomeType(str, Enum):
    """Enum of expected outcomes for action validation."""

    ARM_REACHES_TARGET = "arm_reaches_target"
    OBJECT_GRASPED = "object_grasped"
    OBJECT_RELEASED = "object_released"
    OBJECT_VISIBLE = "object_visible"
    EMERGENCY_STOPPED = "emergency_stopped"


class SequenceType(str, Enum):
    """Enum of action sequence execution types."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class Action:
    """Represents a single action proposal."""

    action_type: ActionType
    params: Dict[str, Any]
    expected_outcome: ExpectedOutcomeType

    def __post_init__(self) -> None:
        """Validate action types are enums."""
        if isinstance(self.action_type, str):
            self.action_type = ActionType(self.action_type)
        if isinstance(self.expected_outcome, str):
            self.expected_outcome = ExpectedOutcomeType(self.expected_outcome)


@dataclass
class ActionProposal:
    """Strict-typed action proposal from LLM with validation metadata.

    Uses enums instead of free strings to ensure type safety at the LLM output layer.
    """

    action_sequence: List[Action]
    id: str = field(default_factory=lambda: str(uuid4()))
    sequence_type: SequenceType = SequenceType.SEQUENTIAL
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate and normalize input types."""
        # Convert string sequence_type to enum
        if isinstance(self.sequence_type, str):
            self.sequence_type = SequenceType(self.sequence_type)

        # Validate action_sequence is a list of Action objects
        if not isinstance(self.action_sequence, list):
            raise TypeError("action_sequence must be a list")

        for i, action in enumerate(self.action_sequence):
            if not isinstance(action, Action):
                raise TypeError(f"action_sequence[{i}] must be an Action instance")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActionProposal:
        """Create ActionProposal from dictionary with type validation.

        Args:
            data: Dictionary containing proposal data

        Returns:
            Validated ActionProposal instance

        Raises:
            TypeError: If types don't match expected schema
            ValueError: If enum values are invalid
        """
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary")

        # Convert action_sequence items to Action objects
        action_sequence = []
        for item in data.get("action_sequence", []):
            if isinstance(item, dict):
                action = Action(
                    action_type=ActionType(item["action_type"]),
                    params=item.get("params", {}),
                    expected_outcome=ExpectedOutcomeType(item["expected_outcome"]),
                )
                action_sequence.append(action)
            elif isinstance(item, Action):
                action_sequence.append(item)
            else:
                raise TypeError(f"Expected Action or dict, got {type(item)}")

        # Parse timestamp if it's a string
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            action_sequence=action_sequence,
            id=data.get("id", str(uuid4())),
            sequence_type=data.get("sequence_type", SequenceType.SEQUENTIAL),
            reasoning=data.get("reasoning", ""),
            timestamp=timestamp,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ActionProposal to dictionary for serialization.

        Returns:
            Dictionary representation of the proposal
        """
        return {
            "id": self.id,
            "action_sequence": [
                {
                    "action_type": action.action_type.value,
                    "params": action.params,
                    "expected_outcome": action.expected_outcome.value,
                }
                for action in self.action_sequence
            ],
            "sequence_type": self.sequence_type.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationResult:
    """Result of validation check on an action proposal.

    Used by each validator in the three-layer pipeline.
    """

    valid: bool
    reason: str = ""
    validator: str = ""
    requires_human_approval: bool = False

    def __post_init__(self) -> None:
        """Ensure bool type for valid field."""
        if not isinstance(self.valid, bool):
            raise TypeError("valid must be a boolean")
