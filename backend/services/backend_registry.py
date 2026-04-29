from __future__ import annotations

from backend.backends.base import BackendDescriptor, SimulationBackend


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, SimulationBackend] = {}
        self._selected_backend_id: str | None = None

    def register(self, backend: SimulationBackend) -> None:
        if backend.backend_id in self._backends:
            raise ValueError(f"Backend {backend.backend_id} is already registered")
        self._backends[backend.backend_id] = backend
        if self._selected_backend_id is None:
            self._selected_backend_id = backend.backend_id

    def list_backends(self) -> list[BackendDescriptor]:
        return [backend.descriptor for backend in self._backends.values()]

    def select_backend(self, backend_id: str) -> SimulationBackend:
        try:
            backend = self._backends[backend_id]
        except KeyError:
            raise KeyError(backend_id) from None

        self._selected_backend_id = backend_id
        return backend

    def get_backend(self, backend_id: str) -> SimulationBackend:
        try:
            return self._backends[backend_id]
        except KeyError:
            raise KeyError(backend_id) from None

    def get_selected_backend(self) -> SimulationBackend:
        if self._selected_backend_id is None:
            raise RuntimeError("No backend registered")
        return self._backends[self._selected_backend_id]


backend_registry = BackendRegistry()


def ensure_default_backends(simulation_service=None) -> None:
    from backend.backends.mujoco_backend import MujocoBackend
    from backend.backends.ros2_gazebo_backend import ROS2GazeboBackend

    for backend in (
        MujocoBackend(simulation_service=simulation_service),
        ROS2GazeboBackend(node=None),
    ):
        try:
            backend_registry.register(backend)
        except ValueError:
            continue
