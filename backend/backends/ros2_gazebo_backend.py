from __future__ import annotations

from types import MappingProxyType

from backend.backends.base import BackendDescriptor, SimulationBackend


class ROS2GazeboBackend(SimulationBackend):
    backend_id = "ros2_gazebo"

    def __init__(self, node) -> None:
        self._node = node

    @property
    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            backend_id=self.backend_id,
            display_name="ROS2 Humble + Gazebo",
            kind="ros2_gazebo",
            available=self._node is not None,
            capabilities=("scene", "state", "command", "topics", "services"),
            extensions=MappingProxyType(
                {
                    "backend_specific_commands": ("publish_topic", "call_service"),
                    "notes": "ROS2 backend skeleton; node bridge wiring is pending",
                }
            ),
        )

    def execute_command(self, action: str, params: dict) -> dict:
        return {
            "status": "unavailable",
            "message": f"ROS2 backend command '{action}' is not wired yet",
            "data": {"params": params},
        }
