# tests/test_mocks.py
import pytest
import asyncio
from agents.harness.mocks.skill_mocks import MockSkillRegistry
from agents.harness.mocks.hardware_mocks import MockArmAdapter
from agents.harness.mocks.vla_mocks import MockVLAAdapter
from agents.hardware.arm_adapter import Pose6D


def test_mock_skill_registry_returns_result():
    reg = MockSkillRegistry(default_success_rate=1.0)
    result = reg.call_skill("manipulation.grasp", {})
    assert result.success is True
    assert "manipulation.grasp" in result.content


def test_mock_skill_registry_zero_rate_fails():
    reg = MockSkillRegistry(default_success_rate=0.0)
    result = reg.call_skill("manipulation.grasp", {})
    assert result.success is False


def test_mock_arm_adapter_move():
    arm = MockArmAdapter()
    pose = Pose6D(x=0.3, y=0.0, z=0.2, roll=0, pitch=0, yaw=0)
    result = asyncio.run(arm.move_to_pose(pose))
    assert isinstance(result, bool)


def test_mock_arm_adapter_get_state():
    from agents.hardware.arm_adapter import RobotState
    arm = MockArmAdapter(joint_error_rate=0.0)
    state = asyncio.run(arm.get_state())
    assert isinstance(state, RobotState)
    assert 0.0 <= state.gripper_opening <= 1.0


def test_mock_vla_returns_action():
    vla = MockVLAAdapter(success_rate=1.0, action_noise=False)
    action = asyncio.run(vla.act({"image": "test"}, "grasp"))
    assert len(action) == 7
