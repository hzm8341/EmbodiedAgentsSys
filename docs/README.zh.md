# EmbodiedAgentsSys - 智能体数字员工框架

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="_static/EMBODIED_AGENTS_DARK.png">
  <source media="(prefers-color-scheme: light)" srcset="_static/EMBODIED_AGENTS_LIGHT.png">
  <img alt="EmbodiedAgentsSys Logo" src="_static/EMBODIED_AGENTS_DARK.png" width="600">
</picture>

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2](https://img.shields.io/badge/ROS2-Humble%2B-green)](https://docs.ros.org/en/humble/index.html)

**通用具身智能机器人框架 - 支持VLA模型的智能体数字员工系统**

[**安装**](#安装) | [**快速开始**](#快速开始) | [**功能列表**](#功能列表) | [**使用指南**](#使用指南)

</div>

---

## 概述

**EmbodiedAgentsSys** 是基于ROS2的通用具身智能机器人框架，支持VLA（Vision-Language-Action）模型的智能体数字员工系统。

### 核心特性

- **VLA多模型支持**
  - 适配器支持LeRobot、ACT、GR00T等多种VLA模型
  - 统一的VLA接口设计，便于扩展新模型

- **丰富的Skills库**
  - 原子技能：抓取、放置、到达、关节运动、检查
  - 支持技能链编排和任务规划

- **事件驱动架构**
  - 异步非阻塞执行
  - 事件总线支持组件间松耦合通信

- **任务规划能力**
  - 基于规则的任务规划
  - LLM驱动的智能任务分解

- **核心执行闭环（Phase 1）**
  - 硬件抽象层：统一机械臂接口 + 多厂商适配器
  - 技能注册表 + 能力缺口检测（YAML驱动）
  - 场景规格说明 + 语音交互填充
  - 双格式执行计划（YAML机器可读 + Markdown人类可读）
  - 失败数据自动记录 + 训练脚本自动生成

---

## 功能列表

### VLA适配器

| 适配器 | 说明 | 状态 |
|--------|------|------|
| VLAAdapterBase | VLA适配器基类 | ✅ |
| LeRobotVLAAdapter | LeRobot框架适配器 | ✅ |
| ACTVLAAdapter | ACT（Action Chunking Transformer）适配器 | ✅ |
| GR00TVLAAdapter | GR00T Diffusion Transformer适配器 | ✅ |

### Skills

| 技能 | 说明 | 状态 |
|------|------|------|
| GraspSkill | 抓取技能 | ✅ |
| PlaceSkill | 放置技能 | ✅ |
| ReachSkill | 到达技能 | ✅ |
| MoveSkill | 关节运动技能 | ✅ |
| InspectSkill | 检查/识别技能 | ✅ |
| AssemblySkill | 装配技能 | ✅ |
| Perception3DSkill | 3D感知技能 | ✅ |

### 组件

| 组件 | 说明 | 状态 |
|------|------|------|
| VoiceCommand | 语音命令理解 | ✅ |
| SemanticParser | 语义解析器（LLM增强） | ✅ |
| TaskPlanner | 任务规划器（带执行记忆） | ✅ |
| EventBus | 事件总线 | ✅ |
| DistributedEventBus | 分布式事件总线 | ✅ |
| SkillGenerator | Skill代码生成器 | ✅ |

### 工具

| 工具 | 说明 | 状态 |
|------|------|------|
| AsyncCache | 异步缓存 | ✅ |
| BatchProcessor | 批处理器 | ✅ |
| RateLimiter | 速率限制器 | ✅ |
| ForceController | 力控制器 | ✅ |

### 硬件抽象层（Phase 1）

| 模块 | 说明 | 状态 |
|------|------|------|
| ArmAdapter | 机械臂抽象基类（ABC），定义`move_to_pose` / `move_joints` / `set_gripper`等统一接口 | ✅ |
| AGXArmAdapter | AGX机械臂适配器（异步，支持mock模式） | ✅ |
| LeRobotArmAdapter | LeRobot机械臂适配器（复用LeRobotClient） | ✅ |
| RobotCapabilityRegistry | YAML驱动的技能注册表，支持按`robot_type`查询能力，返回`GapType`枚举 | ✅ |
| GapDetectionEngine | 对执行计划步骤做hard-gap分类标注，输出`GapReport` | ✅ |

### 规划层扩展（Phase 1）

| 模块 | 说明 | 状态 |
|------|------|------|
| SceneSpec | 结构化场景描述dataclass，支持YAML序列化/反序列化 | ✅ |
| PlanGenerator | 封装TaskPlanner，将flat action映射为dot-notation技能名，输出YAML + Markdown双格式执行计划 | ✅ |
| VoiceTemplateAgent | 引导式语音Q&A，逐步填充SceneSpec字段 | ✅ |

### 数据与训练（Phase 1）

| 模块 | 说明 | 状态 |
|------|------|------|
| FailureDataRecorder | 失败时自动保存`metadata.json` + `scene_spec.yaml` + `plan.yaml` | ✅ |
| TrainingScriptGenerator | 根据能力缺口生成数据集需求报告和bash训练脚本 | ✅ |

---

## 安装

### 1. 安装ROS2 Humble

```bash
sudo apt install ros-humble-desktop
```

### 2. 安装Sugarcoat依赖

```bash
sudo apt install ros-humble-automatika-ros-sugar
```

或者从源码构建：

```bash
git clone https://github.com/automatika-robotics/sugarcoat
cd sugarcoat
pip install -e .
```

### 3. 安装EmbodiedAgentsSys

```bash
pip install -e .
```

---

## 快速开始

### 创建VLA适配器

```python
from agents.clients.vla_adapters import LeRobotVLAAdapter

# 创建LeRobot适配器
adapter = LeRobotVLAAdapter(config={
    "policy_name": "panda_policy",
    "checkpoint": "lerobot/act_...",
    "host": "127.0.0.1",
    "port": 8080,
    "action_dim": 7
})

adapter.reset()
```

### 创建并执行Skill

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

### 1. VLA适配器使用

#### LeRobot适配器

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

#### ACT适配器

```python
from agents.clients.vla_adapters import ACTVLAAdapter

adapter = ACTVLAAdapter(config={
    "model_path": "/models/act",
    "chunk_size": 100,
    "horizon": 1,
    "action_dim": 7
})
```

#### GR00T适配器

```python
from agents.clients.vla_adapters import GR00TVLAAdapter

adapter = GR00TVLAAdapter(config={
    "model_path": "/models/gr00t",
    "inference_steps": 10,
    "action_dim": 7,
    "action_horizon": 8
})
```

### 2. Skills使用

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
# 输出: ['reach', 'grasp', 'reach', 'place']
```

### 6. 语义解析使用

```python
from agents.components.semantic_parser import SemanticParser

# 使用LLM增强解析
parser = SemanticParser(use_llm=True, ollama_model="qwen2.5:3b")

# 同步解析（规则模式）
result = parser.parse("向前20厘米")
# {'intent': 'motion', 'direction': 'forward', 'distance': 0.2}

# 异步解析（LLM模式）
result = await parser.parse_async("帮我把那个圆形零件移过去")
# {'intent': 'motion', 'params': {'direction': 'forward', ...}}
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

### 9. SkillGenerator使用

```python
from skills.teaching.skill_generator import SkillGenerator

generator = SkillGenerator(output_dir="./generated_skills", _simulated=False)

# 从示教动作生成Skill
teaching_action = {
    "action_id": "demo_001",
    "name": "pick_and_place",
    "frames": [
        {"joint_positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
        {"joint_positions": [0.5, 0.2, 0.1, 0.0, 0.0, 0.0, 0.0]},
    ]
}

result = await generator.generate_skill(
    teaching_action=teaching_action,
    skill_name="demo_pick_place"
)

# 导出到文件
export_result = await generator.export_skill(result["skill_id"])
# 生成可执行的Python文件
```

### 10. Phase 1核心执行闭环

#### 场景描述+语音交互填充

```python
import asyncio
from agents.components.scene_spec import SceneSpec
from agents.components.voice_template_agent import VoiceTemplateAgent

# 方式一：直接构建SceneSpec
scene = SceneSpec(
    task_description="将红色零件从A区搬运到B区",
    robot_type="arm",
    objects=["red_part"],
    target_positions={"red_part": [0.5, 0.2, 0.1]},
)

# 方式二：引导式语音交互填充
agent = VoiceTemplateAgent()
scene = asyncio.run(agent.interactive_fill())
```

#### 生成执行计划（YAML + Markdown双格式）

```python
from agents.components.plan_generator import PlanGenerator

generator = PlanGenerator(backend="mock")  # backend="ollama"使用LLM
plan = asyncio.run(generator.generate(scene))

print(plan.yaml_content)    # YAML执行计划（机器可读）
print(plan.markdown_report) # Markdown报告（人类可读）
print(plan.steps)           # 步骤列表，每步含dot-notation技能名
# 例: [{'action': 'manipulation.grasp', 'object': 'red_part', ...}]
```

#### 技能注册表+能力缺口检测

```python
from agents.hardware.capability_registry import RobotCapabilityRegistry, GapType
from agents.hardware.gap_detector import GapDetectionEngine

registry = RobotCapabilityRegistry()

# 查询单个技能
result = registry.query("manipulation.grasp", robot_type="arm")
print(result.gap_type)  # GapType.NONE — 支持

result = registry.query("navigation.goto", robot_type="arm")
print(result.gap_type)  # GapType.HARD — 不支持

# 对计划步骤批量检测缺口
engine = GapDetectionEngine(registry)
report = engine.detect(plan.steps, robot_type="arm")
print(report.has_gaps)        # True/False
print(report.gap_steps)       # 有缺口的步骤列表
annotated = engine.annotate_steps(plan.steps, robot_type="arm")
# 每步新增status: "pending"或"gap"
```

#### 失败数据记录+训练脚本生成

```python
from agents.data.failure_recorder import FailureDataRecorder
from agents.training.script_generator import TrainingScriptGenerator

# 执行失败时保存现场数据
recorder = FailureDataRecorder(base_dir="./failure_data")
record_path = asyncio.run(recorder.record(
    scene=scene,
    plan=plan,
    error="manipulation.grasp执行超时",
))
# 保存：failure_data/<timestamp>/metadata.json + scene_spec.yaml + plan.yaml

# 根据能力缺口生成训练脚本
generator = TrainingScriptGenerator()
config = generator.generate_config(gap_report=report, scene=scene)
script = generator.generate_script(config)
print(script)  # bash训练脚本内容
req_report = generator.generate_requirements_report(config)
print(req_report)  # 数据集需求报告（Markdown）
```

#### 使用机械臂适配器

```python
from agents.hardware.agx_arm_adapter import AGXArmAdapter
from agents.hardware.arm_adapter import Pose6D

# 创建适配器（mock=True用于测试，不需要真实硬件）
arm = AGXArmAdapter(host="192.168.1.100", mock=True)
asyncio.run(arm.connect())

# 检查就绪
ready = asyncio.run(arm.is_ready())

# 移动到目标位姿
pose = Pose6D(x=0.3, y=0.0, z=0.2, roll=0.0, pitch=0.0, yaw=0.0)
success = asyncio.run(arm.move_to_pose(pose, speed=0.1))

# 控制夹爪
asyncio.run(arm.set_gripper(opening=0.8, force=5.0))

# 查询能力
caps = arm.get_capabilities()
print(caps.robot_type)   # "arm"
print(caps.skill_ids)    # ["manipulation.grasp", "manipulation.place", ...]
```

### 11. 分布式事件总线（多机器人协作）

```python
from agents.events.bus import DistributedEventBus

# 创建分布式事件总线（需要ROS2节点）
bus = DistributedEventBus(ros_node=my_ros_node, namespace="/robots/events")

# 订阅事件
async def on_robot_status(event):
    print(f"Robot status: {event.data}")

bus.subscribe("robot.status", on_robot_status)

# 发布事件（自动广播到其他ROS2节点）
await bus.publish(Event(
    type="robot.status",
    source="robot_1",
    data={"status": "working", "battery": 85}
))
```

---

## 配置文件

### VLA配置（config/vla_config.yaml）

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
│   ├── vla_adapters/          # VLA适配器
│   │   ├── base.py
│   │   ├── lerobot.py
│   │   ├── act.py
│   │   └── gr00t.py
│   └── ollama.py              # Ollama LLM客户端
├── components/                # 组件
│   ├── voice_command.py
│   ├── semantic_parser.py
│   ├── task_planner.py        # 含_SKILL_NAMESPACE_MAP
│   ├── scene_spec.py          # [Phase 1] 场景规格说明dataclass
│   ├── plan_generator.py      # [Phase 1] 双格式执行计划生成器
│   └── voice_template_agent.py# [Phase 1] 引导式语音交互填充
├── hardware/                  # [Phase 1] 硬件抽象层
│   ├── arm_adapter.py         # ArmAdapter ABC + Pose6D / RobotState / RobotCapabilities
│   ├── agx_arm_adapter.py     # AGX机械臂适配器
│   ├── lerobot_arm_adapter.py # LeRobot机械臂适配器
│   ├── capability_registry.py # RobotCapabilityRegistry + GapType枚举
│   ├── gap_detector.py        # GapDetectionEngine
│   └── skills_registry.yaml   # 技能注册表（9个技能）
├── data/                      # [Phase 1] 数据层
│   └── failure_recorder.py    # 失败数据自动记录
├── training/                  # [Phase 1] 训练层
│   └── script_generator.py    # 训练脚本 + 数据集需求报告生成
├── skills/
│   ├── vla_skill.py           # Skill基类
│   └── manipulation/          # 操作技能
│       ├── grasp.py
│       ├── place.py
│       ├── reach.py
│       ├── move.py
│       └── inspect.py
├── events/                    # 事件系统
│   └── bus.py                 # EventBus + DistributedEventBus
└── utils/                     # 工具类
    └── performance.py

skills/
├── force_control/             # 力控模块
│   └── force_control.py
├── vision/                    # 视觉技能
│   └── perception_3d_skill.py
└── teaching/                  # 示教模块
    └── skill_generator.py

tests/                         # 测试（57个用例）
docs/
├── api/                       # API文档
├── guides/                    # 使用指南
└── plans/                     # 开发计划
```

---

## Web前端仪表盘

Agent Dashboard提供实时摄像头预览、场景描述和目标检测功能，基于React + FastAPI构建，使用本地Ollama `qwen2.5vl`视觉模型进行推理。

### 演示效果

<div align="center">
<img src="_static/dashboard_demo_1.png" alt="场景分析面板 - 场景描述与物体检测" width="800"/>
<p><em>场景分析面板：实时画面预览 + qwen2.5vl场景描述 + 目标检测置信度</em></p>

<img src="_static/dashboard_demo_2.png" alt="场景分析面板 - 多物体检测结果" width="800"/>
<p><em>检测结果：自动识别办公桌面上的电脑显示器、文件夹、电脑等物体</em></p>
</div>

### 前置条件

- USB摄像头已连接（默认`/dev/video0`）
- Ollama已安装并拉取视觉模型：
  ```bash
  ollama pull qwen2.5vl
  ```
- Python依赖：
  ```bash
  pip install fastapi uvicorn opencv-python ollama
  ```
- Node.js依赖（首次运行）：
  ```bash
  cd web-dashboard && npm install
  ```

### 启动方式

**终端1 — 后端**（接入USB摄像头 + qwen2.5vl推理）：

```bash
cd /path/to/EmbodiedAgentsSys
python examples/agent_dashboard_backend.py
# 后端运行在 http://localhost:8000
```

**终端2 — 前端**（React开发服务器）：

```bash
cd web-dashboard
npx vite
# 前端运行在 http://localhost:5173
```

浏览器打开`http://localhost:5173`

### 功能页面

| 侧边栏 | 功能 |
|--------|------|
| **相机** | 实时画面预览（~10 fps），开始/停止按钮 |
| **场景分析** | 实时预览 + 点击"场景分析"调用qwen2.5vl，返回场景文字描述和物体列表 |
| **检测** | 以表格展示当前画面检测到的物体和置信度 |
| **对话** | 与后端Agent进行文本交互 |

### API接口

后端提供以下REST接口（端口8000）：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/camera/frame` | 获取当前帧（base64 JPEG） |
| POST | `/api/scene/describe` | 触发qwen2.5vl场景理解，返回描述和物体列表 |
| GET | `/api/detection/result` | 获取最新目标检测结果 |
| GET | `/healthz` | 健康检查 |

---

## 相关文档

- [VLA适配器API](docs/api/vla_adapter.md)
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
