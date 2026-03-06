# tests/test_place_skill.py
"""PlaceSkill 放置技能测试"""
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


def test_place_skill_init():
    """验证PlaceSkill初始化"""
    from agents.skills.manipulation.place import PlaceSkill

    skill = PlaceSkill(target_position=[0.5, 0.0, 0.1])
    assert skill.target_position == [0.5, 0.0, 0.1]
    assert skill.max_steps == 50


def test_build_skill_token():
    """验证技能令牌构建"""
    from agents.skills.manipulation.place import PlaceSkill

    skill = PlaceSkill(target_position=[0.5, 0.0, 0.1])
    token = skill.build_skill_token()
    assert "place" in token
    assert "0.5" in token


def test_check_preconditions():
    """验证前置条件检查"""
    from agents.skills.manipulation.place import PlaceSkill

    skill = PlaceSkill(target_position=[0.5, 0.0, 0.1])

    # 物体已被抓取
    observation_held = {"object_held": True}
    assert skill.check_preconditions(observation_held) is True

    # 物体未被抓取
    observation_not_held = {"object_held": False}
    assert skill.check_preconditions(observation_not_held) is False


def test_check_termination():
    """验证终止条件检查"""
    from agents.skills.manipulation.place import PlaceSkill

    skill = PlaceSkill(target_position=[0.5, 0.0, 0.1])

    # 放置成功
    observation_success = {"placement_success": True}
    assert skill.check_termination(observation_success) is True

    # 放置未成功
    observation_pending = {"placement_success": False}
    assert skill.check_termination(observation_pending) is False


def test_place_skill_with_adapter():
    """验证带适配器的PlaceSkill"""
    from agents.skills.manipulation.place import PlaceSkill

    mock_adapter = MockVLAAdapter()
    skill = PlaceSkill(
        target_position=[0.5, 0.0, 0.1],
        vla_adapter=mock_adapter
    )

    assert skill.vla is mock_adapter
    assert skill.status.value == "idle"
