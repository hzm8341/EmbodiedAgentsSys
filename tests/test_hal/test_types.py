import pytest
from datetime import datetime
from embodiedagentsys.hal.types import ExecutionStatus, ExecutionReceipt


class TestExecutionStatus:
    def test_status_constants_defined(self):
        """All required status constants must be defined."""
        assert ExecutionStatus.SUCCESS == "success"
        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.TIMEOUT == "timeout"
        assert ExecutionStatus.EMERGENCY_STOP == "emergency_stop"


class TestExecutionReceipt:
    def test_receipt_can_be_created(self):
        """ExecutionReceipt should be creatable with required fields."""
        receipt = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={"x": 1.0, "y": 2.0},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="Moved successfully"
        )
        assert receipt.receipt_id == "test-001"
        assert receipt.action_type == "move_to"
        assert receipt.status == ExecutionStatus.SUCCESS

    def test_receipt_has_result_data(self):
        """Receipt should have optional result_data field."""
        receipt = ExecutionReceipt(
            receipt_id="test-002",
            action_type="grasp",
            params={"force": 0.8},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="Grasped",
            result_data={"force_applied": 0.8}
        )
        assert receipt.result_data is not None
        assert receipt.result_data["force_applied"] == 0.8

    def test_receipt_id_must_be_unique(self):
        """Each receipt should have a unique ID for tracking."""
        receipt1 = ExecutionReceipt(
            receipt_id="test-001",
            action_type="move_to",
            params={},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="ok"
        )
        receipt2 = ExecutionReceipt(
            receipt_id="test-002",
            action_type="move_to",
            params={},
            status=ExecutionStatus.SUCCESS,
            timestamp=datetime.now(),
            result_message="ok"
        )
        assert receipt1.receipt_id != receipt2.receipt_id
