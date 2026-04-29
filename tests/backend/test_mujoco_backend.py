import asyncio

from backend.backends.mujoco_backend import MujocoBackend
from backend.models.state import JointState, RobotRuntimeState
from backend.services.event_bus import EventBus
from backend.services.scene_service import SceneService
from backend.services.state_store import StateStore


class FakeSimulationService:
    def get_scene(self):
        return {"robot_position": [0, 0, 0]}

    def execute_action(self, action, params):
        class Receipt:
            class Status:
                value = "success"

            status = Status()
            result_message = "ok"
            result_data = {"action": action, "params": params}

        return Receipt()


def test_mujoco_backend_adapts_existing_service():
    backend = MujocoBackend(simulation_service=FakeSimulationService())

    scene = backend.get_scene()
    result = backend.execute_command("move_joint", {"joint": "j1"})

    assert scene["robot_position"] == [0, 0, 0]
    assert result == {
        "status": "success",
        "message": "ok",
        "data": {"action": "move_joint", "params": {"joint": "j1"}},
    }


def test_mujoco_backend_publishes_scene_snapshot_event():
    async def scenario():
        store = StateStore()
        store.put_robot_state(
            RobotRuntimeState(
                robot_id="arm-1",
                backend="mujoco",
                timestamp=42.0,
                joints=[JointState(name="joint_a", position=0.5)],
            )
        )
        bus = EventBus()
        subscriber = bus.subscribe()
        backend = MujocoBackend(
            simulation_service=FakeSimulationService(),
            event_bus=bus,
            scene_service=SceneService(store),
        )

        published = await backend.publish_scene_snapshot()

        return published, await subscriber.get()

    published, event = asyncio.run(scenario())

    assert published is True
    assert event.event == "scene_snapshot"
    assert event.backend == "mujoco"
    assert event.seq == 1
    assert event.payload["backend"] == "mujoco"
    assert event.payload["robots"][0]["robot_id"] == "arm-1"
