import pytest
from datetime import datetime
from embodiedagentsys.hal.audit import AuditLogger, AuditEntry, AuditEventType
from embodiedagentsys.hal.types import ExecutionStatus, ExecutionReceipt


class TestAuditEntry:
    def test_audit_entry_creation(self):
        """AuditEntry should capture all required fields."""
        entry = AuditEntry(
            event_type=AuditEventType.ACTION_EXECUTED,
            receipt_id="test-001",
            action_type="move_to",
            params={"x": 1.0},
            status=ExecutionStatus.SUCCESS,
            operator="llm_agent"
        )
        assert entry.event_type == AuditEventType.ACTION_EXECUTED
        assert entry.receipt_id == "test-001"


class TestAuditLogger:
    def test_logger_records_action(self):
        """Logger should record action execution."""
        logger = AuditLogger()
        receipt = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={"x": 1.0},
            status=ExecutionStatus.SUCCESS,
            result_message="Moved"
        )
        entry = logger.log_action(receipt, operator="test")
        assert entry is not None
        assert entry.receipt_id == "test-001"

    def test_logger_records_validation(self):
        """Logger should record validation decisions."""
        logger = AuditLogger()
        entry = logger.log_validation(
            action_type="move_to",
            params={"x": 1.0},
            allowed=True,
            operator="test"
        )
        assert entry.event_type == AuditEventType.VALIDATION_RESULT

    def test_logger_records_emergency_stop(self):
        """Logger should record emergency stops."""
        logger = AuditLogger()
        entry = logger.log_emergency_stop(operator="operator_001", reason="Safety boundary violated")
        assert entry.event_type == AuditEventType.EMERGENCY_STOP

    def test_logger_returns_entries(self):
        """Logger should return logged entries for review."""
        logger = AuditLogger()
        receipt = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={},
            status=ExecutionStatus.SUCCESS,
            result_message="ok"
        )
        logger.log_action(receipt)
        entries = logger.get_entries()
        assert len(entries) >= 1
