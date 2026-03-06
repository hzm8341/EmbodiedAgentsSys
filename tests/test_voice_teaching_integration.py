# tests/test_voice_teaching_integration.py
"""语音示教端到端集成测试"""
import pytest


class MockVLAAdapter:
    """模拟 VLA 适配器"""

    def __init__(self):
        self.action_dim = 7

    def act(self, observation, skill_token, termination=None):
        import numpy as np
        return np.zeros(self.action_dim)

    def execute(self, action):
        return {"status": "executed"}


def test_integration_components_exist():
    """验证所有集成组件存在"""
    from agents.components.voice_command import VoiceCommand
    from agents.components.semantic_parser import SemanticParser
    from agents.components.task_planner import TaskPlanner
    from agents.skills.manipulation import GraspSkill, PlaceSkill, ReachSkill

    assert VoiceCommand is not None
    assert SemanticParser is not None
    assert TaskPlanner is not None
    assert GraspSkill is not None
    assert PlaceSkill is not None
    assert ReachSkill is not None


def test_voice_to_skill_pipeline():
    """验证语音到技能的完整流程"""
    from agents.components.voice_command import VoiceCommand
    from agents.components.semantic_parser import SemanticParser

    # 1. 语音命令解析
    voice = VoiceCommand()
    result = voice.parse("向前20厘米")

    assert result.intent == "motion"
    assert result.params["direction"] == "forward"

    # 2. 语义解析器
    parser = SemanticParser()
    parsed = parser.parse("向前20厘米")

    assert parsed["intent"] == "motion"
    assert parsed["direction"] == "forward"
    assert parsed["distance"] == 0.2


def test_task_planning_integration():
    """验证任务规划集成"""
    from agents.components.task_planner import TaskPlanner, PlanningStrategy
    from agents.skills.manipulation import GraspSkill, PlaceSkill

    # 创建规划器
    planner = TaskPlanner(strategy=PlanningStrategy.RULE_BASED)

    # 规划抓取放置任务
    task = planner.plan("抓取杯子放到桌子上")

    # 验证技能序列
    assert "grasp" in task.skills
    assert "place" in task.skills


def test_skill_execution_with_mock_vla():
    """验证使用 mock VLA 执行技能"""
    from agents.skills.manipulation import GraspSkill

    mock_adapter = MockVLAAdapter()

    # 创建抓取技能
    skill = GraspSkill(object_name="cube", vla_adapter=mock_adapter)

    # 模拟观察
    observation = {"object_detected": True, "grasp_success": False}

    # 检查前置条件
    assert skill.check_preconditions(observation) is True


def test_full_teaching_flow():
    """验证完整的示教流程"""
    from agents.components.voice_command import VoiceCommand
    from agents.components.task_planner import TaskPlanner
    from agents.skills.manipulation import GraspSkill, PlaceSkill
    from agents.clients.vla_adapters import LeRobotVLAAdapter

    # 1. 语音输入
    voice = VoiceCommand()
    command = voice.parse("把零件放到盒子里")

    assert command.intent == "task"

    # 2. 任务规划
    planner = TaskPlanner()
    task = planner.plan(command.raw_text)

    # 3. 创建技能
    vla_adapter = LeRobotVLAAdapter(config={"action_dim": 7})

    grasp_skill = GraspSkill(object_name="part", vla_adapter=vla_adapter)
    place_skill = PlaceSkill(target_position=[0.3, 0.0, 0.1], vla_adapter=vla_adapter)

    assert grasp_skill is not None
    assert place_skill is not None
    assert grasp_skill.vla is vla_adapter
