"""Tests for ExecutionConfirmationEngine."""

import pytest
import time
from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.policy.action_proposal import Action, ActionType, ExpectedOutcomeType


def _make_feedback(stage, progress=1.0):
    """Helper to create test feedback."""
    return ExecutionFeedback(
        stage=stage, progress=progress, current_state={}, timestamp=time.time()
    )


class TestExecutionConfirmationEngine:
    @pytest.mark.asyncio
    async def test_confirmed_when_pose_accurate(self):
        """Test confirmation when arm reaches target pose within tolerance."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        actual_state = {
            "current_pose": [0.5, 0.3, 0.2],
            "collision_detected": False,
        }
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "confirmed"

    @pytest.mark.asyncio
    async def test_failed_when_pose_error_too_large(self):
        """Test failure when pose error exceeds tolerance."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        actual_state = {"current_pose": [1.0, 1.0, 1.0], "collision_detected": False}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_timeout_when_execution_too_slow(self):
        """Test timeout when execution exceeds time limit."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        actual_state = {
            "current_pose": [0.5, 0.3, 0.2],
            "collision_detected": False,
        }
        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(
                stage=FeedbackStage.STARTED,
                progress=0.0,
                current_state={},
                timestamp=t0,
            ),
            ExecutionFeedback(
                stage=FeedbackStage.COMPLETED,
                progress=1.0,
                current_state={},
                timestamp=t0 + 100,
            ),  # exceeds timeout
        ]
        result = await engine.confirm(
            action, feedbacks, actual_state, timeout_seconds=5.0
        )
        assert result.status == "timeout"

    @pytest.mark.asyncio
    async def test_confirmed_grasp_outcome(self):
        """Test confirmation for object grasped outcome."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 50.0},
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )
        actual_state = {"gripper_holding": True}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "confirmed"

    @pytest.mark.asyncio
    async def test_failed_grasp_outcome(self):
        """Test failure when object not grasped."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 50.0},
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )
        actual_state = {"gripper_holding": False}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_confirmed_release_outcome(self):
        """Test confirmation for object released outcome."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.GRIPPER_OPEN,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_RELEASED,
        )
        actual_state = {"gripper_holding": False}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "confirmed"

    @pytest.mark.asyncio
    async def test_failed_release_outcome(self):
        """Test failure when object still held."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.GRIPPER_OPEN,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_RELEASED,
        )
        actual_state = {"gripper_holding": True}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_confirmed_vision_outcome(self):
        """Test confirmation for object visible outcome."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.VISION_CAPTURE,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_VISIBLE,
        )
        actual_state = {"object_visible": True}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "confirmed"

    @pytest.mark.asyncio
    async def test_failed_vision_outcome(self):
        """Test failure when object not visible."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.VISION_CAPTURE,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_VISIBLE,
        )
        actual_state = {"object_visible": False}
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_failed_when_collision_detected(self):
        """Test failure when collision is detected."""
        from agents.execution.confirmation import ExecutionConfirmationEngine

        engine = ExecutionConfirmationEngine()
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        actual_state = {
            "current_pose": [0.5, 0.3, 0.2],
            "collision_detected": True,
        }
        feedbacks = [
            _make_feedback(FeedbackStage.STARTED, 0.0),
            _make_feedback(FeedbackStage.COMPLETED, 1.0),
        ]
        result = await engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed"
        assert "collision" in result.reason.lower()
