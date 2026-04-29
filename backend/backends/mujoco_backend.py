from __future__ import annotations

from itertools import count
from types import MappingProxyType
from typing import Any

from backend.backends.base import BackendDescriptor, SimulationBackend
from backend.models.messages import EventEnvelope


class MujocoBackend(SimulationBackend):
    _descriptor = BackendDescriptor(
        backend_id="mujoco",
        display_name="MuJoCo",
        kind="mujoco",
        available=True,
        capabilities=("scene", "state", "command"),
        extensions=MappingProxyType({}),
    )

    def __init__(self, simulation_service=None, event_bus=None, scene_service=None) -> None:
        self._simulation_service = simulation_service
        self._event_bus = event_bus
        self._scene_service = scene_service
        self._seq = count(1)

    @property
    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            backend_id=self._descriptor.backend_id,
            display_name=self._descriptor.display_name,
            kind=self._descriptor.kind,
            available=self._descriptor.available,
            capabilities=tuple(self._descriptor.capabilities),
            extensions=MappingProxyType(dict(self._descriptor.extensions)),
        )

    def get_scene(self) -> dict[str, Any]:
        return self._service.get_scene()

    def execute_command(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        receipt = self._service.execute_action(action, params)
        return {
            "status": receipt.status.value,
            "message": receipt.result_message,
            "data": receipt.result_data or {},
        }

    async def publish_scene_snapshot(self) -> bool:
        if self._event_bus is None or self._scene_service is None:
            return False

        snapshot = self._scene_service.build_snapshot(self)
        await self._event_bus.publish(
            EventEnvelope(
                event="scene_snapshot",
                backend=self.backend_id,
                robot_id=None,
                ts=snapshot.timestamp,
                seq=next(self._seq),
                task_id=None,
                payload=snapshot.model_dump(),
            )
        )
        return True

    @property
    def _service(self):
        if self._simulation_service is None:
            from backend.services.simulation import simulation_service

            self._simulation_service = simulation_service
        return self._simulation_service
