"""Simulation driver for testing without real hardware."""

from pathlib import Path
from embodiedagentsys.hal.base_driver import BaseDriver
from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus


class SimulationDriver(BaseDriver):
    """Simulation driver with proper闭环确认.

    Returns ExecutionReceipt for every action.
    """

    def __init__(self, gui: bool = False, **kwargs):
        self._gui = gui
        self._scene: dict = {"objects": {}, "robots": {}}
        self._connected = False
        self._position = {"x": 0.0, "y": 0.0, "z": 0.0}

    def get_profile_path(self) -> Path:
        return Path(__file__).resolve().parent / "profiles" / "simulation.md"

    def get_allowed_actions(self) -> list[str]:
        """Whitelist of allowed actions."""
        return ["move_to", "move_relative", "grasp", "release", "get_scene"]

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """Execute simulated action with receipt."""
        valid, reason = self.validate_action(action_type, params)
        if not valid:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Validation failed: {reason}"
            )

        if action_type == "move_to":
            self._position = {
                "x": params.get("x", 0.0),
                "y": params.get("y", 0.0),
                "z": params.get("z", 0.0),
            }
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Moved to {self._position}",
                result_data={"position": self._position}
            )
        elif action_type == "grasp":
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message="Grasped",
                result_data={"gripper_state": "closed", "force": params.get("force", 0.5)}
            )
        elif action_type == "release":
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message="Released",
                result_data={"gripper_state": "open"}
            )
        else:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Simulated {action_type}"
            )

    def get_scene(self) -> dict:
        return dict(self._scene)

    def is_connected(self) -> bool:
        return self._connected

    def health_check(self) -> dict:
        return {
            "status": "ok",
            "driver": "simulation",
            "position": self._position,
        }

    def emergency_stop(self) -> ExecutionReceipt:
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Simulation emergency stop executed"
        )
