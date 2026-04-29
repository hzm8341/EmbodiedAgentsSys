from __future__ import annotations

import time
from typing import Any

from backend.models.scene import RobotView, SceneViewModel
from backend.services.state_store import StateStore, state_store


class SceneService:
    def __init__(self, store: StateStore) -> None:
        self._store = store

    def build_snapshot(self, backend: Any) -> SceneViewModel:
        backend_id = getattr(getattr(backend, "descriptor", backend), "backend_id", "unknown")
        raw_scene = self._get_raw_scene(backend)
        robot_states = [
            state
            for state in self._store.list_robot_states()
            if state.backend in (backend_id, "unknown")
        ]
        timestamp = max((state.timestamp for state in robot_states), default=time.time())

        return SceneViewModel(
            backend=backend_id,
            timestamp=timestamp,
            robots=[
                RobotView(
                    robot_id=state.robot_id,
                    joints=state.joints,
                    pose=state.pose,
                    status=state.status,
                )
                for state in robot_states
            ],
            objects=list(raw_scene.get("objects", [])),
            overlays=list(raw_scene.get("overlays", [])),
            metadata=dict(raw_scene.get("metadata", {})),
        )

    def _get_raw_scene(self, backend: Any) -> dict:
        if not hasattr(backend, "get_scene"):
            return {}
        try:
            return backend.get_scene()
        except ModuleNotFoundError:
            return {}


scene_service = SceneService(state_store)
