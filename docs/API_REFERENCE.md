# EmbodiedAgentsSys API 参考文档

**版本**: 1.0.0
**最后更新**: 2026-04-04

---

## 目录

1. [核心类型](#核心类型)
2. [代理循环](#代理循环)
3. [配置管理](#配置管理)
4. [认知层](#认知层)
5. [反馈系统](#反馈系统)
6. [执行工具](#执行工具)
7. [扩展插件](#扩展插件)
8. [简化接口](#简化接口)

---

## 核心类型

### RobotObservation

机器人观察数据结构。

```python
from agents import RobotObservation

# 创建观察
obs = RobotObservation(
    image=np.array([...]),      # 图像数据
    state={"joint_angles": [...]},  # 关节状态
    gripper_position=0.5,        # 机械爪位置
)
```

**属性**：
- `image`: 观察图像数据（可选）
- `state`: 机器人状态字典（可选）
- `gripper_position`: 机械爪位置（0.0-1.0）
- `timestamp`: 观察时间戳（自动生成）

---

### SkillResult

技能执行结果。

```python
from agents import SkillResult

# 成功结果
result = SkillResult(
    success=True,
    message="Task completed successfully",
    data={"key": "value"}
)

# 失败结果
result = SkillResult(
    success=False,
    message="Task failed due to collision",
    error="CollisionError"
)
```

**属性**：
- `success`: 执行是否成功（布尔值）
- `message`: 结果信息（字符串）
- `data`: 结果数据（可选字典）
- `error`: 错误类型（失败时可选）

---

### AgentConfig

代理配置。

```python
from agents import AgentConfig

config = AgentConfig(
    agent_name="my_robot",      # 代理名称
    max_steps=100,              # 最大步数
    llm_model="qwen",           # LLM 模型
    perception_enabled=True,    # 是否启用感知
)
```

**属性**：
- `agent_name`: 代理名称（必需）
- `max_steps`: 最大执行步数（默认 100，>= 1）
- `llm_model`: LLM 模型名称（默认 "qwen"）
- `perception_enabled`: 是否启用感知（默认 True）

---

## 代理循环

### RobotAgentLoop

核心代理循环，实现 observe-think-act 流程。

```python
from agents import RobotAgentLoop, AgentConfig

config = AgentConfig(agent_name="robot")

loop = RobotAgentLoop(
    llm_provider=llm_provider,
    perception_provider=perception_provider,
    executor=executor,
    config=config
)

# 执行单步
result = await loop.step()
```

**方法**：
- `async step() -> SkillResult`：执行单步循环
  - 获取观察
  - 生成动作
  - 执行动作
  - 返回结果

**属性**：
- `step_count`: 当前步数
- `config`: 代理配置

---

## 配置管理

### ConfigManager

统一配置管理。

```python
from agents import ConfigManager

# 创建默认配置
config = ConfigManager.create(agent_name="robot")

# 加载预设配置
config = ConfigManager.load_preset("default")

# 从 YAML 加载
config = ConfigManager.load_yaml("config.yaml")
```

**方法**：
- `ConfigManager.create(**kwargs) -> AgentConfig`：创建配置
- `ConfigManager.load_preset(name: str) -> AgentConfig`：加载预设
- `ConfigManager.load_yaml(path: str) -> AgentConfig`：从 YAML 加载

**预设**：
- `"default"`：默认配置
- `"vla_plus"`：VLA+ 模型配置

---

## 认知层

### PlanningLayerBase 和 DefaultPlanningLayer

规划层：任务 → 计划。

```python
from agents import DefaultPlanningLayer

layer = DefaultPlanningLayer()
plan = await layer.generate_plan("pick up the red ball")
```

**方法**：
- `async generate_plan(task: str) -> dict`：生成任务计划

---

### ReasoningLayerBase 和 DefaultReasoningLayer

推理层：计划 + 观察 → 动作。

```python
from agents import DefaultReasoningLayer

layer = DefaultReasoningLayer()
action = await layer.generate_action(plan, observation)
```

**方法**：
- `async generate_action(plan: dict, observation) -> str`：生成动作

---

### LearningLayerBase 和 DefaultLearningLayer

学习层：反馈 → 改进。

```python
from agents import DefaultLearningLayer

layer = DefaultLearningLayer()
improved_action = await layer.improve(action, feedback)
```

**方法**：
- `async improve(action: str, feedback: dict) -> str`：改进动作

---

### CognitionEngine

认知引擎，集成三层。

```python
from agents import CognitionEngine, AgentConfig

config = AgentConfig(agent_name="robot")
engine = CognitionEngine(config)

# 思考
result = await engine.think(task="pick up object")

# 提供反馈
await engine.provide_feedback(result, feedback_data)
```

**方法**：
- `async think(task: str) -> dict`：认知处理
- `async provide_feedback(result, feedback) -> None`：提供反馈

---

## 反馈系统

### FeedbackLogger

反馈记录。

```python
from agents import FeedbackLogger

logger = FeedbackLogger()
logger.log_result(result, metadata={"task": "pick"})
```

**方法**：
- `log_result(result, metadata=None)`：记录结果

---

### FeedbackAnalyzer

反馈分析。

```python
from agents import FeedbackAnalyzer

analyzer = FeedbackAnalyzer()
insights = analyzer.analyze_results(results)
```

**方法**：
- `analyze_results(results) -> dict`：分析结果

---

### FeedbackLoop

反馈循环，集成记录和分析。

```python
from agents import FeedbackLoop

loop = FeedbackLoop()

# 接收反馈
await loop.receive_feedback(result)

# 获取洞察
insights = loop.get_insights()
```

**方法**：
- `async receive_feedback(result)`：接收反馈
- `get_insights() -> dict`：获取洞察

---

## 执行工具

### ToolBase

工具基类。

```python
from agents.execution.tools import ToolBase

class CustomTool(ToolBase):
    name = "custom"
    description = "Custom tool"
    keywords = ["custom", "tool"]

    async def execute(self, **kwargs) -> dict:
        # 实现工具逻辑
        return {"success": True}
```

**方法**：
- `async execute(**kwargs) -> dict`：执行工具
- `async validate(**kwargs) -> bool`：验证参数
- `async cleanup()`：清理资源

---

### GripperTool

机械爪控制工具。

```python
from agents import GripperTool

tool = GripperTool()

# 打开
result = await tool.execute(action="open")

# 关闭
result = await tool.execute(action="close")

# 抓取
result = await tool.execute(action="grasp", force=0.8)
```

**参数**：
- `action`：动作（'open', 'close', 'grasp'）
- `force`：夹持力度（0.0-1.0，默认 1.0）

---

### MoveTool

移动规划工具。

```python
from agents import MoveTool

tool = MoveTool()

# 直接移动
result = await tool.execute(
    target={"x": 0.5, "y": 0.3, "z": 0.2},
    mode="direct"
)

# 相对移动
result = await tool.execute(
    target={"x": 0.1, "y": -0.05, "z": 0.02},
    mode="relative"
)
```

**参数**：
- `target`：目标位置（字典或轨迹）
- `mode`：移动模式（'direct', 'relative', 'safe', 'trajectory'）

---

### VisionTool

视觉处理工具。

```python
from agents import VisionTool

tool = VisionTool()

# 对象检测
result = await tool.execute(operation="detect_objects")

# 图像分割
result = await tool.execute(operation="segment")

# 姿态估计
result = await tool.execute(operation="estimate_pose")

# 相机标定
result = await tool.execute(operation="calibrate")
```

**操作**：
- `detect_objects`：检测对象
- `segment`：图像分割
- `estimate_pose`：姿态估计
- `calibrate`：相机标定

---

### ToolRegistry

工具注册表。

```python
from agents import ToolRegistry, GripperTool

registry = ToolRegistry()
registry.register("gripper", GripperTool())

# 检索
tool = registry.get("gripper")

# 列表
tools = registry.list_tools()

# 注销
registry.unregister("gripper")
```

**方法**：
- `register(name, tool)`：注册工具
- `get(name) -> ToolBase`：获取工具
- `list_tools() -> List[str]`：列表工具
- `unregister(name)`：注销工具

---

### StrategySelector

策略选择器。

```python
from agents import StrategySelector, ToolRegistry

selector = StrategySelector(registry)

# 按名称选择
tool = selector.select_tool("gripper")

# 按关键词选择
tool = selector.find_tool_by_keyword("grasp")

# 为任务排名
ranked = selector.rank_tools_for_task("pick up object")
best = selector.find_best_tool("pick up object")
```

**方法**：
- `select_tool(name) -> ToolBase`：按名称选择
- `find_tool_by_keyword(keyword) -> ToolBase`：按关键词选择
- `rank_tools_for_task(description) -> List[ToolBase]`：为任务排名
- `find_best_tool(description) -> ToolBase`：找最佳工具

---

## 扩展插件

### PluginBase

插件基类。

```python
from agents.extensions.plugin import PluginBase

class CustomPlugin(PluginBase):
    name = "custom"
    version = "1.0.0"
    description = "Custom plugin"

    async def initialize(self, config=None):
        # 初始化
        pass

    async def execute(self, **kwargs) -> dict:
        # 执行
        return {"success": True}

    async def cleanup(self):
        # 清理
        pass
```

**方法**：
- `async initialize(config=None)`：初始化
- `async execute(**kwargs) -> dict`：执行
- `async cleanup()`：清理资源

---

### PreprocessorPlugin

数据预处理插件。

```python
from agents import PreprocessorPlugin

plugin = PreprocessorPlugin()
await plugin.initialize()

# 数据清理
result = await plugin.execute(operation="clean", data=data)

# 数据标准化
result = await plugin.execute(operation="normalize", data=data)

# 数据验证
result = await plugin.execute(operation="validate", data=data)
```

**操作**：
- `clean`：数据清理
- `normalize`：数据标准化
- `validate`：数据验证

---

### PostprocessorPlugin

结果后处理插件。

```python
from agents import PostprocessorPlugin

plugin = PostprocessorPlugin()
await plugin.initialize()

# 结果格式化
result = await plugin.execute(operation="format", data=data)

# 结果聚合
result = await plugin.execute(operation="aggregate", data=data)

# 置信度过滤
result = await plugin.execute(operation="filter", data=data, threshold=0.8)
```

---

### VisualizationPlugin

数据可视化插件。

```python
from agents import VisualizationPlugin

plugin = VisualizationPlugin()
await plugin.initialize()

# 生成图表
result = await plugin.execute(operation="generate_chart", data=[1,2,3,4,5])

# 统计分析
result = await plugin.execute(operation="statistics", data=[1,2,3,4,5])

# 导出
result = await plugin.execute(operation="export", data=data, format="json")
```

---

## 简化接口

### SimpleAgent

一行代码创建代理的简化接口。

```python
from agents import SimpleAgent

# 从预设创建
agent = SimpleAgent.from_preset("default")

# 执行任务
result = await agent.run_task("pick up the red ball")
```

**方法**：
- `SimpleAgent.from_preset(name: str) -> SimpleAgent`：从预设创建
- `async run_task(task: str) -> SkillResult`：执行任务

---

## 完整示例

```python
from agents import (
    SimpleAgent,
    ToolRegistry, StrategySelector,
    PluginRegistry,
    PreprocessorPlugin, PostprocessorPlugin, VisualizationPlugin,
)

# 1. 创建代理
agent = SimpleAgent.from_preset("default")

# 2. 注册工具
tool_registry = ToolRegistry()
tool_registry.register("gripper", GripperTool())
tool_registry.register("move", MoveTool())
selector = StrategySelector(tool_registry)

# 3. 注册插件
plugin_registry = PluginRegistry()
prep = PreprocessorPlugin()
await prep.initialize()
plugin_registry.register("preprocessor", prep)

# 4. 执行任务
result = await agent.run_task("pick up the red ball")

# 5. 后处理
post = PostprocessorPlugin()
await post.initialize()
processed = await post.execute(operation="format", data=result)

# 6. 可视化
viz = VisualizationPlugin()
await viz.initialize()
report = await viz.execute(operation="generate_chart", data=[...])
```

---

*生成于 2026-04-04*
