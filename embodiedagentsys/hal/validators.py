"""Action validators for P1安全优先 and P6白名单制度."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Result of action validation."""
    valid: bool
    reason: Optional[str] = None
    warning: Optional[str] = None


class ActionValidator:
    """White-list based action validator.

    Following P6安全机制层 - 白名单制度:
    - All executable actions must be pre-registered in whitelist
    - Unauthorized actions are rejected without exception
    - Parameter ranges are enforced
    """

    def __init__(
        self,
        allowed_actions: list[str],
        param_constraints: Optional[dict] = None
    ):
        """
        Args:
            allowed_actions: List of allowed action types.
            param_constraints: Dict mapping action_type to param bounds.
                              e.g., {"move_to": {"x": (-2.0, 2.0), ...}}
        """
        self._allowed = set(allowed_actions)
        self._constraints = param_constraints or {}

    def validate(self, action_type: str, params: dict) -> ValidationResult:
        """Validate action against whitelist and constraints.

        Args:
            action_type: Type of action to validate.
            params: Action parameters.

        Returns:
            ValidationResult with valid=True if allowed.
        """
        # Check whitelist (P6 - 白名单制度)
        if action_type not in self._allowed:
            return ValidationResult(
                valid=False,
                reason=f"Action '{action_type}' not in whitelist"
            )

        # Check parameter constraints
        if action_type in self._constraints:
            bounds = self._constraints[action_type]
            for param_name, (min_val, max_val) in bounds.items():
                if param_name in params:
                    value = params[param_name]
                    if not (min_val <= value <= max_val):
                        return ValidationResult(
                            valid=False,
                            reason=f"Parameter '{param_name}' value {value} out of bounds [{min_val}, {max_val}]"
                        )

        return ValidationResult(valid=True)

    def add_action(self, action_type: str) -> None:
        """Dynamically add action to whitelist."""
        self._allowed.add(action_type)

    def remove_action(self, action_type: str) -> None:
        """Remove action from whitelist."""
        self._allowed.discard(action_type)
