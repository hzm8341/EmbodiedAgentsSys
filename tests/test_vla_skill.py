# tests/test_vla_skill.py
"""VLASkill 基类测试"""
import pytest
from abc import ABC


def test_skill_status_enum():
    """验证技能状态枚举"""
    from agents.skills.vla_skill import SkillStatus

    assert SkillStatus.IDLE.value == "idle"
    assert SkillStatus.RUNNING.value == "running"
    assert SkillStatus.SUCCESS.value == "success"
    assert SkillStatus.FAILED.value == "failed"


def test_skill_result_dataclass():
    """验证技能结果数据结构"""
    from agents.skills.vla_skill import SkillResult, SkillStatus

    result = SkillResult(status=SkillStatus.SUCCESS, output={"key": "value"})
    assert result.status == SkillStatus.SUCCESS
    assert result.output["key"] == "value"


def test_vla_skill_is_abc():
    """验证VLASkill是抽象基类"""
    from agents.skills.vla_skill import VLASkill

    assert issubclass(VLASkill, ABC)


def test_vla_skill_required_attributes():
    """验证VLASkill必需的属性"""
    from agents.skills.vla_skill import VLASkill

    # 检查类属性
    assert hasattr(VLASkill, "required_inputs")
    assert hasattr(VLASkill, "produced_outputs")
    assert hasattr(VLASkill, "default_vla")
    assert hasattr(VLASkill, "max_steps")


class MockVLAAdapter:
    """模拟 VLA 适配器"""

    def __init__(self):
        self.action_dim = 7

    def act(self, observation, skill_token, termination=None):
        import numpy as np
        return np.zeros(self.action_dim)

    def execute(self, action):
        return {"status": "executed"}


def test_vla_skill_init():
    """验证VLASkill初始化"""
    from agents.skills.vla_skill import VLASkill, SkillStatus

    class TestSkill(VLASkill):
        def build_skill_token(self) -> str:
            return "test"

        def check_preconditions(self, observation: dict) -> bool:
            return True

        def check_termination(self, observation: dict) -> bool:
            return False

    mock_adapter = MockVLAAdapter()
    skill = TestSkill(vla_adapter=mock_adapter)

    assert skill.vla is mock_adapter
    assert skill._status == SkillStatus.IDLE
    assert skill.max_steps == 100
