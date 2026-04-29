import asyncio

from backend.api import state as state_api
from backend.models.state import JointState, RobotRuntimeState
from backend.services.state_store import state_store


def test_update_robot_state_preserves_unknown_backend_on_first_write(monkeypatch):
    sent_messages: list[tuple[str, dict]] = []
    previous_states = state_store._states.copy()
    state_store._states.clear()

    async def fake_send_state(robot_id: str, payload: dict) -> None:
        sent_messages.append((robot_id, payload))

    monkeypatch.setattr(state_api.manager, "send_state", fake_send_state)

    try:
        state = RobotRuntimeState(
            robot_id="ignored-by-endpoint",
            timestamp=12.5,
            joints=[JointState(name="joint_a", position=0.25)],
        )

        asyncio.run(state_api.update_robot_state("arm-1", state))

        stored = state_store.get_robot_state("arm-1")
        assert stored is not None
        assert stored.backend == "unknown"
        assert sent_messages[0][0] == "arm-1"
    finally:
        state_store._states.clear()
        state_store._states.update(previous_states)


def test_update_robot_state_broadcasts_joint_name_payload(monkeypatch):
    sent_messages: list[tuple[str, dict]] = []
    previous_states = state_store._states.copy()
    state_store._states.clear()

    async def fake_send_state(robot_id: str, payload: dict) -> None:
        sent_messages.append((robot_id, payload))

    monkeypatch.setattr(state_api.manager, "send_state", fake_send_state)

    try:
        state = RobotRuntimeState(
            robot_id="ignored-by-endpoint",
            backend="mujoco",
            timestamp=12.5,
            joints=[JointState(name="joint_a", position=0.25)],
        )

        asyncio.run(state_api.update_robot_state("arm-1", state))

        payload = sent_messages[0][1]
        assert payload["joints"] == [{"joint_name": "joint_a", "position": 0.25, "velocity": None}]
        assert "name" not in payload["joints"][0]
    finally:
        state_store._states.clear()
        state_store._states.update(previous_states)
