from __future__ import annotations

import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from backend.backends.base import BackendDescriptor, SimulationBackend
from backend.services.safety_guard import SafetyGuard


@dataclass
class RealRobotConnection:
    connected: bool = False
    last_heartbeat: float = 0.0


class RealRobotBackend(SimulationBackend):
    backend_id = "real_robot"

    def __init__(self) -> None:
        self._connection = RealRobotConnection()
        self._guard = SafetyGuard()

    @property
    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            backend_id=self.backend_id,
            display_name="Real Robot",
            kind="real",
            available=True,
            capabilities=("command", "state", "safety", "lifecycle"),
            extensions=MappingProxyType({"requires_auth": True}),
        )

    def initialize(self) -> dict[str, Any]:
        self._connection.connected = True
        self._connection.last_heartbeat = time.time()
        return {"status": "connected"}

    def heartbeat(self) -> dict[str, Any]:
        self._connection.last_heartbeat = time.time()
        return {"status": "ok", "ts": self._connection.last_heartbeat}

    def reconnect(self) -> dict[str, Any]:
        self.shutdown()
        return self.initialize()

    def shutdown(self) -> dict[str, Any]:
        self._connection.connected = False
        return {"status": "disconnected"}

    def execute_command(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._connection.connected:
            return {"status": "failed", "message": "real robot not connected", "data": {}}
        decision = self._guard.validate(action, params)
        if not decision.allowed:
            return {
                "status": "blocked",
                "message": decision.reason,
                "data": {"action": action, "params": params},
            }
        return {
            "status": "success",
            "message": f"command '{action}' acknowledged",
            "data": {
                "acknowledged": True,
                "action": action,
                "params": params,
                "completed": True,
            },
        }
