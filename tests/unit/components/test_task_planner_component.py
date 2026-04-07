# tests/test_task_planner_component.py
import pytest
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


@pytest.mark.anyio
async def test_planner_plan_sync_mock(planner):
    """mock 后端同步规划测试。"""
    plan = await planner.plan("拿起桌上的杯子")
    assert isinstance(plan, TaskPlan)
    assert len(plan.actions) >= 1


def test_planner_replan_with_history(planner):
    """加入失败历史后重规划，历史应出现在 prompt 中。"""
    planner.record_failure(target="flower", location="desk", reason="not found")
    prompt = planner._build_prompt("拿起花")
    assert "flower" in prompt
    assert "desk" in prompt


# ---------- Integration Tests ----------

from agents.components.semantic_map import SemanticMap


def test_planner_uses_semantic_map_in_prompt(planner, tmp_path):
    """规划 prompt 应包含语义地图中的地点信息。"""
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("实验台", x=1.5, y=0.0, theta=0.0)
    sm.add_object("烧杯", location="实验台")

    planner._semantic_map = sm
    prompt = planner._build_prompt("拿起烧杯")
    assert "实验台" in prompt
    assert "烧杯" in prompt


@pytest.mark.anyio
async def test_full_replan_cycle(tmp_path):
    """完整重规划循环：规划 → 记录失败 → 重规划。"""
    from agents.components.task_planner import TaskPlanner
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("桌子", x=1.0, y=0.0, theta=0.0)

    planner = TaskPlanner(backend="mock", semantic_map=sm)
    # 第一次规划
    plan1 = await planner.plan("拿起花")
    assert plan1.success

    # 模拟失败
    planner.record_failure(target="花", location="桌子", reason="not found")

    # 重规划，历史应出现在 prompt
    prompt = planner._build_prompt("拿起花")
    assert "失败" in prompt
    assert "花" in prompt
