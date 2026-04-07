import pytest
import json


class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_log_execution_event(self):
        from agents.feedback.audit_trail import AuditTrail, ExecutionLog
        trail = AuditTrail()
        event = ExecutionLog(
            event_type="validation_passed",
            action_type="move_to",
            details={"reason": "whitelist ok"}
        )
        trail.log_event(event)
        assert len(trail.events) == 1

    @pytest.mark.asyncio
    async def test_log_chain_integrity(self):
        from agents.feedback.audit_trail import AuditTrail, ExecutionLog
        trail = AuditTrail()
        for i in range(3):
            event = ExecutionLog(
                event_type="test_event",
                action_type="test",
                details={"index": i}
            )
            trail.log_event(event)
        assert trail.verify_chain_integrity()

    def test_alert_system_critical(self):
        from agents.feedback.alert_system import AlertSystem, AlertLevel
        alerts = AlertSystem()
        alerts.raise_alert("critical_boundary_violation", AlertLevel.CRITICAL, "gripper force exceeded")
        assert len(alerts.alerts) == 1
        assert alerts.alerts[0].level == AlertLevel.CRITICAL
