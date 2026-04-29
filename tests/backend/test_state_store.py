import asyncio

import pytest
from fastapi import HTTPException

from backend.api.state import get_robot_state
from backend.models.state import JointState, RobotRuntimeState
from backend.services.state_store import StateStore, state_store


def test_put_and_get_robot_state_round_trip():
    store = StateStore()
    state = RobotRuntimeState(
        robot_id="arm-1",
        backend="mujoco",
        timestamp=123.4,
        joints=[JointState(name="joint_a", position=1.25)],
        status="moving",
    )

    store.put_robot_state(state)

    assert store.get_robot_state("arm-1") == state


def test_list_robot_states_returns_all_known_robots():
    store = StateStore()
    first = RobotRuntimeState(
        robot_id="arm-1",
        backend="mujoco",
        timestamp=10.0,
        joints=[JointState(name="joint_a", position=0.1)],
    )
    second = RobotRuntimeState(
        robot_id="arm-2",
        backend="mujoco",
        timestamp=20.0,
        joints=[JointState(name="joint_b", position=0.2)],
    )

    store.put_robot_state(first)
    store.put_robot_state(second)

    states = store.list_robot_states()

    assert {state.robot_id for state in states} == {"arm-1", "arm-2"}
    assert store.get_robot_state("missing") is None


def test_list_robot_states_can_filter_by_backend():
    store = StateStore()
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-1",
            backend="mujoco",
            timestamp=10.0,
            joints=[JointState(name="joint_a", position=0.1)],
        )
    )
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-2",
            backend="ros2_gazebo",
            timestamp=20.0,
            joints=[JointState(name="joint_b", position=0.2)],
        )
    )

    states = store.list_robot_states(backend="mujoco")

    assert [state.robot_id for state in states] == ["arm-1"]


def test_get_robot_state_raises_404_for_unknown_robot():
    previous_states = state_store._states.copy()
    state_store._states.clear()

    try:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_robot_state("missing"))
    finally:
        state_store._states.clear()
        state_store._states.update(previous_states)

    assert exc_info.value.status_code == 404
