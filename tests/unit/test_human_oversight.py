"""Unit tests for human oversight engine and state machine."""

import pytest


class TestSystemMode:
    """Test SystemMode enum and ModeTransition dataclass."""

    def test_system_mode_enum_values(self):
        """Test that SystemMode has all required modes."""
        from agents.human_oversight.system_mode import SystemMode

        assert SystemMode.AUTOMATIC.value == "automatic"
        assert SystemMode.MANUAL_OVERRIDE.value == "manual_override"
        assert SystemMode.PAUSED.value == "paused"
        assert SystemMode.EMERGENCY_STOP.value == "emergency_stop"

    def test_mode_transition_creation(self):
        """Test creating a ModeTransition record."""
        from agents.human_oversight.system_mode import SystemMode, ModeTransition

        transition = ModeTransition(
            from_mode=SystemMode.AUTOMATIC,
            to_mode=SystemMode.MANUAL_OVERRIDE,
            reason="operator requested manual control",
            triggered_by="user"
        )

        assert transition.from_mode == SystemMode.AUTOMATIC
        assert transition.to_mode == SystemMode.MANUAL_OVERRIDE
        assert transition.reason == "operator requested manual control"
        assert transition.triggered_by == "user"
        assert transition.timestamp is not None


class TestHumanOversightEngine:
    """Test HumanOversightEngine state machine and validation."""

    def test_initial_mode_is_automatic(self):
        """Test that engine starts in AUTOMATIC mode."""
        from agents.human_oversight.engine import HumanOversightEngine

        engine = HumanOversightEngine()
        assert engine.current_mode.value == "automatic"
        assert engine.is_automatic()

    def test_automatic_to_manual_transition(self):
        """Test transitioning from AUTOMATIC to MANUAL_OVERRIDE."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        success = engine.transition_mode(
            SystemMode.MANUAL_OVERRIDE,
            "operator requested manual control"
        )

        assert success
        assert engine.current_mode == SystemMode.MANUAL_OVERRIDE
        assert engine.is_manual()
        assert len(engine.transitions) == 1

    def test_manual_to_automatic_transition(self):
        """Test transitioning from MANUAL_OVERRIDE back to AUTOMATIC."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "manual control")
        success = engine.transition_mode(
            SystemMode.AUTOMATIC,
            "returning to automatic mode"
        )

        assert success
        assert engine.current_mode == SystemMode.AUTOMATIC
        assert len(engine.transitions) == 2

    def test_automatic_to_paused_transition(self):
        """Test transitioning to PAUSED mode."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        success = engine.transition_mode(
            SystemMode.PAUSED,
            "system paused by operator"
        )

        assert success
        assert engine.current_mode == SystemMode.PAUSED

    def test_emergency_stop_from_any_mode(self):
        """Test that EMERGENCY_STOP can be reached from any mode."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        for start_mode in [
            SystemMode.AUTOMATIC,
            SystemMode.MANUAL_OVERRIDE,
            SystemMode.PAUSED
        ]:
            engine = HumanOversightEngine()
            engine.current_mode = start_mode

            success = engine.transition_mode(
                SystemMode.EMERGENCY_STOP,
                "safety system triggered"
            )

            assert success, f"Should be able to reach EMERGENCY_STOP from {start_mode}"
            assert engine.current_mode == SystemMode.EMERGENCY_STOP

    def test_cannot_transition_from_emergency_stop(self):
        """Test that we cannot transition FROM EMERGENCY_STOP."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        engine.current_mode = SystemMode.EMERGENCY_STOP

        # Try to transition to any mode
        for target_mode in [
            SystemMode.AUTOMATIC,
            SystemMode.MANUAL_OVERRIDE,
            SystemMode.PAUSED
        ]:
            success = engine.transition_mode(
                target_mode,
                "trying to recover from emergency stop"
            )
            assert not success, f"Should not be able to leave EMERGENCY_STOP to {target_mode}"
            assert engine.current_mode == SystemMode.EMERGENCY_STOP

    def test_transition_audit_trail(self):
        """Test that transitions are logged in audit trail."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "manual control")

        # Check audit trail has the transition logged
        assert len(engine.audit_trail.events) == 1
        event = engine.audit_trail.events[0]
        assert event.event_type == "mode_transition"
        assert event.action_type == "manual_override"
        assert event.details["from"] == "automatic"
        assert event.details["to"] == "manual_override"

    def test_multiple_transitions_recorded(self):
        """Test that multiple transitions are all recorded."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "to manual")
        engine.transition_mode(SystemMode.PAUSED, "to paused")
        engine.transition_mode(SystemMode.AUTOMATIC, "to automatic")

        assert len(engine.transitions) == 3
        assert engine.transitions[0].from_mode == SystemMode.AUTOMATIC
        assert engine.transitions[0].to_mode == SystemMode.MANUAL_OVERRIDE
        assert engine.transitions[1].from_mode == SystemMode.MANUAL_OVERRIDE
        assert engine.transitions[1].to_mode == SystemMode.PAUSED
        assert engine.transitions[2].from_mode == SystemMode.PAUSED
        assert engine.transitions[2].to_mode == SystemMode.AUTOMATIC

    @pytest.mark.asyncio
    async def test_manual_action_boundary_validation_valid(self):
        """Test manual action validation when action is within boundaries."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode
        from agents.policy.action_proposal import Action, ActionType, ExpectedOutcomeType

        engine = HumanOversightEngine()

        # Valid action within workspace
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [0.5, 0.5, 0.5], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        result = await engine.validate_manual_action(action)
        # Should be valid (within default workspace bounds)
        assert result.valid

    @pytest.mark.asyncio
    async def test_manual_action_boundary_violation_raises_alert(self):
        """Test that boundary violation in manual mode raises CRITICAL alert."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode
        from agents.policy.action_proposal import Action, ActionType, ExpectedOutcomeType
        from agents.feedback.alert_system import AlertLevel

        engine = HumanOversightEngine()

        # Out of workspace action
        action = Action(
            action_type=ActionType.MOVE_TO,
            params={"target_pose": [99, 99, 99], "speed": 0.5},
            expected_outcome=ExpectedOutcomeType.ARM_REACHES_TARGET,
        )

        result = await engine.validate_manual_action(action)
        assert result.valid is False

        # Check that CRITICAL alert was raised
        assert len(engine.alert_system.alerts) == 1
        alert = engine.alert_system.alerts[0]
        assert alert.level == AlertLevel.CRITICAL
        assert "boundary" in alert.message.lower()

    def test_triggered_by_tracking(self):
        """Test that triggered_by is tracked in transitions."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()

        # Transition triggered by safety system
        engine.transition_mode(
            SystemMode.EMERGENCY_STOP,
            "safety limit exceeded",
            triggered_by="safety_system"
        )

        transition = engine.transitions[0]
        assert transition.triggered_by == "safety_system"

    def test_emergency_stop_triggered_by_safety(self):
        """Test emergency stop transition triggered by safety system."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()
        success = engine.transition_mode(
            SystemMode.EMERGENCY_STOP,
            "gripper force limit exceeded",
            triggered_by="safety_system"
        )

        assert success
        assert engine.is_emergency_stopped()
        assert engine.transitions[0].triggered_by == "safety_system"

    def test_get_current_mode_matches_state(self):
        """Test that get_current_mode always reflects actual state."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()

        assert engine.get_current_mode() == SystemMode.AUTOMATIC
        engine.transition_mode(SystemMode.MANUAL_OVERRIDE, "test")
        assert engine.get_current_mode() == SystemMode.MANUAL_OVERRIDE
        engine.transition_mode(SystemMode.AUTOMATIC, "test")
        assert engine.get_current_mode() == SystemMode.AUTOMATIC

    def test_mode_check_functions(self):
        """Test mode checking functions (is_automatic, is_manual, is_emergency_stopped)."""
        from agents.human_oversight.engine import HumanOversightEngine
        from agents.human_oversight.system_mode import SystemMode

        engine = HumanOversightEngine()

        # Test AUTOMATIC
        assert engine.is_automatic()
        assert not engine.is_manual()
        assert not engine.is_emergency_stopped()

        # Test MANUAL_OVERRIDE
        engine.current_mode = SystemMode.MANUAL_OVERRIDE
        assert not engine.is_automatic()
        assert engine.is_manual()
        assert not engine.is_emergency_stopped()

        # Test EMERGENCY_STOP
        engine.current_mode = SystemMode.EMERGENCY_STOP
        assert not engine.is_automatic()
        assert not engine.is_manual()
        assert engine.is_emergency_stopped()
