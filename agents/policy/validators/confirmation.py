"""Second confirmation validator - marks high-risk actions for human approval."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import yaml

from agents.policy.action_proposal import Action, ValidationResult
from agents.policy.validators.base import Validator


class SecondConfirmation(Validator):
    """Mark high-risk actions requiring human approval.

    This validator identifies actions that require human confirmation before
    execution. It does NOT block execution - it only marks the action with
    requires_human_approval=True. The ValidationPipeline decides how to handle
    approval (e.g., teachpendant, web portal, email).

    Actions like move_to and emergency_stop are flagged as requiring approval.
    Safe actions like gripper_open, gripper_close, and vision_capture do not
    require approval.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize SecondConfirmation with approval policy.

        Args:
            config_path: Path to approval_policy.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default to config/approval_policy.yaml relative to project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            config_path = os.path.join(project_root, "config", "approval_policy.yaml")

        self.config_path = config_path
        self._rules: Dict[str, Any] = self._load_approval_rules()

    def _load_approval_rules(self) -> Dict[str, Any]:
        """Load approval rules from configuration file.

        Returns:
            Dictionary containing approval rules for each action type.
        """
        if not os.path.exists(self.config_path):
            # Return default rules if config not found
            return {
                "move_to": {"required": True, "reason": "Arm movement requires approval"},
                "emergency_stop": {"required": True, "reason": "Emergency stop requires confirmation"},
            }

        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        return data.get("approval_rules", {})

    def priority(self) -> int:
        """Return priority 4 (after Conflict detector priority 3).

        Returns:
            Priority level 4.
        """
        return 4

    async def check_requires_approval(self, action: Action) -> ValidationResult:
        """Check if action requires human approval.

        Args:
            action: The Action object to check.

        Returns:
            ValidationResult with requires_human_approval flag set appropriately.
        """
        action_type = action.action_type.value

        # Check if action is in approval rules and marked as required
        if action_type in self._rules:
            rule = self._rules[action_type]
            if rule.get("required", False):
                return ValidationResult(
                    valid=True,
                    validator="second_confirmation",
                    requires_human_approval=True,
                    reason=rule.get("reason", "human approval required"),
                )

        # Action does not require approval
        return ValidationResult(
            valid=True,
            validator="second_confirmation",
            requires_human_approval=False,
        )

    async def validate_action(
        self, action: Action, robot_state: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate action - delegates to check_requires_approval.

        Args:
            action: The Action object to validate.
            robot_state: Optional robot state dictionary (unused by SecondConfirmation).

        Returns:
            ValidationResult with requires_human_approval flag set.
        """
        return await self.check_requires_approval(action)
