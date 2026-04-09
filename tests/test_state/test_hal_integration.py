"""Integration tests for HAL and State module."""

import pytest
from embodiedagentsys.state.manager import StateManager
from embodiedagentsys.state.types import ProtocolType
from embodiedagentsys.hal.drivers import SimulationDriver


class TestHALStateIntegration:
    """Test HAL and State integration for闭环确认."""

    def test_driver_scene_synced_to_state(self):
        """Driver scene should sync to STATE."""
        state_mgr = StateManager()
        driver = SimulationDriver()

        # Execute action
        receipt = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
        assert receipt.is_success()

        # Get scene from driver
        scene = driver.get_scene()

        # Write to state
        state_mgr.write_protocol(ProtocolType.ENVIRONMENT, scene)

        # Read back
        saved_scene = state_mgr.read_protocol(ProtocolType.ENVIRONMENT)
        assert saved_scene == scene

    def test_state_manager_with_hal_driver(self):
        """StateManager should work with HAL driver pattern."""
        driver = SimulationDriver()
        state_mgr = StateManager()

        # Driver provides allowed actions
        allowed = driver.get_allowed_actions()
        assert "move_to" in allowed
        assert "grasp" in allowed

        # Execute and record
        receipt = driver.execute_action("grasp", {"force": 0.8})
        state_mgr.write_protocol(
            ProtocolType.ACTION,
            {"last_action": receipt.action_type, "status": receipt.status.value}
        )

        action_state = state_mgr.read_protocol(ProtocolType.ACTION)
        assert action_state["last_action"] == "grasp"

    def test_driver_provides_profile_path(self):
        """Driver should provide profile path."""
        driver = SimulationDriver()
        profile_path = driver.get_profile_path()
        assert profile_path is not None
        assert str(profile_path).endswith(".md")

    def test_receipt_tracking_in_state(self):
        """Receipts should be trackable through state."""
        state_mgr = StateManager()
        driver = SimulationDriver()

        # Execute action and get receipt
        receipt1 = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
        receipt2 = driver.execute_action("grasp", {"force": 0.8})

        # Record receipts
        state_mgr.write_protocol(ProtocolType.ACTION, {
            "receipts": [
                {"id": receipt1.receipt_id, "action": receipt1.action_type},
                {"id": receipt2.receipt_id, "action": receipt2.action_type},
            ]
        })

        # Read back
        state = state_mgr.read_protocol(ProtocolType.ACTION)
        assert len(state["receipts"]) == 2
