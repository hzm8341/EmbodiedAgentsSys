"""Human oversight engine with state machine and takeover capability."""

from typing import List

from agents.human_oversight.system_mode import SystemMode, ModeTransition
from agents.policy.action_proposal import Action, ValidationResult
from agents.policy.validators.boundary import BoundaryChecker
from agents.feedback.audit_trail import AuditTrail, ExecutionLog
from agents.feedback.alert_system import AlertSystem, AlertLevel


class HumanOversightEngine:
    """Manages system operational modes and human takeover.

    Implements a finite state machine with four states:
    - AUTOMATIC: System operates autonomously
    - MANUAL_OVERRIDE: Human has direct control (with boundary enforcement)
    - PAUSED: System is paused
    - EMERGENCY_STOP: System is in emergency stop (terminal state)

    Transitions follow specific rules:
    - Can transition TO EMERGENCY_STOP from any state
    - Cannot transition FROM EMERGENCY_STOP except via external reset
    """

    def __init__(self):
        """Initialize the oversight engine."""
        self.current_mode = SystemMode.AUTOMATIC
        self.transitions: List[ModeTransition] = []
        self.audit_trail = AuditTrail()
        self.alert_system = AlertSystem()
        self.boundary_checker = BoundaryChecker()
        self.manual_override_action: Action = None

    def transition_mode(
        self,
        target_mode: SystemMode,
        reason: str,
        triggered_by: str = "user"
    ) -> bool:
        """Attempt to transition to a new mode.

        Args:
            target_mode: The SystemMode to transition to
            reason: Human-readable reason for the transition
            triggered_by: Who triggered the transition ("user", "safety_system", "timeout")

        Returns:
            True if transition was successful, False otherwise
        """
        # Validate transition
        if not self._is_valid_transition(self.current_mode, target_mode):
            return False

        transition = ModeTransition(
            from_mode=self.current_mode,
            to_mode=target_mode,
            reason=reason,
            triggered_by=triggered_by
        )
        self.transitions.append(transition)

        # Log to audit trail
        self.audit_trail.log_event(ExecutionLog(
            event_type="mode_transition",
            action_type=target_mode.value,
            details={
                "from": self.current_mode.value,
                "to": target_mode.value,
                "reason": reason,
                "triggered_by": triggered_by
            }
        ))

        self.current_mode = target_mode
        return True

    def _is_valid_transition(self, from_mode: SystemMode, to_mode: SystemMode) -> bool:
        """Check if a mode transition is valid.

        Args:
            from_mode: Current SystemMode
            to_mode: Target SystemMode

        Returns:
            True if transition is allowed, False otherwise
        """
        # EMERGENCY_STOP can be reached from any state
        if to_mode == SystemMode.EMERGENCY_STOP:
            return True
        # Can't transition FROM emergency stop except via external reset
        if from_mode == SystemMode.EMERGENCY_STOP:
            return False
        return True

    async def validate_manual_action(self, action: Action) -> ValidationResult:
        """Validate action in MANUAL_OVERRIDE mode with mandatory boundary checking.

        In manual mode, boundary violations are treated as CRITICAL alerts.

        Args:
            action: The Action to validate

        Returns:
            ValidationResult from boundary checker
        """
        # Mandatory boundary checking in manual mode
        result = await self.boundary_checker.validate_action(action)

        if not result.valid:
            # Boundary violation in manual mode = CRITICAL alert
            self.alert_system.raise_alert(
                "manual_boundary_violation",
                AlertLevel.CRITICAL,
                f"Manual action violates boundary: {result.reason}"
            )

        return result

    def get_current_mode(self) -> SystemMode:
        """Get current operational mode.

        Returns:
            Current SystemMode
        """
        return self.current_mode

    def is_automatic(self) -> bool:
        """Check if system is in automatic mode.

        Returns:
            True if current mode is AUTOMATIC, False otherwise
        """
        return self.current_mode == SystemMode.AUTOMATIC

    def is_manual(self) -> bool:
        """Check if system is in manual override mode.

        Returns:
            True if current mode is MANUAL_OVERRIDE, False otherwise
        """
        return self.current_mode == SystemMode.MANUAL_OVERRIDE

    def is_emergency_stopped(self) -> bool:
        """Check if system is in emergency stop state.

        Returns:
            True if current mode is EMERGENCY_STOP, False otherwise
        """
        return self.current_mode == SystemMode.EMERGENCY_STOP
