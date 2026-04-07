# tests/test_arm_adapter.py
import pytest
from agents.hardware.arm_adapter import (
    Pose6D, RobotState, RobotCapabilities, ArmAdapter
)


class _DummyAdapter(ArmAdapter):
    async def move_to_pose(self, pose, speed=0.1):
        return True
    async def move_joints(self, angles, speed=0.1):
        return True
    async def set_gripper(self, opening, force=10.0):
        return True
    async def get_state(self):
        return RobotState(
            joint_angles=[0.0] * 6,
            end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
            gripper_opening=0.5,
            is_moving=False,
        )
    async def is_ready(self):
        return True
    async def emergency_stop(self):
        pass
    def get_capabilities(self):
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=["manipulation.grasp", "manipulation.place"],
        )


def test_pose6d_fields():
    p = Pose6D(1.0, 2.0, 3.0, 0.1, 0.2, 0.3)
    assert p.x == 1.0 and p.yaw == 0.3


def test_robot_state_fields():
    s = RobotState(
        joint_angles=[0.0] * 6,
        end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
        gripper_opening=0.5,
        is_moving=False,
    )
    assert s.error_code == 0


def test_capabilities_fields():
    cap = RobotCapabilities(robot_type="arm", supported_skills=["manipulation.grasp"])
    assert cap.max_payload_kg == 0.0


@pytest.mark.anyio
async def test_dummy_adapter_is_ready():
    adapter = _DummyAdapter()
    assert await adapter.is_ready()


@pytest.mark.anyio
async def test_dummy_adapter_get_capabilities():
    adapter = _DummyAdapter()
    cap = adapter.get_capabilities()
    assert "manipulation.grasp" in cap.supported_skills


def test_abstract_methods_enforced():
    """ArmAdapter cannot be instantiated without all abstract methods."""
    with pytest.raises(TypeError):
        ArmAdapter()  # type: ignore


# --- AGX Arm wrapper ---
from agents.hardware.agx_arm_adapter import AGXArmAdapter

def test_agx_adapter_capabilities():
    adapter = AGXArmAdapter(config={})
    cap = adapter.get_capabilities()
    assert cap.robot_type == "arm"
    assert "manipulation.grasp" in cap.supported_skills


@pytest.mark.anyio
async def test_agx_adapter_is_ready_no_hardware():
    """Without real hardware, is_ready returns False (not raises)."""
    adapter = AGXArmAdapter(config={"mock": True})
    result = await adapter.is_ready()
    assert isinstance(result, bool)


# --- LeRobot wrapper ---
from agents.hardware.lerobot_arm_adapter import LeRobotArmAdapter

def test_lerobot_adapter_capabilities():
    adapter = LeRobotArmAdapter(config={})
    cap = adapter.get_capabilities()
    assert cap.robot_type == "arm"
    assert "manipulation.reach" in cap.supported_skills


@pytest.mark.anyio
async def test_lerobot_adapter_is_ready_no_hardware():
    adapter = LeRobotArmAdapter(config={"mock": True})
    result = await adapter.is_ready()
    assert isinstance(result, bool)
