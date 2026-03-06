# Agent 数字员工框架 - 使用指南

## 快速开始

### 1. 安装依赖

```bash
# 安装 ROS2 Humble
sudo apt install ros-humble-automatika-ros-sugar

# 安装框架
pip install -e .
```

### 2. 创建 VLA 适配器

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter

# 创建适配器
adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_...",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})

adapter.reset()
```

### 3. 创建并执行 Skill

```python
from agents.skills.manipulation import GraspSkill

# 创建抓取技能
skill = GraspSkill(
    object_name="cube",
    vla_adapter=adapter
)

# 准备观察数据
observation = {
    "object_detected": True,
    "grasp_success": False
}

# 执行技能
import asyncio
result = asyncio.run(skill.execute(observation))

print(f"Status: {result.status}")
print(f"Output: {result.output}")
```

## 技能链执行

```python
from agents.skills.manipulation import ReachSkill, GraspSkill, PlaceSkill

async def pick_and_place():
    # 创建技能
    reach = ReachSkill(target_position=[0.3, 0.0, 0.2], vla_adapter=adapter)
    grasp = GraspSkill(object_name="cube", vla_adapter=adapter)
    place = PlaceSkill(target_position=[0.5, 0.0, 0.1], vla_adapter=adapter)

    # 执行技能链
    observation = await get_observation()

    result1 = await reach.execute(observation)
    result2 = await grasp.execute(observation)
    result3 = await place.execute(observation)

    return result3

asyncio.run(pick_and_place())
```

## 事件驱动

```python
from agents.events.bus import EventBus, Event

bus = EventBus()

async def on_skill_started(event: Event):
    print(f"Skill started: {event.data}")

bus.subscribe("skill.started", on_skill_started)

# 发布事件
await bus.publish(Event(
    type="skill.started",
    source="agent",
    data={"skill": "grasp", "object": "cube"}
))
```

## 任务规划

```python
from agents.components.task_planner import TaskPlanner, PlanningStrategy

# 创建规划器
planner = TaskPlanner(strategy=PlanningStrategy.RULE_BASED)

# 规划任务
task = planner.plan("抓取杯子放到桌子上")

print(f"Task: {task.name}")
print(f"Skills: {task.skills}")
# Output: ['reach', 'grasp', 'reach', 'place']
```

## 配置

```yaml
# config/vla_config.yaml
lerobot:
  policy_name: "panda_policy"
  checkpoint: null
  host: "127.0.0.1"
  port: 8080
  action_dim: 7

skills:
  max_retries: 3
  observation_timeout: 5.0
```
