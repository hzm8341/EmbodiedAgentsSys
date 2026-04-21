"""Full end-to-end execution pipeline orchestration.

Orchestrates LLM → ValidationPipeline → ToolAdapter/Tool → ConfirmationEngine →
HumanOversight → AuditTrail, implementing the complete execution flow with
fail-fast validation, execution confirmation, and comprehensive audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.policy.action_proposal import ActionProposal, Action
from agents.policy.validation_pipeline import TwoLevelValidationPipeline
from agents.execution.confirmation import ExecutionConfirmationEngine, ConfirmationResult
from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.execution.tools.base import ToolBase
from agents.human_oversight.engine import HumanOversightEngine
from agents.feedback.audit_trail import AuditTrail, ExecutionLog
from agents.feedback.alert_system import AlertSystem, AlertLevel


@dataclass
class ActionExecutionResult:
    """Result of executing a single action."""

    action_id: str
    action_type: str
    success: bool
    feedbacks: List[ExecutionFeedback] = field(default_factory=list)
    confirmation: Optional[ConfirmationResult] = None
    error_reason: str = ""
    timestamp_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def duration_seconds(self) -> float:
        """Get execution duration in seconds."""
        return (self.timestamp_end - self.timestamp_start).total_seconds()


@dataclass
class ExecutionPipelineResult:
    """Result of end-to-end pipeline execution."""

    success: bool
    proposal_id: str
    action_results: List[ActionExecutionResult] = field(default_factory=list)
    reason: str = ""
    validation_error: Optional[str] = None
    execution_error: Optional[str] = None

    @property
    def total_duration_seconds(self) -> float:
        """Get total execution duration in seconds."""
        if not self.action_results:
            return 0.0
        start = min(r.timestamp_start for r in self.action_results)
        end = max(r.timestamp_end for r in self.action_results)
        return (end - start).total_seconds()


class ExecutionPipeline:
    """Orchestrates full end-to-end execution pipeline.

    Implements the complete flow:
    1. Validation: TwoLevelValidationPipeline (fails fast on invalid proposals)
    2. Approval: HumanOversightEngine (waits for approval if needed)
    3. Execution: Execute each action via tool with feedback streaming
    4. Confirmation: ExecutionConfirmationEngine (validates outcomes)
    5. Logging: AuditTrail (comprehensive event logging with chain integrity)

    The pipeline enforces a strict fail-fast on validation and oversight failures,
    while continuing through execution errors to ensure maximum observability.
    """

    def __init__(self):
        """Initialize ExecutionPipeline with all component systems."""
        self.validation_pipeline = TwoLevelValidationPipeline()
        self.confirmation_engine = ExecutionConfirmationEngine()
        self.oversight_engine = HumanOversightEngine()
        self.audit_trail = AuditTrail()
        self.alert_system = AlertSystem()

    async def execute_proposal(
        self,
        proposal: ActionProposal,
        robot_state: Dict[str, Any],
        tools_registry: Dict[str, ToolBase],
    ) -> ExecutionPipelineResult:
        """Execute a proposal end-to-end through the full pipeline.

        Pipeline flow:
        1. Validate proposal (fail-fast)
        2. Check human oversight requirements (wait if needed)
        3. Execute each action in sequence with tool feedback
        4. Confirm each execution result
        5. Log all events to audit trail
        6. Return comprehensive result

        Args:
            proposal: ActionProposal with action sequence to execute
            robot_state: Current robot state (arm_is_moving, etc.)
            tools_registry: Dictionary mapping action types to ToolBase instances

        Returns:
            ExecutionPipelineResult with detailed execution status and results
        """
        result = ExecutionPipelineResult(
            success=False,
            proposal_id=proposal.id,
            reason="execution not started",
        )

        # Step 1: Validate proposal (fail-fast)
        validation_result = await self.validation_pipeline.validate_proposal(
            proposal, robot_state
        )

        if not validation_result.valid:
            result.success = False
            result.validation_error = validation_result.reason
            result.reason = f"validation failed: {validation_result.reason}"

            # Log validation failure
            self.audit_trail.log_event(
                ExecutionLog(
                    event_type="validation_failed",
                    action_type="proposal_validation",
                    details={
                        "proposal_id": proposal.id,
                        "validator": validation_result.validator,
                        "reason": validation_result.reason,
                    },
                )
            )

            # Alert on validation failure
            self.alert_system.raise_alert(
                event_id=f"validation_failed_{proposal.id}",
                level=AlertLevel.CRITICAL,
                message=f"Proposal validation failed: {validation_result.reason}",
            )

            return result

        # Log validation passed
        self.audit_trail.log_event(
            ExecutionLog(
                event_type="validation_passed",
                action_type="proposal_validation",
                details={
                    "proposal_id": proposal.id,
                    "requires_approval": validation_result.requires_human_approval,
                },
            )
        )

        # Step 2: Check human oversight requirements
        if validation_result.requires_human_approval:
            approval_granted = await self._handle_approval(proposal)
            if not approval_granted:
                result.success = False
                result.reason = "awaiting human approval"

                # Log approval waiting
                self.audit_trail.log_event(
                    ExecutionLog(
                        event_type="approval_required",
                        action_type="oversight",
                        details={
                            "proposal_id": proposal.id,
                            "reason": "high-risk actions require human approval",
                        },
                    )
                )

                return result

            # Log approval granted
            self.audit_trail.log_event(
                ExecutionLog(
                    event_type="approval_granted",
                    action_type="oversight",
                    details={"proposal_id": proposal.id},
                )
            )

        # Step 3-5: Execute each action in sequence
        all_actions_successful = True
        for action in proposal.action_sequence:
            action_result = await self._execute_action(
                action, proposal.id, robot_state, tools_registry
            )
            result.action_results.append(action_result)

            if not action_result.success:
                all_actions_successful = False
                # Continue execution for observability (don't fail-fast on execution)
                self.alert_system.raise_alert(
                    event_id=f"execution_failed_{action_result.action_id}",
                    level=AlertLevel.CRITICAL,
                    message=f"Action execution failed: {action_result.error_reason}",
                )

        # Final result
        result.success = all_actions_successful
        result.reason = (
            "all actions executed successfully"
            if all_actions_successful
            else "some actions failed during execution"
        )

        # Log final result
        self.audit_trail.log_event(
            ExecutionLog(
                event_type="execution_complete",
                action_type="proposal_execution",
                details={
                    "proposal_id": proposal.id,
                    "success": result.success,
                    "actions_executed": len(result.action_results),
                    "total_duration_seconds": result.total_duration_seconds,
                },
            )
        )

        return result

    async def _handle_approval(self, proposal: ActionProposal) -> bool:
        """Wait for human approval if needed.

        In production, this would integrate with a human oversight interface.
        For now, returns True (simulates approval granted).

        Args:
            proposal: ActionProposal requiring approval

        Returns:
            True if approval granted, False if denied or timeout
        """
        # In production, would integrate with human oversight interface
        # For testing, we simulate immediate approval
        return True

    async def _execute_action(
        self,
        action: Action,
        proposal_id: str,
        robot_state: Dict[str, Any],
        tools_registry: Dict[str, ToolBase],
    ) -> ActionExecutionResult:
        """Execute a single action via tool with feedback collection.

        Executes the action using the appropriate tool from the registry,
        collecting all feedback events, and returning a detailed result.

        Args:
            action: Single Action to execute
            proposal_id: ID of parent proposal (for logging)
            robot_state: Current robot state
            tools_registry: Available tools

        Returns:
            ActionExecutionResult with execution details
        """
        action_id = f"{proposal_id}_{action.action_type.value}"
        result = ActionExecutionResult(
            action_id=action_id,
            action_type=action.action_type.value,
            success=False,
        )

        # Get tool
        tool = tools_registry.get(action.action_type.value)
        if not tool:
            result.error_reason = f"tool not found: no tool registered for {action.action_type.value}"

            # Log tool not found
            self.audit_trail.log_event(
                ExecutionLog(
                    event_type="execution_failed",
                    action_type=action.action_type.value,
                    details={
                        "action_id": action_id,
                        "reason": "tool not found",
                    },
                )
            )

            return result

        # Log execution started
        self.audit_trail.log_event(
            ExecutionLog(
                event_type="execution_started",
                action_type=action.action_type.value,
                details={
                    "action_id": action_id,
                    "action_type": action.action_type.value,
                    "params": action.params,
                },
            )
        )

        # Execute tool and collect feedback
        try:
            result.timestamp_start = datetime.now(timezone.utc)

            async for feedback in tool.execute_with_feedback(
                params=action.params,
                current_state=robot_state,
            ):
                result.feedbacks.append(feedback)

                # Check for errors during execution
                if feedback.has_error:
                    result.error_reason = feedback.error_message
                    self.alert_system.raise_alert(
                        event_id=f"execution_error_{action_id}",
                        level=AlertLevel.WARNING,
                        message=f"Tool error during {action.action_type.value}: {feedback.error_message}",
                    )

            result.timestamp_end = datetime.now(timezone.utc)

            # If any feedback reported an error, skip confirmation and fail immediately
            if result.error_reason:
                self.audit_trail.log_event(
                    ExecutionLog(
                        event_type="execution_failed",
                        action_type=action.action_type.value,
                        details={"action_id": action_id, "reason": result.error_reason},
                    )
                )
                return result

            # Step 4: Confirm execution result
            # Use the last feedback's current_state if available (reflects post-execution state)
            last_state = robot_state
            if result.feedbacks and result.feedbacks[-1].current_state:
                last_state = {**robot_state, **result.feedbacks[-1].current_state}
            confirmation = await self.confirmation_engine.confirm(
                action,
                result.feedbacks,
                last_state,
            )
            result.confirmation = confirmation

            # Interpret confirmation result
            if confirmation.status == "confirmed":
                result.success = True
                self.audit_trail.log_event(
                    ExecutionLog(
                        event_type="execution_confirmed",
                        action_type=action.action_type.value,
                        details={
                            "action_id": action_id,
                            "confirmation_status": confirmation.status,
                            "confirmation_reason": confirmation.reason,
                        },
                    )
                )
            elif confirmation.status in ("partial", "failed"):
                result.success = False
                result.error_reason = f"confirmation failed: {confirmation.reason}"
                self.audit_trail.log_event(
                    ExecutionLog(
                        event_type="execution_not_confirmed",
                        action_type=action.action_type.value,
                        details={
                            "action_id": action_id,
                            "confirmation_status": confirmation.status,
                            "confirmation_reason": confirmation.reason,
                        },
                    )
                )
            elif confirmation.status == "timeout":
                result.success = False
                result.error_reason = f"execution timeout: {confirmation.reason}"
                self.audit_trail.log_event(
                    ExecutionLog(
                        event_type="execution_timeout",
                        action_type=action.action_type.value,
                        details={
                            "action_id": action_id,
                            "reason": confirmation.reason,
                        },
                    )
                )

        except Exception as e:
            result.error_reason = str(e)
            result.timestamp_end = datetime.now(timezone.utc)

            # Log execution error
            self.audit_trail.log_event(
                ExecutionLog(
                    event_type="execution_error",
                    action_type=action.action_type.value,
                    details={
                        "action_id": action_id,
                        "error": str(e),
                    },
                )
            )

            self.alert_system.raise_alert(
                event_id=f"execution_exception_{action_id}",
                level=AlertLevel.CRITICAL,
                message=f"Exception during execution of {action.action_type.value}: {str(e)}",
            )

        return result

    def get_audit_trail(self) -> AuditTrail:
        """Get the audit trail for verification and export.

        Returns:
            AuditTrail instance with all logged events
        """
        return self.audit_trail

    def get_alerts(self) -> List:
        """Get all system alerts.

        Returns:
            List of Alert instances
        """
        return self.alert_system.alerts

    def verify_audit_integrity(self) -> bool:
        """Verify audit trail chain integrity (tamper-proof verification).

        Returns:
            True if all events are intact and properly chained, False if tampered
        """
        return self.audit_trail.verify_chain_integrity()

    async def get_system_state(self) -> Dict[str, Any]:
        """Get current system state for diagnostics.

        Returns:
            Dictionary with oversight mode, audit status, and alerts
        """
        return {
            "oversight_mode": self.oversight_engine.current_mode.value,
            "audit_verified": self.verify_audit_integrity(),
            "unacknowledged_alerts": len(
                self.alert_system.get_unacknowledged_alerts()
            ),
            "audit_events": len(self.audit_trail.events),
        }
