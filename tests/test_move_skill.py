# tests/test_move_skill.py
"""MoveSkill 关节运动技能测试"""
import pytest
import numpy as np


class MockVLAAdapter:
    """模拟 VLA 适配器"""

    def __init__(self):
        self.action_dim = 7

    def act(self, observation, skill_token, termination=None):
        return np.zeros(self.action_dim)

    def execute(self, action):
        return {"status": "executed"}


def test_move_skill_init_joints():
    """验证MoveSkill初始化（关节模式）"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert skill.target_joints == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert skill.max_steps == 30


def test_move_skill_init_pose():
    """验证MoveSkill初始化（末端位姿模式）"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_pose=[0.3, 0.0, 0.2, 0.0, 0.0, 0.0])
    assert skill.target_pose == [0.3, 0.0, 0.2, 0.0, 0.0, 0.0]


def test_build_skill_token_joints():
    """验证关节模式技能令牌"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_joints=[0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0])
    assert skill.build_skill_token() == "move(joints=[0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0])"


def test_build_skill_token_pose():
    """验证末端位姿模式技能令牌"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_pose=[0.3, 0.0, 0.2, 0.0, 0.0, 0.0])
    assert skill.build_skill_token() == "move(pose=[0.3, 0.0, 0.2, 0.0, 0.0, 0.0])"


def test_check_preconditions():
    """验证前置条件检查"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_joints=[0.0, 0.0, 0.0])

    # 无碰撞
    observation_safe = {"collision_detected": False}
    assert skill.check_preconditions(observation_safe) is True

    # 有碰撞
    observation_collision = {"collision_detected": True}
    assert skill.check_preconditions(observation_collision) is False


def test_check_termination_by_joint_error():
    """验证基于关节误差的终止条件"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_joints=[0.0, 0.0, 0.0])

    # 关节误差小于阈值
    observation_close = {"joint_error": 0.005}
    assert skill.check_termination(observation_close) is True

    # 关节误差大于阈值
    observation_far = {"joint_error": 0.05}
    assert skill.check_termination(observation_far) is False


def test_check_termination_by_pose_error():
    """验证基于末端位姿误差的终止条件"""
    from agents.skills.manipulation.move import MoveSkill

    skill = MoveSkill(target_pose=[0.3, 0.0, 0.2])

    # 末端误差小于阈值
    observation_close = {"pose_error": 0.003}
    assert skill.check_termination(observation_close) is True


def test_move_skill_with_adapter():
    """验证带适配器的MoveSkill"""
    from agents.skills.manipulation.move import MoveSkill

    mock_adapter = MockVLAAdapter()
    skill = MoveSkill(target_joints=[0.0, 0.0, 0.0], vla_adapter=mock_adapter)

    assert skill.vla is mock_adapter
    assert skill.status.value == "idle"
