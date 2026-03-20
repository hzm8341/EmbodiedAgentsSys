# tests/test_task_planner_component.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from agents.components.task_planner import TaskPlanner, TaskAction, TaskPlan


def test_task_action_fields():
    action = TaskAction(action="pick", target="cup", location="desk")
    assert action.action == "pick"
    assert action.target == "cup"


def test_task_plan_empty():
    plan = TaskPlan(actions=[], instruction="test")
    assert len(plan.actions) == 0
    assert plan.success is True  # 空计划默认成功


@pytest.fixture
def planner():
    return TaskPlanner(
        ollama_model="qwen2.5:3b",
        backend="mock",  # 测试用 mock 后端
    )


def test_planner_parse_valid_json(planner):
    json_str = '[{"action": "go_to", "target": "desk", "location": "desk"}]'
    actions = planner._parse_plan_json(json_str)
    assert len(actions) == 1
    assert actions[0].action == "go_to"


def test_planner_parse_invalid_json_returns_empty(planner):
    actions = planner._parse_plan_json("not json")
    assert actions == []


def test_planner_record_failure(planner):
    planner.record_failure(target="cup", location="desk", reason="not found")
    history = planner.get_failure_history()
    assert len(history) == 1
    assert "cup" in history[0]


def test_planner_clear_history(planner):
    planner.record_failure(target="cup", location="desk", reason="not found")
    planner.clear_history()
    assert planner.get_failure_history() == []


def test_planner_plan_sync_mock(planner):
    """mock 后端同步规划测试。"""
    plan = asyncio.run(planner.plan("拿起桌上的杯子"))
    assert isinstance(plan, TaskPlan)
    assert len(plan.actions) >= 1


def test_planner_replan_with_history(planner):
    """加入失败历史后重规划，历史应出现在 prompt 中。"""
    planner.record_failure(target="flower", location="desk", reason="not found")
    prompt = planner._build_prompt("拿起花")
    assert "flower" in prompt
    assert "desk" in prompt
