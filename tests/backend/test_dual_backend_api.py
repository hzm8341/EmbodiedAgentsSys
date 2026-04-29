import pytest

from backend.api.routes import (
    SelectBackendRequest,
    BackendCommandRequest,
    execute_backend_command,
    get_backend_capabilities,
    get_scene_view,
    list_backends,
    select_backend,
)
from backend.models.state import JointState, RobotRuntimeState
from backend.services.backend_registry import backend_registry, ensure_default_backends
from backend.services.state_store import state_store


def _reset_selection() -> None:
    ensure_default_backends()
    backend_registry.select_backend("mujoco")


def test_backends_endpoint_lists_default_backends():
    _reset_selection()

    data = list_backends()

    backend_ids = {item["backend_id"] for item in data["backends"]}
    assert data["selected_backend"] == "mujoco"
    assert {"mujoco", "ros2_gazebo"}.issubset(backend_ids)


def test_select_backend_updates_current_selection():
    _reset_selection()

    response = select_backend(SelectBackendRequest(backend_id="ros2_gazebo"))

    assert response["selected_backend"] == "ros2_gazebo"


def test_select_backend_rejects_unknown_backend():
    _reset_selection()

    with pytest.raises(Exception) as exc:
        select_backend(SelectBackendRequest(backend_id="missing"))

    assert getattr(exc.value, "status_code") == 404


def test_backend_capabilities_exposes_backend_specific_extensions():
    _reset_selection()

    capabilities = get_backend_capabilities("ros2_gazebo")

    assert capabilities["backend_id"] == "ros2_gazebo"
    assert "topics" in capabilities["capabilities"]
    assert "backend_specific_commands" in capabilities["extensions"]


def test_backend_command_passthrough_for_ros2_skeleton():
    _reset_selection()

    result = execute_backend_command(
        "ros2_gazebo",
        "publish_topic",
        BackendCommandRequest(params={"topic": "/joint_states"}),
    )

    assert result["status"] == "unavailable"
    assert "not wired yet" in result["message"]


def test_scene_endpoint_uses_selected_backend():
    _reset_selection()
    state_store.put_robot_state(
        RobotRuntimeState(
            robot_id="scene-api-robot",
            backend="unknown",
            timestamp=123.0,
            joints=[JointState(name="joint_a", position=0.5)],
        )
    )

    scene = get_scene_view()

    assert scene.backend == "mujoco"
    assert any(robot.robot_id == "scene-api-robot" for robot in scene.robots)
