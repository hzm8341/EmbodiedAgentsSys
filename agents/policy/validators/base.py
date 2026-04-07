"""Validator abstract base class for policy validation layer."""

from abc import ABC, abstractmethod
from agents.policy.action_proposal import Action, ValidationResult


class Validator(ABC):
    """Abstract base class for all policy validators.

    All validators in the three-layer policy validation pipeline must inherit
    from this base class and implement the required methods.
    """

    @abstractmethod
    async def validate_action(self, action: Action) -> ValidationResult:
        """Validate a single action and return ValidationResult.

        Args:
            action: The Action object to validate.

        Returns:
            ValidationResult with valid flag and reason.
        """
        ...

    def priority(self) -> int:
        """Execution priority: lower number = earlier execution.

        Default priority is 100. Subclasses can override to execute earlier/later.
        Priority 1 is reserved for critical whitelist validation.

        Returns:
            Priority level (lower = earlier execution).
        """
        return 100
