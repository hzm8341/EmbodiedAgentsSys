"""Tests for SimulationDriver."""
import pytest
from embodiedagentsys.hal.drivers import SimulationDriver
from embodiedagentsys.hal.types import ExecutionStatus


class TestSimulationDriver:
    def test_driver_returns_receipt(self):
        """execute_action must return ExecutionReceipt."""
        driver = SimulationDriver()
        receipt = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
        assert hasattr(receipt, 'receipt_id')
        assert hasattr(receipt, 'status')

    def test_move_to_success(self):
        """move_to should succeed with valid params."""
        driver = SimulationDriver()
        receipt = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
        assert receipt.status == ExecutionStatus.SUCCESS
        assert receipt.is_success()

    def test_grasp_success(self):
        """grasp should succeed."""
        driver = SimulationDriver()
        receipt = driver.execute_action("grasp", {"force": 0.8})
        assert receipt.status == ExecutionStatus.SUCCESS
        assert receipt.result_data["gripper_state"] == "closed"

    def test_invalid_action_rejected(self):
        """Actions not in whitelist should be rejected."""
        driver = SimulationDriver()
        receipt = driver.execute_action("emergency_shutdown", {})
        assert receipt.status == ExecutionStatus.FAILED

    def test_emergency_stop(self):
        """emergency_stop should return EMERGENCY_STOP status."""
        driver = SimulationDriver()
        receipt = driver.emergency_stop()
        assert receipt.status == ExecutionStatus.EMERGENCY_STOP

    def test_is_instance_of_base_driver(self):
        """SimulationDriver should be BaseDriver subclass."""
        from embodiedagentsys.hal.base_driver import BaseDriver
        driver = SimulationDriver()
        assert isinstance(driver, BaseDriver)
