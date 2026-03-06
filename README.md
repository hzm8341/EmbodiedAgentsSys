# EmbodiedAgentsSys - Agent 数字员工框架

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/_static/EMBODIED_AGENTS_DARK.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/_static/EMBODIED_AGENTS_LIGHT.png">
  <img alt="EmbodiedAgentsSys Logo" src="docs/_static/EMBODIED_AGENTS_DARK.png" width="600">
</picture>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2](https://img.shields.io/badge/ROS2-Humble%2B-green)](https://docs.ros.org/en/humble/index.html)

**通用具身智能机器人框架 - 支持 VLA 模型的 Agent 数字员工系统**

[**安装**](#安装) | [**快速开始**](#快速开始) | [**功能列表**](#功能列表) | [**使用指南**](#使用指南)

</div>

---

## 概述

**EmbodiedAgentsSys** 是基于 ROS2 的通用具身智能机器人框架，支持 VLA (Vision-Language-Action) 模型的 Agent 数字员工系统。

### 核心特性

- **VLA 多模型支持**
  - LeRobot、ACT、GR00T 等多种 VLA 模型适配器
  - 统一的 VLA 接口设计，便于扩展新模型

- **丰富的 Skills 库**
  - 抓取、放置、到达、关节运动、检查等原子技能
  - 支持技能链编排和任务规划

- **事件驱动架构**
  - 异步非阻塞执行
  - 事件总线支持组件间松耦合通信

- **任务规划能力**
  - 基于规则的任务规划
  - LLM 驱动的智能任务分解

---

## 功能列表

### VLA 适配器

| 适配器 | 说明 | 状态 |
|--------|------|------|
| VLAAdapterBase | VLA 适配器基类 | ✅ |
| LeRobotVLAAdapter | LeRobot 框架适配器 | ✅ |
| ACTVLAAdapter | ACT (Action Chunking Transformer) 适配器 | ✅ |
| GR00TVLAAdapter | GR00T Diffusion Transformer 适配器 | ✅ |

### Skills

| Skill | 说明 | 状态 |
|-------|------|------|
| GraspSkill | 抓取技能 | ✅ |
| PlaceSkill | 放置技能 | ✅ |
| ReachSkill | 到达技能 | ✅ |
| MoveSkill | 关节运动技能 | ✅ |
| InspectSkill | 检查/识别技能 | ✅ |

### 组件

| 组件 | 说明 | 状态 |
|------|------|------|
| VoiceCommand | 语音命令理解 | ✅ |
| SemanticParser | 语义解析器 | ✅ |
| TaskPlanner | 任务规划器 | ✅ |
| EventBus | 事件总线 | ✅ |

### 工具

| 工具 | 说明 | 状态 |
|------|------|------|
| AsyncCache | 异步缓存 | ✅ |
| BatchProcessor | 批处理器 | ✅ |
| RateLimiter | 速率限制器 | ✅ |
| ForceController | 力控制器 | ✅ |

---

## 安装

### 1. 安装 ROS2 Humble

```bash
sudo apt install ros-humble-desktop
```

### 2. 安装 Sugarcoat 依赖

```bash
sudo apt install ros-humble-automatika-ros-sugar
```

或者从源码构建：

```bash
git clone https://github.com/automatika-robotics/sugarcoat
cd sugarcoat
pip install -e .
```

### 3. 安装 EmbodiedAgentsSys

```bash
pip install -e .
```

---

## 快速开始

### 创建 VLA 适配器

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter

# 创建 LeRobot 适配器
adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_...",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})

adapter.reset()
```

### 创建并执行 Skill

```python
import asyncio
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
result = asyncio.run(skill.execute(observation))

print(f"Status: {result.status}")
print(f"Output: {result.output}")
```

---

## 使用指南

### 1. VLA 适配器使用

#### LeRobot 适配器

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter

adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_sim_transfer_cube_human",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})

adapter.reset()

# 生成动作
observation = {
    "image": image_data,
    "joint_positions": joints
}
action = adapter.act(observation, "grasp(object=cube)")

# 执行动作
result = adapter.execute(action)
```

#### ACT 适配器

```python
from agents.clients.vla_adapters import ACTVLAAdapter

adapter = ACTVLAAdapter(config={
    "model_path": "/models/act",
    "chunk_size": 100,
    "horizon": 1,
    "action_dim": 7
})
```

#### GR00T 适配器

```python
from agents.clients.vla_adapters import GR00TVLAAdapter

adapter = GR00TVLAAdapter(config={
    "model_path": "/models/gr00t",
    "inference_steps": 10,
    "action_dim": 7,
    "action_horizon": 8
})
```

### 2. Skills 使用

#### GraspSkill - 抓取

```python
from agents.skills.manipulation import GraspSkill

skill = GraspSkill(
    object_name="cube",
    vla_adapter=adapter
)

# 检查前置条件
observation = {"object_detected": True}
if skill.check_preconditions(observation):
    result = asyncio.run(skill.execute(observation))
```

#### PlaceSkill - 放置

```python
from agents.skills.manipulation import PlaceSkill

skill = PlaceSkill(
    target_position=[0.5, 0.0, 0.1],  # x, y, z
    vla_adapter=adapter
)
```

#### ReachSkill - 到达

```python
from agents.skills.manipulation import ReachSkill

skill = ReachSkill(
    target_position=[0.3, 0.0, 0.2],
    vla_adapter=adapter
)
```

#### MoveSkill - 关节运动

```python
from agents.skills.manipulation import MoveSkill

# 关节模式
skill = MoveSkill(
    target_joints=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    vla_adapter=adapter
)

# 末端位姿模式
skill = MoveSkill(
    target_pose=[0.3, 0.0, 0.2, 0.0, 0.0, 0.0],  # x, y, z, roll, pitch, yaw
    vla_adapter=adapter
)
```

#### InspectSkill - 检查

```python
from agents.skills.manipulation import InspectSkill

skill = InspectSkill(
    target_object="cup",
    inspection_type="detect",  # detect/verify/quality
    vla_adapter=adapter
)
```

### 3. 技能链执行

```python
import asyncio
from agents.skills.manipulation import ReachSkill, GraspSkill, PlaceSkill

async def pick_and_place():
    adapter = LeRobotVLAAdapter(config={"action_dim": 7})

    # 创建技能链
    reach = ReachSkill(target_position=[0.3, 0.0, 0.2], vla_adapter=adapter)
    grasp = GraspSkill(object_name="cube", vla_adapter=adapter)
    place = PlaceSkill(target_position=[0.5, 0.0, 0.1], vla_adapter=adapter)

    # 依次执行
    observation = await get_observation()

    await reach.execute(observation)
    await grasp.execute(observation)
    await place.execute(observation)

asyncio.run(pick_and_place())
```

### 4. 事件总线使用

```python
from agents.events.bus import EventBus, Event

bus = EventBus()

async def on_skill_started(event: Event):
    print(f"Skill started: {event.data}")

# 订阅事件
bus.subscribe("skill.started", on_skill_started)

# 发布事件
await bus.publish(Event(
    type="skill.started",
    source="agent",
    data={"skill": "grasp", "object": "cube"}
))
```

### 5. 任务规划使用

```python
from agents.components.task_planner import TaskPlanner, PlanningStrategy

# 创建规划器（基于规则）
planner = TaskPlanner(strategy=PlanningStrategy.RULE_BASED)

# 规划任务
task = planner.plan("抓取杯子放到桌子上")

print(f"Task: {task.name}")
print(f"Skills: {task.skills}")
# Output: ['reach', 'grasp', 'reach', 'place']
```

### 6. 语义解析使用

```python
from agents.components.semantic_parser import SemanticParser

parser = SemanticParser()

# 解析运动指令
result = parser.parse("向前20厘米")
# {'intent': 'motion', 'direction': 'forward', 'distance': 0.2}

# 解析抓取指令
result = parser.parse("抓取杯子")
# {'intent': 'grasp'}

# 解析放置指令
result = parser.parse("放到桌子上")
# {'intent': 'place'}
```

### 7. 力控模块使用

```python
from skills.force_control import ForceController, ForceControlMode

controller = ForceController(
    max_force=10.0,
    contact_threshold=0.5
)

# 设置力控模式
controller.set_mode(ForceControlMode.FORCE)

# 施加力
target_force = np.array([0.0, 0.0, -5.0])
result = await controller.execute(target_force)
```

### 8. 性能优化工具

#### 异步缓存

```python
from agents.utils.performance import AsyncCache, get_cache

cache = get_cache(ttl_seconds=60)

@cache.cached
async def expensive_operation(data):
    # 耗时操作
    return result
```

#### 批处理器

```python
from agents.utils.performance import BatchProcessor

processor = BatchProcessor(batch_size=10, timeout=0.1)

async def handler(items):
    # 批量处理
    return [process(item) for item in items]

# 启动处理
asyncio.create_task(processor.process(handler))

# 添加任务
result = await processor.add(item)
```

---

## 配置文件

### VLA 配置 (config/vla_config.yaml)

```yaml
lerobot:
  policy_name: "default_policy"
  checkpoint: null
  host: "127.0.0.1"
  port: 8080
  action_dim: 7

vla_type: "lerobot"

skills:
  max_retries: 3
  observation_timeout: 5.0
```

---

## 项目结构

```
agents/
├── clients/
│   └── vla_adapters/      # VLA 适配器
│       ├── base.py
│       ├── lerobot.py
│       ├── act.py
│       └── gr00t.py
├── components/            # 组件
│   ├── voice_command.py
│   ├── semantic_parser.py
│   └── task_planner.py
├── skills/
│   ├── vla_skill.py      # Skill 基类
│   └── manipulation/      # 操作技能
│       ├── grasp.py
│       ├── place.py
│       ├── reach.py
│       ├── move.py
│       └── inspect.py
├── events/               # 事件系统
│   └── bus.py
└── utils/               # 工具类
    └── performance.py

skills/
├── force_control/       # 力控模块
│   └── force_control.py
└── vision/             # 视觉技能
    └── perception_skill.py

tests/                   # 测试
docs/
├── api/                 # API 文档
└── guides/              # 使用指南
```

---

## 相关文档

- [VLA 适配器 API](docs/api/vla_adapter.md)
- [Skills API](docs/api/skills.md)
- [使用指南](docs/guides/getting_started.md)
- [整合方案](docs/integration_plan_v1.0_20260303_AI.md)

---

## 许可证

MIT License - Copyright (c) 2024-2026

---

## 联系方式

- GitHub: https://github.com/hzm8341/EmbodiedAgentsSys
- 文档: https://automatika-robotics.github.io/embodied-agents/
