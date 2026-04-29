from types import SimpleNamespace

from backend.models.state import JointState, RobotRuntimeState
from backend.services.scene_service import SceneService
from backend.services.state_store import StateStore


class FakeBackend:
    def __init__(self) -> None:
        self.descriptor = SimpleNamespace(backend_id="mujoco")

    def get_scene(self) -> dict:
        return {
            "objects": [{"id": "cube", "position": [1.0, 2.0, 3.0]}],
            "metadata": {"source": "fake-driver"},
        }


class MissingOptionalDependencyBackend:
    descriptor = SimpleNamespace(backend_id="mujoco")

    def get_scene(self) -> dict:
        raise ModuleNotFoundError("missing optional dependency")


def test_build_snapshot_projects_backend_scene_and_robot_states():
    store = StateStore()
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-1",
            backend="mujoco",
            timestamp=42.0,
            joints=[JointState(name="joint_a", position=0.5)],
            status="ready",
        )
    )
    service = SceneService(store)

    snapshot = service.build_snapshot(FakeBackend())

    assert snapshot.backend == "mujoco"
    assert snapshot.timestamp == 42.0
    assert len(snapshot.robots) == 1
    assert snapshot.robots[0].robot_id == "arm-1"
    assert snapshot.robots[0].joints[0].name == "joint_a"
    assert snapshot.objects == [{"id": "cube", "position": [1.0, 2.0, 3.0]}]
    assert snapshot.metadata == {"source": "fake-driver"}


def test_build_snapshot_keeps_robot_state_when_raw_scene_dependency_is_missing():
    store = StateStore()
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-1",
            backend="mujoco",
            timestamp=42.0,
            joints=[JointState(name="joint_a", position=0.5)],
        )
    )
    service = SceneService(store)

    snapshot = service.build_snapshot(MissingOptionalDependencyBackend())

    assert snapshot.backend == "mujoco"
    assert [robot.robot_id for robot in snapshot.robots] == ["arm-1"]
    assert snapshot.objects == []


def test_build_snapshot_scopes_robot_states_to_backend():
    store = StateStore()
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-1",
            backend="mujoco",
            timestamp=42.0,
            joints=[JointState(name="joint_a", position=0.5)],
        )
    )
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-2",
            backend="ros2_gazebo",
            timestamp=84.0,
            joints=[JointState(name="joint_b", position=1.5)],
        )
    )
    service = SceneService(store)

    snapshot = service.build_snapshot(FakeBackend())

    assert [robot.robot_id for robot in snapshot.robots] == ["arm-1"]
    assert snapshot.timestamp == 42.0


def test_build_snapshot_includes_unknown_backend_states_as_compatibility_fallback():
    store = StateStore()
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-1",
            backend="unknown",
            timestamp=42.0,
            joints=[JointState(name="joint_a", position=0.5)],
        )
    )
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm-2",
            backend="ros2_gazebo",
            timestamp=84.0,
            joints=[JointState(name="joint_b", position=1.5)],
        )
    )
    service = SceneService(store)

    snapshot = service.build_snapshot(FakeBackend())

    assert [robot.robot_id for robot in snapshot.robots] == ["arm-1"]
    assert snapshot.timestamp == 42.0
