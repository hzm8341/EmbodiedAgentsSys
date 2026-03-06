# tests/test_reach_skill.py
"""ReachSkill 到达技能测试"""
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


def test_reach_skill_init():
    """验证ReachSkill初始化"""
    from agents.skills.manipulation.reach import ReachSkill

    skill = ReachSkill(target_position=[0.3, 0.2, 0.1])
    assert skill.target_position == [0.3, 0.2, 0.1]
    assert skill.max_steps == 30


def test_build_skill_token():
    """验证技能令牌构建"""
    from agents.skills.manipulation.reach import ReachSkill

    skill = ReachSkill(target_position=[0.3, 0.2, 0.1])
    token = skill.build_skill_token()
    assert "reach" in token
    assert "0.3" in token


def test_reach_skill_with_position_3d():
    """验证3D位置"""
    from agents.skills.manipulation.reach import ReachSkill

    skill = ReachSkill(target_position=[0.5, -0.3, 0.2])
    assert skill.target_position == [0.5, -0.3, 0.2]

    pos_str = str(skill.target_position)
    assert "0.5" in pos_str


def test_check_preconditions():
    """验证前置条件检查"""
    from agents.skills.manipulation.reach import ReachSkill

    skill = ReachSkill(target_position=[0.3, 0.2, 0.1])

    # 无碰撞，安全
    observation_safe = {"collision_detected": False}
    assert skill.check_preconditions(observation_safe) is True

    # 有碰撞
    observation_collision = {"collision_detected": True}
    assert skill.check_preconditions(observation_collision) is False


def test_check_termination():
    """验证终止条件检查"""
    from agents.skills.manipulation.reach import ReachSkill

    skill = ReachSkill(target_position=[0.3, 0.2, 0.1])

    # 到达目标
    observation_reached = {"position_reached": True}
    assert skill.check_termination(observation_reached) is True

    # 未到达
    observation_pending = {"position_reached": False}
    assert skill.check_termination(observation_pending) is False


def test_check_termination_by_distance():
    """验证基于距离的终止条件"""
    from agents.skills.manipulation.reach import ReachSkill

    skill = ReachSkill(target_position=[0.0, 0.0, 0.0])

    # 距离小于阈值
    observation_close = {"distance_to_target": 0.01}
    assert skill.check_termination(observation_close) is True

    # 距离大于阈值
    observation_far = {"distance_to_target": 0.5}
    assert skill.check_termination(observation_far) is False


def test_reach_skill_with_adapter():
    """验证带适配器的ReachSkill"""
    from agents.skills.manipulation.reach import ReachSkill

    mock_adapter = MockVLAAdapter()
    skill = ReachSkill(
        target_position=[0.3, 0.2, 0.1],
        vla_adapter=mock_adapter
    )

    assert skill.vla is mock_adapter
    assert skill.status.value == "idle"
