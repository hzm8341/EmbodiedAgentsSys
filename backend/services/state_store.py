from __future__ import annotations

from backend.models.state import RobotRuntimeState


class StateStore:
    def __init__(self) -> None:
        self._states: dict[str, RobotRuntimeState] = {}

    def put_robot_state(self, state: RobotRuntimeState) -> None:
        self._states[state.robot_id] = state

    def get_robot_state(self, robot_id: str) -> RobotRuntimeState | None:
        return self._states.get(robot_id)

    def list_robot_states(
        self, backend: str | None = None
    ) -> list[RobotRuntimeState]:
        states = list(self._states.values())
        if backend is None:
            return states
        return [state for state in states if state.backend == backend]


state_store = StateStore()
