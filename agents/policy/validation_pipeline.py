"""Two-level validation pipeline orchestrating all policy validators.

This module implements the orchestration layer that combines all four validators
(WhitelistValidator, BoundaryChecker, ConflictDetector, SecondConfirmation) into
a two-level validation system:

- Layer 1 (Local, always-on): WhitelistValidator → BoundaryChecker
- Layer 2 (Central, can degrade): ConflictDetector → SecondConfirmation → Custom validators

The pipeline uses fail-fast semantics: returns immediately on the first validation error.
"""

from typing import Any, Dict, List, Optional

from agents.policy.action_proposal import ActionProposal, Action, ValidationResult
from agents.policy.validators.base import Validator
from agents.policy.validators.whitelist import WhitelistValidator
from agents.policy.validators.boundary import BoundaryChecker
from agents.policy.validators.conflict import ConflictDetector
from agents.policy.validators.confirmation import SecondConfirmation


class TwoLevelValidationPipeline:
    """Orchestrates two-level validation pipeline for action proposals.

    Layer 1 (Local, always-on validators):
    - Priority 1: WhitelistValidator - checks action types and parameters
    - Priority 2: BoundaryChecker - enforces physical workspace boundaries

    Layer 2 (Central, can degrade validators):
    - Priority 3: ConflictDetector - checks robot state conflicts
    - Priority 4: SecondConfirmation - marks high-risk actions for approval
    - Priority 50+: Custom validators (registered by user)

    The pipeline uses fail-fast semantics: stops validation on first failure
    and returns the ValidationResult immediately.
    """

    def __init__(self):
        """Initialize the two-level validation pipeline with built-in validators."""
        # Layer 1: Local validators (always-on)
        self._layer1_validators: List[Validator] = [
            WhitelistValidator(),
            BoundaryChecker(),
        ]

        # Layer 2: Central validators (can degrade)
        self._layer2_validators: List[Validator] = [
            ConflictDetector(),
            SecondConfirmation(),
        ]

        # Custom validators (registered by user, priority 50+)
        self._custom_validators: List[Validator] = []

    def register_custom_validator(self, validator: Validator) -> None:
        """Register a custom validator in Layer 2.

        Custom validators are executed after built-in validators in Layer 2,
        sorted by priority() method. Lower priority values execute earlier.

        Args:
            validator: A Validator instance to register.
        """
        self._custom_validators.append(validator)
        # Keep custom validators sorted by priority
        self._custom_validators.sort(key=lambda v: v.priority())

    async def validate_proposal(
        self, proposal: ActionProposal, robot_state: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate an action proposal through the two-level pipeline.

        Validates each action in the sequence using fail-fast semantics:
        - Stops on first validation error
        - Aggregates requires_human_approval across all actions
        - Returns result indicating overall validity

        Args:
            proposal: ActionProposal to validate containing action sequence.
            robot_state: Optional dictionary containing current robot state flags.
                Example: {"arm_is_moving": False, "emergency_stop": False}

        Returns:
            ValidationResult with:
            - valid: True if all actions pass all validators
            - requires_human_approval: True if any action requires approval
            - reason: Error message (if valid=False) or empty string
            - validator: Name of validator that failed (if valid=False)
        """
        if robot_state is None:
            robot_state = {}

        # Track whether any action requires human approval
        requires_approval = False
        last_validator = "pipeline"

        # Validate each action in sequence (fail-fast)
        for action in proposal.action_sequence:
            result = await self._validate_single_action(action, robot_state)
            last_validator = result.validator

            # Fail-fast: return immediately on first error
            if not result.valid:
                return result

            # Aggregate approval requirements
            if result.requires_human_approval:
                requires_approval = True

        # All actions passed validation
        return ValidationResult(
            valid=True,
            reason="All actions passed validation",
            validator=last_validator,
            requires_human_approval=requires_approval,
        )

    async def _validate_single_action(
        self, action: Action, robot_state: Dict[str, Any]
    ) -> ValidationResult:
        """Validate a single action through all validator layers.

        Runs validators in two layers with priority ordering within each layer:
        - Layer 1: WhitelistValidator (priority 1), BoundaryChecker (priority 2)
        - Layer 2: ConflictDetector (priority 3), SecondConfirmation (priority 4),
                   then custom validators in priority order

        Returns on first failure (fail-fast).

        Args:
            action: The Action to validate.
            robot_state: Current robot state dictionary.

        Returns:
            ValidationResult from first failing validator, or success result
            with aggregated approval requirements.
        """
        # Combine all validators and sort by priority
        all_validators = (
            self._layer1_validators + self._layer2_validators + self._custom_validators
        )
        all_validators.sort(key=lambda v: v.priority())

        # Track if any validator marks for approval (don't fail on approval)
        requires_approval = False
        last_validator_name = "pipeline"

        # Run all validators in priority order (fail-fast)
        for validator in all_validators:
            result = await validator.validate_action(action, robot_state)
            last_validator_name = result.validator

            # Fail-fast: return immediately on validation error
            if not result.valid:
                return result

            # Track approval requirement (don't fail, just note it)
            if result.requires_human_approval:
                requires_approval = True

        # All validators passed - return success with approval flag
        return ValidationResult(
            valid=True,
            reason="Action passed all validators",
            validator=last_validator_name,
            requires_human_approval=requires_approval,
        )
