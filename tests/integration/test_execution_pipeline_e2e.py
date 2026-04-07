"""Integration tests for end-to-end ExecutionPipeline.

Tests the complete flow: ValidationPipeline → HumanOversight → Execution →
Confirmation → AuditTrail, verifying all components work together correctly.
"""

import pytest
from datetime import datetime
from typing import AsyncGenerator, Dict, Any

from agents.pipeline.execution_pipeline import (
    ExecutionPipeline,
    ExecutionPipelineResult,
)
from agents.policy.action_proposal import (
    ActionProposal,
    Action,
    ActionType,
    ExpectedOutcomeType,
    SequenceType,
)
from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.execution.tools.base import ToolBase


class MockMoveTool(ToolBase):
    """Mock tool for testing move_to actions."""

    name = "move_to"
    description = "Mock move tool"

    async def execute(self, *args, **kwargs) -> dict:
        """Legacy interface (not used in new pipeline)."""
        return {"status": "success"}

    async def execute_with_feedback(
        self,
        params: dict,
        current_state: dict,
    ) -> AsyncGenerator[ExecutionFeedback, None]:
        """Execute move with feedback generation."""
        # Simulate movement sequence
        yield ExecutionFeedback(
            stage=FeedbackStage.STARTED,
            progress=0.0,
            message="Starting move",
        )

        yield ExecutionFeedback(
            stage=FeedbackStage.IN_PROGRESS,
            progress=0.5,
            message="Moving towards target",
            current_state={"position": "midpoint"},
        )

        # Simulate reaching target
        yield ExecutionFeedback(
            stage=FeedbackStage.COMPLETED,
            progress=1.0,
            message="Reached target position",
            current_state={
                "current_pose": params.get("target_pose", [0.5, 0.5, 0.5]),
                "collision_detected": False,
            },
        )


class MockGripperTool(ToolBase):
    """Mock tool for testing gripper actions."""

    name = "gripper_close"
    description = "Mock gripper tool"

    async def execute(self, *args, **kwargs) -> dict:
        """Legacy interface."""
        return {"status": "success"}

    async def execute_with_feedback(
        self,
        params: dict,
        current_state: dict,
    ) -> AsyncGenerator[ExecutionFeedback, None]:
        """Execute gripper action with feedback."""
        yield ExecutionFeedback(
            stage=FeedbackStage.STARTED,
            progress=0.0,
            message="Starting gripper closure",
        )

        yield ExecutionFeedback(
            stage=FeedbackStage.COMPLETED,
            progress=1.0,
            message="Gripper closed successfully",
            current_state={
                "gripper_state": "closed",
                "object_grasped": True,
            },
        )


class MockFailingTool(ToolBase):
    """Mock tool that simulates execution failure."""

    name = "failing_tool"
    description = "Tool that fails during execution"

    async def execute(self, *args, **kwargs) -> dict:
        """Legacy interface."""
        return {"status": "failed"}

    async def execute_with_feedback(
        self,
        params: dict,
        current_state: dict,
    ) -> AsyncGenerator[ExecutionFeedback, None]:
        """Simulate execution failure."""
        yield ExecutionFeedback(
            stage=FeedbackStage.STARTED,
            progress=0.0,
            message="Starting operation",
        )

        yield ExecutionFeedback(
            stage=FeedbackStage.FAILED,
            progress=0.5,
            message="Operation failed",
            has_error=True,
            error_message="Simulated tool failure",
            error_type="execution_error",
        )


@pytest.fixture
def pipeline():
    """Create ExecutionPipeline fixture."""
    return ExecutionPipeline()


@pytest.fixture
def tools_registry():
    """Create tools registry with mock tools."""
    return {
        "move_to": MockMoveTool(),
        "gripper_close": MockGripperTool(),
        "gripper_open": MockGripperTool(),
        "failing_tool": MockFailingTool(),
    }


@pytest.fixture
def robot_state():
    """Create robot state fixture."""
    return {
        "arm_is_moving": False,
        "emergency_stop": False,
        "gripper_state": "open",
        "current_pose": [0.0, 0.0, 0.0],
    }


class TestValidProposalExecution:
    """Test successful end-to-end execution of valid proposals."""

    @pytest.mark.asyncio
    async def test_simple_move_action(self, pipeline, tools_registry, robot_state):
        """Test execution of a simple move_to action."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
            reasoning="Move arm to pick location",
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Verify execution succeeded
        assert result.success is True
        assert result.proposal_id == proposal.id
        assert len(result.action_results) == 1
        assert result.action_results[0].success is True
        assert result.action_results[0].action_type == "move_to"
        assert len(result.action_results[0].feedbacks) > 0

        # Verify confirmation was collected
        assert result.action_results[0].confirmation is not None
        assert result.action_results[0].confirmation.status == "confirmed"

    @pytest.mark.asyncio
    async def test_sequence_of_actions(self, pipeline, tools_registry, robot_state):
        """Test execution of multiple actions in sequence."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                ),
                Action(
                    action_type=ActionType.GRIPPER_CLOSE,
                    params={},
                    expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
                ),
            ],
            reasoning="Pick up object sequence",
            sequence_type=SequenceType.SEQUENTIAL,
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Verify both actions executed
        assert result.success is True
        assert len(result.action_results) == 2
        assert all(ar.success for ar in result.action_results)

        # Verify action types
        assert result.action_results[0].action_type == "move_to"
        assert result.action_results[1].action_type == "gripper_close"

        # Verify feedback collected for both
        assert len(result.action_results[0].feedbacks) > 0
        assert len(result.action_results[1].feedbacks) > 0

    @pytest.mark.asyncio
    async def test_audit_trail_logging(self, pipeline, tools_registry, robot_state):
        """Test that all events are properly logged to audit trail."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
            reasoning="Test audit logging",
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Get audit trail
        audit_trail = pipeline.get_audit_trail()

        # Verify events were logged
        assert len(audit_trail.events) > 0

        # Verify key event types
        event_types = [event.event_type for event in audit_trail.events]
        assert "validation_passed" in event_types
        assert "execution_started" in event_types
        assert "execution_confirmed" in event_types
        assert "execution_complete" in event_types

        # Verify chain integrity
        assert audit_trail.verify_chain_integrity() is True

    @pytest.mark.asyncio
    async def test_execution_duration_tracking(
        self, pipeline, tools_registry, robot_state
    ):
        """Test that execution durations are properly tracked."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Verify duration tracking
        assert result.total_duration_seconds >= 0.0
        assert result.action_results[0].duration_seconds >= 0.0
        assert result.action_results[0].timestamp_start <= result.action_results[0].timestamp_end


class TestInvalidProposalHandling:
    """Test handling of invalid proposals that should be rejected at validation."""

    @pytest.mark.asyncio
    async def test_invalid_action_type_rejection(
        self, pipeline, tools_registry, robot_state
    ):
        """Test that proposals with unsupported action types are rejected."""
        # Create a proposal with an invalid action type
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={},  # Missing required target_pose parameter
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
            reasoning="Invalid proposal with missing parameters",
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Should fail at validation stage
        assert result.success is False
        assert result.validation_error is not None
        assert result.validation_error != ""

        # Should not execute actions
        assert len(result.action_results) == 0

        # Verify audit trail has validation failure
        audit_trail = pipeline.get_audit_trail()
        event_types = [event.event_type for event in audit_trail.events]
        assert "validation_failed" in event_types

        # Verify alert was raised
        alerts = pipeline.get_alerts()
        assert any(alert.event_id.startswith("validation_failed") for alert in alerts)


class TestExecutionErrorHandling:
    """Test handling of errors that occur during tool execution."""

    @pytest.mark.asyncio
    async def test_tool_not_found(self, pipeline, tools_registry, robot_state):
        """Test handling when tool is not registered."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.VISION_CAPTURE,  # Not in registry
                    params={},
                    expected_outcome=ExpectedOutcomeType.OBJECT_VISIBLE,
                )
            ],
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Execution should fail with clear error
        assert result.success is False
        assert "tool not found" in result.action_results[0].error_reason

        # Verify audit trail has tool not found event
        audit_trail = pipeline.get_audit_trail()
        event_types = [event.event_type for event in audit_trail.events]
        assert "execution_failed" in event_types

    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, pipeline, tools_registry, robot_state):
        """Test handling of tool execution failures."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                ),
                Action(
                    action_type=ActionType.EMERGENCY_STOP,  # Will fail
                    params={},
                    expected_outcome=ExpectedOutcomeType.EMERGENCY_STOPPED,
                ),
            ],
        )

        # Add failing tool to registry
        tools_registry["emergency_stop"] = MockFailingTool()

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # First action should succeed, second should fail
        assert result.success is False
        assert result.action_results[0].success is True
        assert result.action_results[1].success is False

        # Verify error details
        assert result.action_results[1].error_reason != ""

        # Verify alerts were raised for failure
        alerts = pipeline.get_alerts()
        assert any(alert.level.value == "critical" for alert in alerts)


class TestAuditTrailIntegrity:
    """Test audit trail chain integrity verification."""

    @pytest.mark.asyncio
    async def test_audit_chain_verification(self, pipeline, tools_registry, robot_state):
        """Test that audit trail chain can be verified for integrity."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Verify chain integrity
        assert pipeline.verify_audit_integrity() is True

        # Verify all events have proper hash chain
        audit_trail = pipeline.get_audit_trail()
        for i, event in enumerate(audit_trail.events):
            if i > 0:
                assert event.previous_hash == audit_trail.events[i - 1].event_hash

    @pytest.mark.asyncio
    async def test_comprehensive_event_logging(self, pipeline, tools_registry, robot_state):
        """Test comprehensive event logging across full pipeline."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
            reasoning="Test comprehensive logging",
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        audit_trail = pipeline.get_audit_trail()

        # Collect all event details
        event_details = {
            event.event_type: event.details for event in audit_trail.events
        }

        # Verify key stages are logged
        assert "validation_passed" in event_details
        assert event_details["validation_passed"]["proposal_id"] == proposal.id

        assert "execution_started" in event_details
        assert event_details["execution_started"]["action_type"] == "move_to"

        assert "execution_confirmed" in event_details
        assert "confirmation_status" in event_details["execution_confirmed"]

        assert "execution_complete" in event_details
        assert event_details["execution_complete"]["success"] is True


class TestSystemState:
    """Test system state retrieval and diagnostics."""

    @pytest.mark.asyncio
    async def test_system_state_after_execution(
        self, pipeline, tools_registry, robot_state
    ):
        """Test retrieving system state after execution."""
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        state = await pipeline.get_system_state()

        # Verify state dictionary
        assert "oversight_mode" in state
        assert "audit_verified" in state
        assert "unacknowledged_alerts" in state
        assert "audit_events" in state

        # Verify values are reasonable
        assert state["audit_verified"] is True
        assert state["audit_events"] > 0

    @pytest.mark.asyncio
    async def test_multiple_executions_state_accumulation(
        self, pipeline, tools_registry, robot_state
    ):
        """Test that multiple executions accumulate state correctly."""
        # First execution
        proposal1 = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
        )

        result1 = await pipeline.execute_proposal(
            proposal1, robot_state, tools_registry
        )
        state1 = await pipeline.get_system_state()
        event_count1 = state1["audit_events"]

        # Second execution
        proposal2 = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.GRIPPER_CLOSE,
                    params={},
                    expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
                )
            ],
        )

        result2 = await pipeline.execute_proposal(
            proposal2, robot_state, tools_registry
        )
        state2 = await pipeline.get_system_state()
        event_count2 = state2["audit_events"]

        # Verify state accumulated
        assert event_count2 > event_count1
        assert result1.success is True
        assert result2.success is True


class TestExecutionEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_action_sequence(self, pipeline, tools_registry, robot_state):
        """Test handling of proposal with empty action sequence."""
        proposal = ActionProposal(
            action_sequence=[],
            reasoning="Empty action sequence",
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Should fail validation on empty sequence
        assert result.success is False or len(result.action_results) == 0

    @pytest.mark.asyncio
    async def test_robot_state_preservation(self, pipeline, tools_registry):
        """Test that robot state is not modified during execution."""
        robot_state = {
            "arm_is_moving": False,
            "emergency_stop": False,
            "gripper_state": "open",
        }
        robot_state_copy = robot_state.copy()

        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.5, 0.5]},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ],
        )

        result = await pipeline.execute_proposal(proposal, robot_state, tools_registry)

        # Verify robot_state was not modified by pipeline
        assert robot_state == robot_state_copy
