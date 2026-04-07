# tests/test_full_integration.py
"""完整集成测试

测试 VLA Adapter + Skills + EventBus 的完整集成。
"""
import pytest
import asyncio
import numpy as np


class MockVLAAdapter:
    """模拟 VLA 适配器"""

    def __init__(self, action_dim=7):
        self.action_dim = action_dim
        self.call_count = 0

    def reset(self):
        pass

    def act(self, observation, skill_token, termination=None):
        self.call_count += 1
        return np.zeros(self.action_dim)

    def execute(self, action):
        return {"status": "executed", "action": action.tolist()}


@pytest.mark.asyncio
async def test_skill_chain_integration():
    """测试技能链集成"""
    from agents.skills.manipulation import GraspSkill, PlaceSkill, ReachSkill

    adapter = MockVLAAdapter()

    # 创建技能链
    reach = ReachSkill(target_position=[0.3, 0.0, 0.2], vla_adapter=adapter)
    grasp = GraspSkill(object_name="cube", vla_adapter=adapter)
    place = PlaceSkill(target_position=[0.5, 0.0, 0.1], vla_adapter=adapter)

    # 模拟观察
    observation_reaching = {
        "collision_detected": False,
        "position_reached": False,
        "distance_to_target": 0.1
    }

    observation_grasping = {
        "object_detected": True,
        "grasp_success": False
    }

    observation_placing = {
        "object_held": True,
        "placement_success": False
    }

    # 验证前置条件
    assert reach.check_preconditions(observation_reaching) is True
    assert grasp.check_preconditions(observation_grasping) is True
    assert place.check_preconditions(observation_placing) is True


@pytest.mark.asyncio
async def test_vla_adapter_selection():
    """测试 VLA 适配器选择"""
    from agents.clients.vla_adapters import LeRobotVLAAdapter, ACTVLAAdapter, GR00TVLAAdapter

    # LeRobot
    lerobot = LeRobotVLAAdapter(config={"action_dim": 7})
    assert lerobot.action_dim == 7

    # ACT
    act = ACTVLAAdapter(config={"action_dim": 7})
    assert act.action_dim == 7

    # GR00T
    gr00t = GR00TVLAAdapter(config={"action_dim": 7})
    assert gr00t.action_dim == 7


@pytest.mark.asyncio
async def test_event_bus_with_skills():
    """测试事件总线与技能集成"""
    from agents.events.bus import EventBus, Event
    from agents.skills.manipulation import GraspSkill

    bus = EventBus()
    events_received = []

    async def on_skill_started(event: Event):
        events_received.append(event)

    bus.subscribe("skill.started", on_skill_started)

    # 发布技能开始事件
    event = Event(
        type="skill.started",
        source="test",
        data={"skill": "grasp", "object": "cube"}
    )
    await bus.publish(event)

    assert len(events_received) == 1
    assert events_received[0].data["skill"] == "grasp"


@pytest.mark.asyncio
async def test_task_planner_with_skills():
    """测试任务规划与技能集成"""
    from agents.components.task_planner import TaskPlanner, PlanningStrategy
    from agents.skills.manipulation import GraspSkill, PlaceSkill, ReachSkill

    # 创建规划器
    planner = TaskPlanner(strategy=PlanningStrategy.RULE_BASED)

    # 规划任务
    task = planner.plan("抓取杯子放到桌子上")

    # 验证技能序列
    assert "reach" in task.skills
    assert "grasp" in task.skills
    assert "place" in task.skills


@pytest.mark.asyncio
async def test_multi_vla_coordination():
    """测试多 VLA 协调"""
    from agents.clients.vla_adapters import LeRobotVLAAdapter, ACTVLAAdapter

    # 创建两个不同类型的适配器
    lerobot = LeRobotVLAAdapter(config={"action_dim": 7})
    act = ACTVLAAdapter(config={"action_dim": 7})

    # 模拟观察
    observation = {
        "joint_positions": np.zeros(7),
        "joint_velocities": np.zeros(7)
    }

    # 两个适配器都可以处理相同的观察
    action1 = lerobot.act(observation, "reach")
    action2 = act.act(observation, "reach")

    assert action1.shape == (7,)
    assert action2.shape == (7,)


@pytest.mark.asyncio
async def test_skill_with_different_vlas():
    """测试同一技能使用不同 VLA"""
    from agents.skills.manipulation import GraspSkill
    from agents.clients.vla_adapters import LeRobotVLAAdapter, ACTVLAAdapter

    # LeRobot 适配器
    lerobot = LeRobotVLAAdapter(config={"action_dim": 7})
    skill1 = GraspSkill(object_name="cube", vla_adapter=lerobot)

    # ACT 适配器
    act = ACTVLAAdapter(config={"action_dim": 7})
    skill2 = GraspSkill(object_name="cube", vla_adapter=act)

    # 验证技能都可以构建 token
    assert skill1.build_skill_token() == "grasp(object=cube)"
    assert skill2.build_skill_token() == "grasp(object=cube)"

    # 验证前置条件检查相同
    observation = {"object_detected": True}
    assert skill1.check_preconditions(observation) is True
    assert skill2.check_preconditions(observation) is True


def test_skill_token_format_consistency():
    """测试技能令牌格式一致性"""
    from agents.skills.manipulation import GraspSkill, PlaceSkill, ReachSkill, MoveSkill, InspectSkill

    skills = [
        GraspSkill(object_name="cube"),
        PlaceSkill(target_position=[0.5, 0.0, 0.1]),
        ReachSkill(target_position=[0.3, 0.0, 0.2]),
        MoveSkill(target_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        InspectSkill(target_object="cube")
    ]

    for skill in skills:
        token = skill.build_skill_token()
        # 所有 token 应该是统一的格式
        assert "(" in token
        assert ")" in token
        assert "=" in token
