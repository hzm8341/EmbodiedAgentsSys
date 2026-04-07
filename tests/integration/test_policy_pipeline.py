"""Integration tests for TwoLevelValidationPipeline."""

import pytest
from agents.policy.action_proposal import (
    ActionProposal, Action, ActionType, ExpectedOutcomeType
)


@pytest.fixture
def valid_move():
    """Fixture: valid move_to action within workspace."""
    return ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.MOVE_TO,
                params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )
        ]
    )


@pytest.fixture
def out_of_workspace():
    """Fixture: move_to action outside workspace boundaries."""
    return ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.MOVE_TO,
                params={"target_pose": [99, 99, 99], "speed": 0.5},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )
        ]
    )


class TestTwoLevelValidationPipeline:
    """Test suite for TwoLevelValidationPipeline orchestration."""

    @pytest.mark.asyncio
    async def test_valid_proposal_passes(self, valid_move):
        """Test that valid action proposal passes all validators."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": False, "emergency_stop": False}
        result = await pipeline.validate_proposal(valid_move, robot_state)

        assert result.valid

    @pytest.mark.asyncio
    async def test_out_of_workspace_rejected(self, out_of_workspace):
        """Test that out-of-bounds move_to action is rejected by BoundaryChecker."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": False, "emergency_stop": False}
        result = await pipeline.validate_proposal(out_of_workspace, robot_state)

        assert result.valid is False
        assert "boundary" in result.validator.lower()

    @pytest.mark.asyncio
    async def test_move_to_requires_approval(self, valid_move):
        """Test that move_to actions are marked as requiring human approval."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": False, "emergency_stop": False}
        result = await pipeline.validate_proposal(valid_move, robot_state)

        assert result.valid
        assert result.requires_human_approval

    @pytest.mark.asyncio
    async def test_custom_validator_registered(self, valid_move):
        """Test that custom validators can be registered and executed."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline
        from agents.policy.validators.base import Validator
        from agents.policy.action_proposal import Action, ValidationResult

        class AlwaysRejectValidator(Validator):
            """Custom validator that always rejects actions."""

            async def validate_action(self, action: Action, robot_state=None) -> ValidationResult:
                return ValidationResult(
                    valid=False,
                    reason="always rejected",
                    validator="custom"
                )

            def priority(self):
                return 50

        pipeline = TwoLevelValidationPipeline()
        pipeline.register_custom_validator(AlwaysRejectValidator())
        robot_state = {"arm_is_moving": False, "emergency_stop": False}
        result = await pipeline.validate_proposal(valid_move, robot_state)

        assert result.valid is False
        assert result.validator == "custom"

    @pytest.mark.asyncio
    async def test_gripper_action_no_approval(self):
        """Test that gripper actions don't require approval."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        gripper_close = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.GRIPPER_CLOSE,
                    params={"force": 10.0},
                    expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
                )
            ]
        )

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": False, "emergency_stop": False, "gripper_holding": False}
        result = await pipeline.validate_proposal(gripper_close, robot_state)

        assert result.valid
        assert result.requires_human_approval is False

    @pytest.mark.asyncio
    async def test_emergency_stop_rejected(self, valid_move):
        """Test that actions are rejected when emergency_stop is active."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": False, "emergency_stop": True}
        result = await pipeline.validate_proposal(valid_move, robot_state)

        assert result.valid is False

    @pytest.mark.asyncio
    async def test_arm_already_moving_rejected(self, valid_move):
        """Test that move_to is rejected when arm is already moving."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": True, "emergency_stop": False}
        result = await pipeline.validate_proposal(valid_move, robot_state)

        assert result.valid is False

    @pytest.mark.asyncio
    async def test_fail_fast_returns_first_error(self):
        """Test that validation fails fast on first error."""
        from agents.policy.validation_pipeline import TwoLevelValidationPipeline

        # Invalid action type should be caught by WhitelistValidator
        invalid_proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [99, 99, 99], "speed": 0.5},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ]
        )

        pipeline = TwoLevelValidationPipeline()
        robot_state = {"arm_is_moving": False, "emergency_stop": False}
        result = await pipeline.validate_proposal(invalid_proposal, robot_state)

        # Should fail on boundary check (first failure in sequence)
        assert result.valid is False
