"""Execution result confirmation engine.

Validates actual execution results against expected outcomes, providing
closed-loop feedback to detect successful completion or failure modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from agents.execution.execution_feedback import ExecutionFeedback
from agents.policy.action_proposal import Action, ExpectedOutcomeType


@dataclass
class ConfirmationResult:
    """Result of execution confirmation check.

    Attributes:
        status: One of "confirmed", "partial", "failed", "timeout"
        reason: Human-readable explanation of the result
        pose_error: Euclidean distance error in meters (for pose checks)
    """

    status: str
    reason: str = ""
    pose_error: float = 0.0


class ExecutionConfirmationEngine:
    """Validates execution results against expected outcomes.

    Performs closed-loop confirmation by comparing actual system state
    against expected outcomes specified in action proposals. Supports
    multiple outcome types: pose accuracy, grasp state, vision detection, etc.
    """

    def __init__(self):
        """Initialize confirmation engine with default tolerances."""
        self.tolerance_pose = 0.05  # meters
        self.tolerance_force = 5.0  # Newtons

    async def confirm(
        self,
        action: Action,
        feedbacks: List[ExecutionFeedback],
        actual_state: Dict,
        timeout_seconds: float = 30.0,
    ) -> ConfirmationResult:
        """Confirm execution result against expected outcome.

        Args:
            action: Action proposal with expected outcome type
            feedbacks: List of feedback events during execution
            actual_state: Dictionary of actual system state after execution
            timeout_seconds: Maximum allowed execution duration

        Returns:
            ConfirmationResult with status and explanation
        """
        # Check timeout
        if feedbacks and len(feedbacks) >= 2:
            duration = feedbacks[-1].timestamp - feedbacks[0].timestamp
            if duration > timeout_seconds:
                return ConfirmationResult(
                    status="timeout",
                    reason=f"execution took {duration:.1f}s > {timeout_seconds}s",
                )

        # Check based on expected outcome type
        if action.expected_outcome == ExpectedOutcomeType.ARM_REACHES_TARGET:
            return self._check_pose_outcome(action, actual_state)
        elif action.expected_outcome == ExpectedOutcomeType.OBJECT_GRASPED:
            return self._check_grasp_outcome(actual_state)
        elif action.expected_outcome == ExpectedOutcomeType.OBJECT_RELEASED:
            return self._check_release_outcome(actual_state)
        elif action.expected_outcome == ExpectedOutcomeType.OBJECT_VISIBLE:
            return self._check_vision_outcome(actual_state)

        return ConfirmationResult(
            status="confirmed", reason="no specific check needed"
        )

    def _check_pose_outcome(
        self, action: Action, actual_state: Dict
    ) -> ConfirmationResult:
        """Check if arm reached target pose.

        Args:
            action: Action proposal with target pose in params
            actual_state: Dictionary containing current_pose and collision_detected

        Returns:
            ConfirmationResult with pose accuracy check
        """
        target_pose = action.params.get("target_pose", [])
        current_pose = actual_state.get("current_pose", [])
        collision = actual_state.get("collision_detected", False)

        if collision:
            return ConfirmationResult(status="failed", reason="collision detected")

        # Calculate pose error using Euclidean distance
        if len(target_pose) == 3 and len(current_pose) == 3:
            error = sum(
                (t - c) ** 2 for t, c in zip(target_pose, current_pose)
            ) ** 0.5
            if error <= self.tolerance_pose:
                return ConfirmationResult(
                    status="confirmed",
                    reason="pose within tolerance",
                    pose_error=error,
                )
            else:
                return ConfirmationResult(
                    status="failed",
                    reason=f"pose error {error:.4f}m > {self.tolerance_pose}m",
                    pose_error=error,
                )

        return ConfirmationResult(status="confirmed")

    def _check_grasp_outcome(self, actual_state: Dict) -> ConfirmationResult:
        """Check if object is grasped.

        Args:
            actual_state: Dictionary containing gripper_holding status

        Returns:
            ConfirmationResult for grasp check
        """
        gripper_holding = actual_state.get("gripper_holding", False)
        if gripper_holding:
            return ConfirmationResult(
                status="confirmed", reason="object grasped"
            )
        return ConfirmationResult(
            status="failed", reason="gripper not holding object"
        )

    def _check_release_outcome(self, actual_state: Dict) -> ConfirmationResult:
        """Check if object was released.

        Args:
            actual_state: Dictionary containing gripper_holding status

        Returns:
            ConfirmationResult for release check
        """
        gripper_holding = actual_state.get("gripper_holding", False)
        if not gripper_holding:
            return ConfirmationResult(
                status="confirmed", reason="object released"
            )
        return ConfirmationResult(
            status="failed", reason="gripper still holding object"
        )

    def _check_vision_outcome(self, actual_state: Dict) -> ConfirmationResult:
        """Check if object is visible.

        Args:
            actual_state: Dictionary containing object_visible status

        Returns:
            ConfirmationResult for vision check
        """
        object_visible = actual_state.get("object_visible", False)
        if object_visible:
            return ConfirmationResult(
                status="confirmed", reason="object visible"
            )
        return ConfirmationResult(
            status="failed", reason="object not visible"
        )
