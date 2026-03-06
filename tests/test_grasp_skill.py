# tests/test_grasp_skill.py
"""GraspSkill 抓取技能测试"""
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


def test_grasp_skill_init():
    """验证GraspSkill初始化"""
    from agents.skills.manipulation.grasp import GraspSkill

    skill = GraspSkill(object_name="cube")
    assert skill.object_name == "cube"
    assert skill.max_steps == 50


def test_build_skill_token():
    """验证技能令牌构建"""
    from agents.skills.manipulation.grasp import GraspSkill

    skill = GraspSkill(object_name="cube")
    assert skill.build_skill_token() == "grasp cube"


def test_build_skill_token_different_objects():
    """验证不同物体的技能令牌"""
    from agents.skills.manipulation.grasp import GraspSkill

    skill_bottle = GraspSkill(object_name="bottle")
    assert skill_bottle.build_skill_token() == "grasp bottle"

    skill_tool = GraspSkill(object_name="screwdriver")
    assert skill_tool.build_skill_token() == "grasp screwdriver"


def test_check_preconditions():
    """验证前置条件检查"""
    from agents.skills.manipulation.grasp import GraspSkill

    skill = GraspSkill(object_name="cube")

    # 物体在视野内
    observation_true = {"object_detected": True}
    assert skill.check_preconditions(observation_true) is True

    # 物体不在视野内
    observation_false = {"object_detected": False}
    assert skill.check_preconditions(observation_false) is False


def test_check_termination():
    """验证终止条件检查"""
    from agents.skills.manipulation.grasp import GraspSkill

    skill = GraspSkill(object_name="cube")

    # 抓取成功
    observation_success = {"grasp_success": True}
    assert skill.check_termination(observation_success) is True

    # 抓取未成功
    observation_pending = {"grasp_success": False}
    assert skill.check_termination(observation_pending) is False


def test_grasp_skill_with_adapter():
    """验证带适配器的GraspSkill"""
    from agents.skills.manipulation.grasp import GraspSkill

    mock_adapter = MockVLAAdapter()
    skill = GraspSkill(object_name="cube", vla_adapter=mock_adapter)

    assert skill.vla is mock_adapter
    assert skill.status.value == "idle"
