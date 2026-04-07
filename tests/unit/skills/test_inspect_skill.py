# tests/test_inspect_skill.py
"""InspectSkill 检查技能测试"""
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


def test_inspect_skill_init():
    """验证InspectSkill初始化"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cube", inspection_type="detect")
    assert skill.target_object == "cube"
    assert skill.inspection_type == "detect"
    assert skill.max_steps == 20


def test_inspect_skill_init_no_target():
    """验证InspectSkill初始化（无目标物体）"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(inspection_type="verify")
    assert skill.target_object is None
    assert skill.inspection_type == "verify"


def test_build_skill_token():
    """验证技能令牌构建"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cup", inspection_type="quality")
    assert skill.build_skill_token() == "inspect(object=cup, type=quality)"


def test_build_skill_token_no_target():
    """验证技能令牌构建（无目标）"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(inspection_type="detect")
    assert skill.build_skill_token() == "inspect(type=detect)"


def test_check_preconditions():
    """验证前置条件检查"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cube")

    # 有视觉输入
    observation_with_vision = {"image": np.zeros((224, 224, 3))}
    assert skill.check_preconditions(observation_with_vision) is True

    # 无视觉输入
    observation_no_vision = {}
    assert skill.check_preconditions(observation_no_vision) is False


def test_check_termination_complete():
    """验证检查完成终止"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cube")

    # 检查完成
    observation_complete = {"inspection_complete": True}
    assert skill.check_termination(observation_complete) is True


def test_check_termination_detection():
    """验证检测到目标终止"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cube")

    # 检测到目标
    observation_detected = {
        "detections": [
            {"class": "cube", "confidence": 0.9},
            {"class": "sphere", "confidence": 0.7}
        ]
    }
    assert skill.check_termination(observation_detected) is True

    # 未检测到目标
    observation_not_detected = {
        "detections": [
            {"class": "sphere", "confidence": 0.7}
        ]
    }
    assert skill.check_termination(observation_not_detected) is False


def test_verify_object():
    """验证物体验证"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cube")

    observation = {
        "detections": [
            {"class": "cube", "confidence": 0.9},
            {"class": "box", "confidence": 0.8}
        ]
    }

    assert skill.verify_object(observation, "cube") is True
    assert skill.verify_object(observation, "sphere") is False


def test_get_inspection_result():
    """验证获取检查结果"""
    from agents.skills.manipulation.inspect import InspectSkill

    skill = InspectSkill(target_object="cup", inspection_type="quality")
    result = skill.get_inspection_result()

    assert result["type"] == "quality"
    assert result["target"] == "cup"
    assert result["status"] == "completed"


def test_inspect_skill_with_adapter():
    """验证带适配器的InspectSkill"""
    from agents.skills.manipulation.inspect import InspectSkill

    mock_adapter = MockVLAAdapter()
    skill = InspectSkill(target_object="cube", vla_adapter=mock_adapter)

    assert skill.vla is mock_adapter
    assert skill.status.value == "idle"
