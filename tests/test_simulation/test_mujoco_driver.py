import pytest
from simulation.mujoco.mujoco_driver import MuJoCoDriver
from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus

class TestMuJoCoDriver:
    def test_create_driver(self):
        driver = MuJoCoDriver()
        assert driver is not None

    def test_execute_action_returns_receipt(self):
        driver = MuJoCoDriver()
        receipt = driver.execute_action("move_to", {"x": 0.1, "y": 0.0, "z": 0.5})
        assert isinstance(receipt, ExecutionReceipt)
        assert receipt.receipt_id is not None

    def test_get_scene_returns_dict(self):
        driver = MuJoCoDriver()
        scene = driver.get_scene()
        assert isinstance(scene, dict)

    def test_emergency_stop(self):
        driver = MuJoCoDriver()
        receipt = driver.emergency_stop()
        assert receipt.status == ExecutionStatus.EMERGENCY_STOP

    def test_get_allowed_actions(self):
        driver = MuJoCoDriver()
        actions = driver.get_allowed_actions()
        assert "move_to" in actions
        assert "grasp" in actions

    def test_invalid_action_rejected(self):
        driver = MuJoCoDriver()
        receipt = driver.execute_action("invalid_action", {})
        assert receipt.status == ExecutionStatus.FAILED
