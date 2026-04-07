"""Test cases for policy validators (base class and implementations)."""

import pytest
from agents.policy.action_proposal import (
    ActionProposal,
    Action,
    ActionType,
    ExpectedOutcomeType,
)


@pytest.fixture
def move_proposal():
    """Create a valid move_to action proposal."""
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
def gripper_proposal():
    """Create a valid gripper_close action proposal."""
    return ActionProposal(
        action_sequence=[
            Action(
                action_type=ActionType.GRIPPER_CLOSE,
                params={"force": 60},
                expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
            )
        ]
    )


class TestWhitelistValidator:
    """Test suite for WhitelistValidator."""

    @pytest.mark.asyncio
    async def test_accept_move_to(self, move_proposal):
        """Test that valid move_to action is accepted."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        for action in move_proposal.action_sequence:
            result = await v.validate_action(action)
        assert result.valid

    @pytest.mark.asyncio
    async def test_reject_unknown_action(self):
        """Test that unknown action types are rejected."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        # Test validate_action_type
        result = await v.validate_action_type("disable_safety_check")
        assert result.valid is False
        assert "whitelist" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_reject_missing_required_param(self):
        """Test that actions with missing required params are rejected."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        # move_to missing speed param
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2]},  # missing speed
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        result = await v.validate_action(action)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_reject_param_out_of_range(self):
        """Test that parameters outside valid range are rejected."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 200},  # exceeds max=100
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )
        result = await v.validate_action(action)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_accept_gripper_open_no_params(self):
        """Test that gripper_open action without params is accepted."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        action = Action(
            action_type=ActionType.GRIPPER_OPEN,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_RELEASED,
        )
        result = await v.validate_action(action)
        assert result.valid

    @pytest.mark.asyncio
    async def test_accept_vision_capture(self):
        """Test that vision_capture action is accepted."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        action = Action(
            action_type=ActionType.VISION_CAPTURE,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_VISIBLE,
        )
        result = await v.validate_action(action)
        assert result.valid

    @pytest.mark.asyncio
    async def test_accept_emergency_stop(self):
        """Test that emergency_stop action is accepted."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        action = Action(
            action_type=ActionType.EMERGENCY_STOP,
            params={},
            expected_outcome=ExpectedOutcomeType.EMERGENCY_STOPPED,
        )
        result = await v.validate_action(action)
        assert result.valid

    @pytest.mark.asyncio
    async def test_validator_priority(self):
        """Test that WhitelistValidator has correct priority."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        assert v.priority() == 1

    @pytest.mark.asyncio
    async def test_param_list_length_validation(self):
        """Test that list parameter length is validated."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        # move_to with wrong target_pose length
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3], "speed": 0.5},  # should be length 3
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        result = await v.validate_action(action)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_speed_param_range(self):
        """Test that speed parameter range is validated."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        # move_to with speed too low
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.001},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        result = await v.validate_action(action)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_speed_param_max(self):
        """Test that speed parameter max is validated."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        # move_to with speed too high
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 1.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        result = await v.validate_action(action)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_force_param_min(self):
        """Test that force parameter min is validated."""
        from agents.policy.validators.whitelist import WhitelistValidator

        v = WhitelistValidator()
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": -1},  # negative force
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )
        result = await v.validate_action(action)
        assert result.valid is False


class TestBoundaryChecker:
    """Test suite for BoundaryChecker validator."""

    @pytest.mark.asyncio
    async def test_accept_pose_in_workspace(self, move_proposal):
        """Test that pose within workspace boundaries is accepted."""
        from agents.policy.validators.boundary import BoundaryChecker

        checker = BoundaryChecker()
        for action in move_proposal.action_sequence:
            result = await checker.validate_action(action)
        assert result.valid

    @pytest.mark.asyncio
    async def test_reject_pose_out_of_workspace(self):
        """Test that pose outside workspace boundaries is rejected."""
        from agents.policy.validators.boundary import BoundaryChecker

        checker = BoundaryChecker()
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [10.0, 10.0, 10.0], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        result = await checker.validate_action(action)
        assert result.valid is False
        assert "workspace" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_accept_gripper_force_in_limit(self, gripper_proposal):
        """Test that gripper force within limits is accepted."""
        from agents.policy.validators.boundary import BoundaryChecker

        checker = BoundaryChecker()
        for action in gripper_proposal.action_sequence:
            result = await checker.validate_action(action)
        assert result.valid

    @pytest.mark.asyncio
    async def test_reject_gripper_force_over_limit(self):
        """Test that gripper force exceeding limit is rejected."""
        from agents.policy.validators.boundary import BoundaryChecker

        checker = BoundaryChecker()
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 150},
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )
        result = await checker.validate_action(action)
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_skip_non_movement_actions(self):
        """Test that non-movement actions are skipped and pass validation."""
        from agents.policy.validators.boundary import BoundaryChecker

        checker = BoundaryChecker()
        action = Action(
            action_type=ActionType.VISION_CAPTURE,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_VISIBLE,
        )
        result = await checker.validate_action(action)
        assert result.valid
