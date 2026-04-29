from __future__ import annotations

from backend.services.simulation import SimulationService
from backend.services.state_store import state_store


def test_simulation_service_publishes_joint_state_after_action() -> None:
    previous_states = state_store._states.copy()
    state_store._states.clear()
    service = SimulationService()
    old_driver = service._driver
    try:
        service.close_viewer()
        service._driver = None
        service.initialize("assets/eyoubot/eu_ca_simple.urdf")

        result = service.execute_action(
            "move_arm_to",
            {"arm": "left", "x": 0.04, "y": 0.36, "z": 0.83},
        )

        state = state_store.get_robot_state("eyoubot")
        assert result.status.value == "success"
        assert state is not None
        assert state.backend == "mujoco"
        assert state.status == "active"
        assert {joint.name for joint in state.joints} >= {
            "left_hand_joint1",
            "left_hand_joint2",
            "left_hand_joint3",
        }
    finally:
        service.close_viewer()
        service._driver = old_driver
        state_store._states.clear()
        state_store._states.update(previous_states)
