"""BoundaryChecker validator for physical safety boundaries."""

import os
from typing import Any, Dict, List, Optional
import yaml

from agents.policy.action_proposal import Action, ActionType, ValidationResult
from agents.policy.validators.base import Validator


class BoundaryChecker(Validator):
    """Validator that enforces physical safety boundaries for workspace and gripper forces.

    This validator checks that:
    - Robot end-effector poses stay within defined workspace boundaries (x, y, z)
    - Gripper forces stay within minimum and maximum limits

    Priority is 2 (executes after WhitelistValidator priority 1).
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize BoundaryChecker with safety limit configuration.

        Args:
            config_path: Path to safety_limits.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default to config/safety_limits.yaml relative to project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            config_path = os.path.join(project_root, "config", "safety_limits.yaml")

        self.config_path = config_path
        self.safety_limits = self._load_safety_limits()

    def _load_safety_limits(self) -> Dict[str, Any]:
        """Load safety limit configuration from YAML file.

        Returns:
            Dictionary containing safety limit configuration.

        Raises:
            FileNotFoundError: If safety_limits.yaml is not found.
            yaml.YAMLError: If YAML parsing fails.
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Safety limits config not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ValueError(f"Safety limits config is empty: {self.config_path}")

        return config

    def priority(self) -> int:
        """Return priority 2 (after WhitelistValidator priority 1).

        Returns:
            Priority level 2.
        """
        return 2

    async def validate_action(
        self, action: Action, robot_state: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate a single action against physical safety boundaries.

        Args:
            action: The Action object to validate.
            robot_state: Optional robot state dictionary (unused by BoundaryChecker).

        Returns:
            ValidationResult with valid flag and reason.
        """
        # Check MOVE_TO actions for workspace boundaries
        if action.action_type == ActionType.MOVE_TO:
            target_pose = action.params.get("target_pose")
            if target_pose is not None:
                return self._check_pose(target_pose)

        # Check GRIPPER_CLOSE actions for force limits
        if action.action_type == ActionType.GRIPPER_CLOSE:
            force = action.params.get("force")
            if force is not None:
                return self._check_gripper_force(force)

        # Skip other action types - they don't have physical boundaries
        return ValidationResult(
            valid=True,
            reason=f"Action '{action.action_type.value}' does not require boundary checking",
            validator="BoundaryChecker",
        )

    def _check_pose(self, pose: List[float]) -> ValidationResult:
        """Validate 3D pose against workspace boundaries.

        Args:
            pose: 3D pose [x, y, z] in meters.

        Returns:
            ValidationResult indicating if pose is within workspace.
        """
        if not isinstance(pose, (list, tuple)) or len(pose) != 3:
            return ValidationResult(
                valid=False,
                reason=f"Pose must be a list/tuple of 3 elements, got {len(pose) if isinstance(pose, (list, tuple)) else 'non-sequence'}",
                validator="BoundaryChecker",
            )

        workspace = self.safety_limits.get("workspace", {})
        axes = [
            ("x", 0, workspace.get("x", {})),
            ("y", 1, workspace.get("y", {})),
            ("z", 2, workspace.get("z", {})),
        ]

        for axis_name, idx, axis_limits in axes:
            min_val = axis_limits.get("min")
            max_val = axis_limits.get("max")
            value = pose[idx]

            if min_val is not None and value < min_val:
                return ValidationResult(
                    valid=False,
                    reason=f"Workspace boundary violation: {axis_name}={value} is below minimum {min_val}",
                    validator="BoundaryChecker",
                )

            if max_val is not None and value > max_val:
                return ValidationResult(
                    valid=False,
                    reason=f"Workspace boundary violation: {axis_name}={value} exceeds maximum {max_val}",
                    validator="BoundaryChecker",
                )

        return ValidationResult(
            valid=True,
            reason=f"Pose {pose} is within workspace boundaries",
            validator="BoundaryChecker",
        )

    def _check_gripper_force(self, force: float) -> ValidationResult:
        """Validate gripper force against limits.

        Args:
            force: Gripper closing force in Newtons.

        Returns:
            ValidationResult indicating if force is within limits.
        """
        if not isinstance(force, (int, float)):
            return ValidationResult(
                valid=False,
                reason=f"Force must be a number, got {type(force).__name__}",
                validator="BoundaryChecker",
            )

        gripper_limits = self.safety_limits.get("gripper_limits", {})
        min_force = gripper_limits.get("min_force", 0)
        max_force = gripper_limits.get("max_force", 100)

        if force < min_force:
            return ValidationResult(
                valid=False,
                reason=f"Gripper force {force}N is below minimum {min_force}N",
                validator="BoundaryChecker",
            )

        if force > max_force:
            return ValidationResult(
                valid=False,
                reason=f"Gripper force {force}N exceeds maximum {max_force}N",
                validator="BoundaryChecker",
            )

        return ValidationResult(
            valid=True,
            reason=f"Gripper force {force}N is within limits [{min_force}N, {max_force}N]",
            validator="BoundaryChecker",
        )
