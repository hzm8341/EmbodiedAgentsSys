"""Conflict detection validator - checks for state conflicts with new actions."""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.policy.action_proposal import Action, ActionType, ValidationResult
from agents.policy.validators.base import Validator


class ConflictDetector(Validator):
    """Check if action conflicts with current robot state.

    This validator ensures that new actions do not conflict with the current
    state of the robot. For example, it prevents starting a move_to action
    while the arm is already moving, and prevents any action while emergency
    stop is active.
    """

    def priority(self) -> int:
        """Return priority 3 (after Whitelist and Boundary validators).

        Returns:
            Priority level 3.
        """
        return 3

    async def validate_action(
        self, action: Action, robot_state: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate action against current robot state.

        Args:
            action: The Action object to validate.
            robot_state: Dictionary containing current robot state flags.
                Example: {"arm_is_moving": False, "emergency_stop": False, "gripper_holding": False}

        Returns:
            ValidationResult indicating if action conflicts with robot state.
        """
        # Default to safe state if not provided
        if robot_state is None:
            robot_state = {}

        # Emergency stop takes priority - no actions allowed
        if robot_state.get("emergency_stop", False):
            return ValidationResult(
                valid=False,
                reason="emergency_stop is active; no actions can be executed",
                validator="conflict",
            )

        # Check MOVE_TO actions
        if action.action_type == ActionType.MOVE_TO:
            if robot_state.get("arm_is_moving", False):
                return ValidationResult(
                    valid=False,
                    reason="arm is already moving; cannot start new move_to",
                    validator="conflict",
                )

        # Check GRIPPER_CLOSE actions
        if action.action_type == ActionType.GRIPPER_CLOSE:
            if robot_state.get("gripper_holding", False):
                return ValidationResult(
                    valid=False,
                    reason="gripper is already holding an object; cannot close again",
                    validator="conflict",
                )

        # All other cases - action is safe to execute
        return ValidationResult(
            valid=True,
            reason=f"Action '{action.action_type.value}' does not conflict with current state",
            validator="conflict",
        )
