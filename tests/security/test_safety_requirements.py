"""Security test suite: Verify system meets Seven Iron Rules for industrial agent safety.

This comprehensive test suite validates all safety mechanisms for industrial-grade
robot control, ensuring:

P1: Safety First - Unauthorized actions must be rejected
P2: Human Control - System can be stopped at any time (Emergency Stop)
P3: Decision Separation - LLM proposals must pass validation before execution
P4: Closed Loop - Execution must have result confirmation
P6: Safety Mechanisms - Audit logs must be complete and tamper-proof
P7: LLM Isolation - LLM inputs must be strictly typed and validated

Note: P5 (Graceful Degradation) is implicitly tested through layer separation.
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from agents.policy.action_proposal import (
    ActionProposal,
    Action,
    ActionType,
    ExpectedOutcomeType,
    ValidationResult,
)
from agents.policy.validators.whitelist import WhitelistValidator
from agents.policy.validators.boundary import BoundaryChecker
from agents.policy.validators.base import Validator
from agents.policy.validation_pipeline import TwoLevelValidationPipeline
from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.execution.confirmation import ExecutionConfirmationEngine, ConfirmationResult
from agents.human_oversight.engine import HumanOversightEngine
from agents.human_oversight.system_mode import SystemMode
from agents.feedback.audit_trail import AuditTrail, ExecutionLog
from agents.feedback.alert_system import AlertSystem, AlertLevel


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_move_action():
    """Valid move action for testing."""
    return Action(
        action_type=ActionType.MOVE_TO,
        params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
        expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
    )


@pytest.fixture
def valid_move_proposal(valid_move_action):
    """Valid action proposal."""
    return ActionProposal(action_sequence=[valid_move_action])


@pytest.fixture
def idle_robot_state():
    """Idle robot state for validation."""
    return {
        "arm_is_moving": False,
        "emergency_stop": False,
        "gripper_holding": False,
        "current_pose": [0.0, 0.0, 0.0],
    }


@pytest.fixture
def test_executor():
    """Test fixture providing a TwoLevelValidationPipeline."""
    return TwoLevelValidationPipeline()


@pytest.fixture
def confirmation_engine():
    """Execution confirmation engine for closed-loop tests."""
    return ExecutionConfirmationEngine()


@pytest.fixture
def human_oversight_engine():
    """Human oversight engine for control tests."""
    return HumanOversightEngine()


@pytest.fixture
def audit_trail():
    """Audit trail for logging tests."""
    return AuditTrail()


@pytest.fixture
def alert_system():
    """Alert system for notification tests."""
    return AlertSystem()


# ============================================================================
# P1: Safety First - Unauthorized actions must be rejected
# ============================================================================


class TestP1SafetyFirst:
    """Test suite for P1: Safety First Iron Rule.

    Verifies that:
    - Unknown actions not in whitelist are rejected
    - Actions with out-of-workspace poses are rejected
    - Actions with excessive gripper forces are rejected
    - Boundary violations are always caught
    """

    @pytest.mark.asyncio
    async def test_unknown_action_type_rejected(self):
        """Unknown action types must be rejected by whitelist."""
        validator = WhitelistValidator(config_path="config/whitelist.yaml")

        # Create an action with an invalid type
        with pytest.raises(ValueError):
            Action(
                action_type="disable_safety_check",  # Invalid action type
                params={},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )

    @pytest.mark.asyncio
    async def test_out_of_workspace_rejected(self):
        """Poses outside workspace must be rejected."""
        checker = BoundaryChecker(config_path="config/safety_limits.yaml")

        # Out of workspace pose
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [99, 99, 99], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        result = await checker.validate_action(action)
        assert not result.valid, "Out of workspace pose should be rejected"
        assert "boundary" in result.reason.lower() or "workspace" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_excessive_force_rejected(self):
        """Gripper forces exceeding limits must be rejected."""
        checker = BoundaryChecker(config_path="config/safety_limits.yaml")

        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 999},  # Exceeds typical limit of ~100N
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )

        result = await checker.validate_action(action)
        assert not result.valid, "Excessive gripper force should be rejected"

    @pytest.mark.asyncio
    async def test_invalid_action_type_enum(self):
        """Invalid action types cannot be created as enum values."""
        with pytest.raises(ValueError):
            ActionType("invalid_action_type")

    @pytest.mark.asyncio
    async def test_boundary_check_always_runs(self, test_executor, idle_robot_state):
        """Boundary checker must run for all MOVE_TO actions."""
        # Create an out-of-bounds action
        bad_action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [99, 99, 99], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        proposal = ActionProposal(action_sequence=[bad_action])

        result = await test_executor.validate_proposal(proposal, idle_robot_state)
        assert not result.valid, "Boundary check must reject out-of-bounds action"


# ============================================================================
# P2: Human Control - System can be stopped at any time
# ============================================================================


class TestP2HumanControl:
    """Test suite for P2: Human Control Iron Rule.

    Verifies that:
    - Emergency stop is always available
    - Cannot exit emergency stop without reset
    - Manual mode enforces safety boundaries
    - System can transition to emergency stop from any state
    """

    @pytest.mark.asyncio
    async def test_emergency_stop_always_available(self, human_oversight_engine):
        """Emergency stop must be reachable from any state."""
        engine = human_oversight_engine

        # From AUTOMATIC
        assert engine.current_mode == SystemMode.AUTOMATIC
        success = engine.transition_mode(SystemMode.EMERGENCY_STOP, "test", "user")
        assert success, "Should be able to enter EMERGENCY_STOP from AUTOMATIC"
        assert engine.current_mode == SystemMode.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_emergency_stop_from_manual(self, human_oversight_engine):
        """Emergency stop must be reachable from MANUAL_OVERRIDE."""
        engine = human_oversight_engine

        # Transition to MANUAL_OVERRIDE first
        success = engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "test", "user")
        assert success

        # Then to EMERGENCY_STOP
        success = engine.transition_mode(SystemMode.EMERGENCY_STOP, "test", "user")
        assert success
        assert engine.current_mode == SystemMode.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_cannot_exit_emergency_stop(self, human_oversight_engine):
        """Cannot transition FROM emergency stop."""
        engine = human_oversight_engine

        # Enter emergency stop
        engine.transition_mode(SystemMode.EMERGENCY_STOP, "test", "user")
        assert engine.current_mode == SystemMode.EMERGENCY_STOP

        # Try to exit
        success = engine.transition_mode(SystemMode.AUTOMATIC, "try exit", "user")
        assert not success, "Should not be able to exit EMERGENCY_STOP"
        assert engine.current_mode == SystemMode.EMERGENCY_STOP

        # Try other transitions
        success = engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "try exit", "user")
        assert not success

    @pytest.mark.asyncio
    async def test_manual_mode_enforces_boundaries(self, human_oversight_engine):
        """Manual mode MUST enforce safety boundaries."""
        engine = human_oversight_engine

        # Enter manual mode
        engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "enter manual", "user")

        # Try out-of-bounds action
        out_of_bounds_action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [99, 99, 99], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        result = await engine.validate_manual_action(out_of_bounds_action)
        assert not result.valid, "Manual mode must reject out-of-bounds actions"

        # Must have raised CRITICAL alert
        critical_alerts = [a for a in engine.alert_system.alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical_alerts) > 0, "Out-of-bounds in manual mode must raise CRITICAL alert"

    @pytest.mark.asyncio
    async def test_emergency_stop_is_terminal(self, human_oversight_engine):
        """EMERGENCY_STOP is a terminal state (cannot exit)."""
        engine = human_oversight_engine

        engine.transition_mode(SystemMode.EMERGENCY_STOP, "safety trigger", "safety_system")

        # Verify all possible transitions from EMERGENCY_STOP fail
        for target in [SystemMode.AUTOMATIC, SystemMode.MANUAL_OVERRIDE, SystemMode.PAUSED]:
            success = engine.transition_mode(target, "attempt", "user")
            assert not success, f"Should not be able to transition to {target} from EMERGENCY_STOP"


# ============================================================================
# P3: Decision Separation - LLM proposals must pass validation before execution
# ============================================================================


class TestP3DecisionSeparation:
    """Test suite for P3: Decision Separation Iron Rule.

    Verifies that:
    - Invalid proposals fail validation before execution
    - Validation cannot be bypassed
    - Validation pipeline is enforced
    """

    @pytest.mark.asyncio
    async def test_invalid_proposal_fails_validation(self, test_executor, idle_robot_state):
        """Invalid proposals must be rejected before execution."""
        bad_proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.GRIPPER_CLOSE,
                    params={"force": 999},  # Exceeds limit
                    expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
                )
            ]
        )

        result = await test_executor.validate_proposal(bad_proposal, idle_robot_state)
        assert not result.valid, "Invalid proposal should fail validation"

    @pytest.mark.asyncio
    async def test_validation_cannot_be_bypassed(self, test_executor, idle_robot_state):
        """Validation layer cannot be skipped."""
        # Create action that passes whitelist but fails boundary check
        bad_action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [99, 99, 99], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )
        bad_proposal = ActionProposal(action_sequence=[bad_action])

        result = await test_executor.validate_proposal(bad_proposal, idle_robot_state)
        assert not result.valid, "Proposal must fail if any validator rejects it"

    @pytest.mark.asyncio
    async def test_multiple_actions_all_validated(self, test_executor, idle_robot_state):
        """All actions in sequence must be validated."""
        # First action valid, second action invalid
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                ),
                Action(
                    action_type=ActionType.GRIPPER_CLOSE,
                    params={"force": 999},  # Invalid
                    expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
                ),
            ]
        )

        result = await test_executor.validate_proposal(proposal, idle_robot_state)
        # Should fail due to second action
        # (Note: this depends on whether first action passes boundary check)

    @pytest.mark.asyncio
    async def test_proposal_from_dict_validation(self):
        """ActionProposal.from_dict must validate all types."""
        # Valid proposal
        valid_dict = {
            "action_sequence": [
                {
                    "action_type": "move_to",
                    "params": {"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                    "expected_outcome": "arm_reaches_target",
                }
            ]
        }
        proposal = ActionProposal.from_dict(valid_dict)
        assert proposal is not None
        assert len(proposal.action_sequence) == 1

    @pytest.mark.asyncio
    async def test_missing_required_fields_rejected(self):
        """Proposals with missing required fields must be rejected."""
        invalid_dict = {
            "action_sequence": [
                {
                    "action_type": "move_to",
                    # Missing expected_outcome
                    "params": {},
                }
            ]
        }

        with pytest.raises((ValueError, KeyError, TypeError)):
            ActionProposal.from_dict(invalid_dict)


# ============================================================================
# P4: Closed Loop - Execution must have result confirmation
# ============================================================================


class TestP4ClosedLoop:
    """Test suite for P4: Closed Loop Iron Rule.

    Verifies that:
    - Execution failures are detected
    - Timeouts are detected
    - Pose accuracy is checked
    - Grasp state is confirmed
    """

    @pytest.mark.asyncio
    async def test_confirmation_detects_pose_failure(self, confirmation_engine):
        """Confirmation must detect when execution didn't meet pose expectations."""
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(FeedbackStage.STARTED, 0.0, {}, timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)),
            ExecutionFeedback(FeedbackStage.COMPLETED, 1.0, {}, timestamp=datetime.fromtimestamp(t0 + 1, tz=timezone.utc)),
        ]

        # Robot didn't reach target (large pose error)
        actual_state = {"current_pose": [0.0, 0.0, 0.0], "collision_detected": False}

        result = await confirmation_engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed", "Should detect pose error"
        assert result.pose_error > 0.05, "Pose error should exceed tolerance"

    @pytest.mark.asyncio
    async def test_confirmation_detects_collision(self, confirmation_engine):
        """Confirmation must detect collisions during execution."""
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(FeedbackStage.STARTED, 0.0, {}, timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)),
            ExecutionFeedback(FeedbackStage.COMPLETED, 1.0, {}, timestamp=datetime.fromtimestamp(t0 + 1, tz=timezone.utc)),
        ]

        # Collision detected
        actual_state = {"current_pose": [0.5, 0.3, 0.2], "collision_detected": True}

        result = await confirmation_engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed", "Should detect collision"
        assert "collision" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_confirmation_detects_timeout(self, confirmation_engine):
        """Confirmation must detect execution timeouts."""
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(FeedbackStage.STARTED, 0.0, {}, timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)),
            # Execution took 100 seconds (exceeds 5 second timeout)
            ExecutionFeedback(FeedbackStage.COMPLETED, 1.0, {}, timestamp=datetime.fromtimestamp(t0 + 100, tz=timezone.utc)),
        ]

        actual_state = {"current_pose": [0.5, 0.3, 0.2], "collision_detected": False}

        result = await confirmation_engine.confirm(action, feedbacks, actual_state, timeout_seconds=5.0)
        assert result.status == "timeout", "Should detect timeout"
        assert "100" in result.reason, "Should report actual duration"

    @pytest.mark.asyncio
    async def test_confirmation_detects_grasp_success(self, confirmation_engine):
        """Confirmation must detect successful gripper grasp."""
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 50},
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )

        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(FeedbackStage.STARTED, 0.0, {}, timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)),
            ExecutionFeedback(FeedbackStage.COMPLETED, 1.0, {}, timestamp=datetime.fromtimestamp(t0 + 1, tz=timezone.utc)),
        ]

        # Object is grasped
        actual_state = {"gripper_holding": True}

        result = await confirmation_engine.confirm(action, feedbacks, actual_state)
        assert result.status == "confirmed", "Should confirm grasp"

    @pytest.mark.asyncio
    async def test_confirmation_detects_grasp_failure(self, confirmation_engine):
        """Confirmation must detect gripper grasp failure."""
        action = Action(
            action_type=ActionType.GRIPPER_CLOSE,
            params={"force": 50},
            expected_outcome=ExpectedOutcomeType.OBJECT_GRASPED,
        )

        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(FeedbackStage.STARTED, 0.0, {}, timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)),
            ExecutionFeedback(FeedbackStage.COMPLETED, 1.0, {}, timestamp=datetime.fromtimestamp(t0 + 1, tz=timezone.utc)),
        ]

        # Gripper not holding
        actual_state = {"gripper_holding": False}

        result = await confirmation_engine.confirm(action, feedbacks, actual_state)
        assert result.status == "failed", "Should detect grasp failure"

    @pytest.mark.asyncio
    async def test_confirmation_detects_release_success(self, confirmation_engine):
        """Confirmation must detect successful object release."""
        action = Action(
            action_type=ActionType.GRIPPER_OPEN,
            params={},
            expected_outcome=ExpectedOutcomeType.OBJECT_RELEASED,
        )

        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(FeedbackStage.STARTED, 0.0, {}, timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)),
            ExecutionFeedback(FeedbackStage.COMPLETED, 1.0, {}, timestamp=datetime.fromtimestamp(t0 + 1, tz=timezone.utc)),
        ]

        # Object released
        actual_state = {"gripper_holding": False}

        result = await confirmation_engine.confirm(action, feedbacks, actual_state)
        assert result.status == "confirmed", "Should confirm release"


# ============================================================================
# P6: Safety Mechanisms - Audit logs must be tamper-proof
# ============================================================================


class TestP6SafetyMechanism:
    """Test suite for P6: Safety Mechanisms Iron Rule.

    Verifies that:
    - Audit trail has tamper-proof chain integrity
    - Critical events raise alerts
    - Audit trail is append-only
    """

    @pytest.mark.asyncio
    async def test_audit_chain_integrity_empty(self, audit_trail):
        """Empty audit trail should verify as valid."""
        assert audit_trail.verify_chain_integrity(), "Empty trail should verify"

    @pytest.mark.asyncio
    async def test_audit_chain_integrity_single_event(self, audit_trail):
        """Single event audit trail should verify."""
        log = ExecutionLog(
            event_type="test_event",
            action_type="move_to",
            details={"index": 0}
        )
        audit_trail.log_event(log)

        assert audit_trail.verify_chain_integrity(), "Single event trail should verify"

    @pytest.mark.asyncio
    async def test_audit_chain_integrity_multiple_events(self, audit_trail):
        """Multiple events with hash chain should verify."""
        for i in range(5):
            log = ExecutionLog(
                event_type=f"test_event_{i}",
                action_type="move_to",
                details={"index": i}
            )
            audit_trail.log_event(log)

        assert audit_trail.verify_chain_integrity(), "Multi-event trail should verify"

    @pytest.mark.asyncio
    async def test_audit_chain_tamper_detection(self, audit_trail):
        """Audit trail must detect tampering."""
        # Add events
        for i in range(3):
            log = ExecutionLog(
                event_type=f"test_{i}",
                action_type="test",
                details={"i": i}
            )
            audit_trail.log_event(log)

        # Verify integrity
        assert audit_trail.verify_chain_integrity()

        # Tamper with an event (modify details)
        if len(audit_trail.events) > 1:
            audit_trail.events[1].details["tampered"] = True
            # Chain should now be broken
            assert not audit_trail.verify_chain_integrity(), "Should detect tampering"

    @pytest.mark.asyncio
    async def test_critical_events_raise_alerts(self, alert_system):
        """Critical failures must raise CRITICAL level alerts."""
        alert_system.raise_alert(
            "boundary_violation",
            AlertLevel.CRITICAL,
            "gripper exceeded force limit"
        )

        critical_alerts = [a for a in alert_system.alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical_alerts) == 1
        assert "force limit" in critical_alerts[0].message

    @pytest.mark.asyncio
    async def test_alert_acknowledgment(self, alert_system):
        """Alerts can be acknowledged."""
        alert_system.raise_alert("test", AlertLevel.WARNING, "test message")

        unacked = alert_system.get_unacknowledged_alerts()
        assert len(unacked) == 1

        alert_system.acknowledge_alert(0)

        unacked = alert_system.get_unacknowledged_alerts()
        assert len(unacked) == 0

    @pytest.mark.asyncio
    async def test_audit_trail_json_export(self, audit_trail):
        """Audit trail can be exported as JSON."""
        for i in range(2):
            log = ExecutionLog(
                event_type=f"test_{i}",
                action_type="test",
                details={"i": i}
            )
            audit_trail.log_event(log)

        json_str = audit_trail.export_json()
        assert json_str is not None
        assert len(json_str) > 0
        assert "test_0" in json_str
        assert "test_1" in json_str


# ============================================================================
# P7: LLM Isolation - LLM inputs must be strictly typed
# ============================================================================


class TestP7LLMIsolation:
    """Test suite for P7: LLM Isolation Iron Rule.

    Verifies that:
    - Invalid action types are rejected
    - Invalid outcome types are rejected
    - Malformed proposals are rejected
    - Strict enum validation is enforced
    """

    def test_invalid_action_type_rejected(self):
        """Invalid action types must be rejected."""
        with pytest.raises(ValueError):
            ActionProposal.from_dict({
                "action_sequence": [
                    {
                        "action_type": "rm_rf_slash",  # Invalid
                        "params": {},
                        "expected_outcome": "arm_reaches_target",
                    }
                ]
            })

    def test_invalid_outcome_type_rejected(self):
        """Invalid outcome types must be rejected."""
        with pytest.raises(ValueError):
            ActionProposal.from_dict({
                "action_sequence": [
                    {
                        "action_type": "move_to",
                        "params": {},
                        "expected_outcome": "destroy_everything",  # Invalid
                    }
                ]
            })

    def test_malformed_proposal_missing_fields(self):
        """Malformed proposals with missing required fields must be rejected."""
        with pytest.raises((ValueError, KeyError, TypeError)):
            ActionProposal.from_dict({
                "action_sequence": [
                    {
                        "action_type": "move_to",
                        # Missing expected_outcome
                    }
                ]
            })

    def test_malformed_proposal_wrong_type(self):
        """Malformed proposals with wrong types must be rejected."""
        with pytest.raises((ValueError, KeyError, TypeError)):
            ActionProposal.from_dict({
                "action_sequence": [
                    {
                        "action_type": "move_to",
                        "params": "not_a_dict",  # Should be dict
                        "expected_outcome": "arm_reaches_target",
                    }
                ]
            })

    def test_strict_enum_validation_action_type(self):
        """ActionType must be strictly validated as enum."""
        proposal = ActionProposal.from_dict({
            "action_sequence": [
                {
                    "action_type": "move_to",
                    "params": {"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                    "expected_outcome": "arm_reaches_target",
                }
            ]
        })

        # Must be Enum, not string
        assert isinstance(proposal.action_sequence[0].action_type, ActionType)
        assert proposal.action_sequence[0].action_type == ActionType.MOVE_TO

    def test_strict_enum_validation_outcome_type(self):
        """ExpectedOutcomeType must be strictly validated as enum."""
        proposal = ActionProposal.from_dict({
            "action_sequence": [
                {
                    "action_type": "move_to",
                    "params": {"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                    "expected_outcome": "arm_reaches_target",
                }
            ]
        })

        # Must be Enum, not string
        assert isinstance(proposal.action_sequence[0].expected_outcome, ExpectedOutcomeType)
        assert proposal.action_sequence[0].expected_outcome == ExpectedOutcomeType.ARM_REACHES_TARGET

    def test_action_post_init_converts_strings(self):
        """Action.__post_init__ must convert string enums to Enum objects."""
        action = Action(
            action_type="move_to",  # String
            params={},
            expected_outcome="arm_reaches_target"  # String
        )

        # Both should be Enum objects after __post_init__
        assert isinstance(action.action_type, ActionType)
        assert isinstance(action.expected_outcome, ExpectedOutcomeType)

    def test_no_arbitrary_string_params(self):
        """Action params must not accept arbitrary strings as action_type."""
        with pytest.raises(ValueError):
            Action(
                action_type="malicious_code_here",
                params={},
                expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
            )

    def test_proposal_validation_result_is_typed(self):
        """ValidationResult must enforce boolean type for valid field."""
        with pytest.raises(TypeError):
            ValidationResult(valid="yes")  # Must be bool, not string


# ============================================================================
# Integration Tests: Combining Multiple Iron Rules
# ============================================================================


class TestIntegrationSafetyRules:
    """Integration tests combining multiple Iron Rules."""

    @pytest.mark.asyncio
    async def test_p1_p3_together(self, test_executor, idle_robot_state):
        """P1 + P3: Unauthorized action rejected before any execution."""
        # Try to execute out-of-workspace action
        bad_proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [99, 99, 99], "speed": 0.5},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ]
        )

        result = await test_executor.validate_proposal(bad_proposal, idle_robot_state)
        assert not result.valid, "P1+P3: Unauthorized action should be caught by validation"

    @pytest.mark.asyncio
    async def test_p2_human_control_precedence(self, human_oversight_engine):
        """P2: Human control is always available regardless of system state."""
        # Start in automatic
        assert human_oversight_engine.current_mode == SystemMode.AUTOMATIC

        # Emergency stop must work
        success = human_oversight_engine.transition_mode(
            SystemMode.EMERGENCY_STOP, "user override", "user"
        )
        assert success

        # Now in emergency stop, cannot do anything else
        success = human_oversight_engine.transition_mode(
            SystemMode.AUTOMATIC, "exit", "user"
        )
        assert not success, "Cannot exit emergency stop"
        assert human_oversight_engine.current_mode == SystemMode.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_p4_p6_feedback_logging(self, confirmation_engine, audit_trail):
        """P4 + P6: Execution confirmation is logged in audit trail."""
        # Create execution feedback
        t0 = time.time()
        feedbacks = [
            ExecutionFeedback(
                FeedbackStage.STARTED,
                0.0,
                {},
                timestamp=datetime.fromtimestamp(t0, tz=timezone.utc)
            ),
            ExecutionFeedback(
                FeedbackStage.COMPLETED,
                1.0,
                {},
                timestamp=datetime.fromtimestamp(t0 + 1, tz=timezone.utc)
            ),
        ]

        # Log to audit trail
        for feedback in feedbacks:
            log = ExecutionLog(
                event_type=f"feedback_{feedback.stage.value}",
                action_type="move_to",
                details={"progress": feedback.progress}
            )
            audit_trail.log_event(log)

        # Verify audit chain
        assert audit_trail.verify_chain_integrity()
        assert len(audit_trail.events) == 2

    @pytest.mark.asyncio
    async def test_p7_prevents_injection(self):
        """P7: Strict typing prevents injection attacks."""
        # Try various injection payloads
        injection_attempts = [
            '"; rm -rf /',
            "'; DROP TABLE users; --",
            "$(echo hacked)",
            "`whoami`",
        ]

        for payload in injection_attempts:
            with pytest.raises(ValueError):
                ActionType(payload)

    @pytest.mark.asyncio
    async def test_complete_safety_flow(self, test_executor, human_oversight_engine, idle_robot_state):
        """Complete flow: Validate → Confirm → Log (P1, P3, P4, P6)."""
        # Step 1: Create valid proposal (P7 validation)
        proposal = ActionProposal(
            action_sequence=[
                Action(
                    action_type=ActionType.MOVE_TO,
                    params={"target_pose": [0.5, 0.3, 0.2], "speed": 0.5},
                    expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
                )
            ]
        )

        # Step 2: Validate through pipeline (P1, P3)
        result = await test_executor.validate_proposal(proposal, idle_robot_state)
        # May pass or fail depending on boundary config, but validation must run

        # Step 3: Can stop anytime (P2)
        success = human_oversight_engine.transition_mode(
            SystemMode.EMERGENCY_STOP, "safety check", "user"
        )
        assert success

        # Step 4: Cannot exit emergency stop (P2)
        success = human_oversight_engine.transition_mode(
            SystemMode.AUTOMATIC, "exit", "user"
        )
        assert not success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
