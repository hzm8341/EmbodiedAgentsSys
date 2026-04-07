# EmbodiedAgentsSys 用户指南

**版本**: 1.0.0
**最后更新**: 2026-04-04

---

## 目录

1. [快速开始](#快速开始)
2. [基本概念](#基本概念)
3. [常见任务](#常见任务)
4. [配置指南](#配置指南)
5. [最佳实践](#最佳实践)
6. [故障排查](#故障排查)

---

## 快速开始

### 安装和导入

```python
# 导入核心代理接口
from agents import SimpleAgent

# 从预设创建代理
agent = SimpleAgent.from_preset("default")

# 执行任务
result = await agent.run_task("pick up the red ball")
```

### 一分钟示例

```python
import asyncio
from agents import SimpleAgent

async def main():
    # 创建代理
    agent = SimpleAgent.from_preset("default")

    # 执行任务
    result = await agent.run_task("place the cube on the table")

    # 检查结果
    if result.success:
        print(f"任务成功: {result.message}")
    else:
        print(f"任务失败: {result.error}")

asyncio.run(main())
```

---

## 基本概念

### 代理 (Agent)

代理是执行机器人任务的核心单位。它包含：
- **感知层**: 接收机器人观察数据
- **认知层**: 规划任务和推理决策
- **执行层**: 控制机器人执行动作
- **反馈层**: 记录和学习执行结果

### 观察 (RobotObservation)

机器人观察包含：
- 图像数据 (image)
- 状态信息 (state dict)
- 机械爪位置 (gripper_position)
- 时间戳 (自动生成)

```python
from agents import RobotObservation
import numpy as np

obs = RobotObservation(
    image=np.zeros((480, 640, 3), dtype=np.uint8),
    state={"joint_angles": [0.1, 0.2, 0.3]},
    gripper_position=0.5
)
```

### 技能结果 (SkillResult)

每个任务返回结果：
- `success`: 执行是否成功
- `message`: 结果信息
- `data`: 可选的结果数据
- `error`: 失败时的错误类型

```python
from agents import SkillResult

# 成功结果
result = SkillResult(
    success=True,
    message="Object picked successfully",
    data={"object_id": "ball_001"}
)

# 失败结果
result = SkillResult(
    success=False,
    message="Failed to grasp object",
    error="GraspFailedError"
)
```

---

## 常见任务

### 任务 1: 简单拿取任务

```python
import asyncio
from agents import SimpleAgent

async def pick_task():
    agent = SimpleAgent.from_preset("default")
    result = await agent.run_task("pick up the red cube")
    return result

result = asyncio.run(pick_task())
```

### 任务 2: 多步骤任务

```python
import asyncio
from agents import RobotAgentLoop, AgentConfig
from agents import ConfigManager

async def multi_step_task():
    # 创建配置
    config = ConfigManager.create(
        agent_name="robot",
        max_steps=10,
        perception_enabled=True
    )

    # 创建代理循环
    loop = RobotAgentLoop(...)  # 提供必要的提供者

    # 执行多步
    for i in range(5):
        result = await loop.step()
        if not result.success:
            print(f"步骤 {i} 失败: {result.error}")
            break

    return loop.step_count
```

### 任务 3: 使用工具执行

```python
from agents import (
    GripperTool, MoveTool, VisionTool,
    ToolRegistry, StrategySelector
)

async def tool_task():
    # 注册工具
    registry = ToolRegistry()
    gripper = GripperTool()
    move = MoveTool()
    vision = VisionTool()

    registry.register("gripper", gripper)
    registry.register("move", move)
    registry.register("vision", vision)

    # 创建选择器
    selector = StrategySelector(registry)

    # 使用视觉工具检测对象
    vision_result = await vision.execute(operation="detect_objects")

    # 使用移动工具移动到目标位置
    move_result = await move.execute(
        target={"x": 0.5, "y": 0.3, "z": 0.2},
        mode="direct"
    )

    # 使用机械爪工具抓取
    gripper_result = await gripper.execute(action="grasp", force=0.8)

    return {
        "vision": vision_result,
        "move": move_result,
        "gripper": gripper_result
    }
```

### 任务 4: 数据处理管道

```python
from agents import (
    PreprocessorPlugin, PostprocessorPlugin, VisualizationPlugin
)

async def data_pipeline():
    # 创建插件
    preprocessor = PreprocessorPlugin()
    postprocessor = PostprocessorPlugin()
    visualizer = VisualizationPlugin()

    # 初始化
    await preprocessor.initialize()
    await postprocessor.initialize()
    await visualizer.initialize()

    # 数据清理和标准化
    raw_data = {
        "values": [1.0, 2.0, None, 4.0, float('nan'), 6.0]
    }

    cleaned = await preprocessor.execute(
        operation="clean",
        data=raw_data
    )

    normalized = await preprocessor.execute(
        operation="normalize",
        data=cleaned
    )

    # 结果后处理
    processed = await postprocessor.execute(
        operation="format",
        data=normalized
    )

    # 可视化
    stats = await visualizer.execute(
        operation="statistics",
        data=normalized.get("data")
    )

    return stats
```

---

## 配置指南

### 预设配置

```python
from agents import ConfigManager

# 加载默认配置
config = ConfigManager.load_preset("default")

# 加载 VLA+ 配置
config = ConfigManager.load_preset("vla_plus")
```

### 自定义配置

```python
from agents import AgentConfig

config = AgentConfig(
    agent_name="my_robot",
    max_steps=100,
    llm_model="qwen",
    perception_enabled=True,
    learning_rate=0.01,
    memory_limit=1000
)
```

### YAML 配置文件

创建 `config.yaml`:

```yaml
agent:
  name: "robot_001"
  max_steps: 50
  llm_model: "qwen"

perception:
  enabled: true
  image_size: [480, 640]

execution:
  default_timeout: 30
  retry_attempts: 3
```

加载配置:

```python
config = ConfigManager.load_yaml("config.yaml")
```

### 环境变量覆盖

```bash
export AGENT_NAME="robot_002"
export MAX_STEPS=100
export LLM_MODEL="llama"
```

---

## 最佳实践

### 1. 使用异步/等待模式

```python
# ✅ 推荐: 使用 async/await
async def good_example():
    agent = SimpleAgent.from_preset("default")
    result = await agent.run_task("pick object")
    return result

# ❌ 避免: 阻塞调用
result = agent.run_task("pick object")  # 会导致错误
```

### 2. 错误处理

```python
async def safe_task():
    try:
        agent = SimpleAgent.from_preset("default")
        result = await agent.run_task("pick object")

        if result.success:
            print(f"成功: {result.message}")
            return result.data
        else:
            print(f"失败: {result.error}")
            return None

    except Exception as e:
        print(f"异常: {e}")
        return None
```

### 3. 资源清理

```python
async def clean_example():
    preprocessor = PreprocessorPlugin()

    try:
        await preprocessor.initialize()
        result = await preprocessor.execute(
            operation="normalize",
            data={"values": [1, 2, 3]}
        )
        return result
    finally:
        await preprocessor.cleanup()  # 总是清理资源
```

### 4. 性能优化

```python
# ✅ 推荐: 并发执行多个任务
import asyncio

async def parallel_tasks():
    agent = SimpleAgent.from_preset("default")

    tasks = [
        agent.run_task("task 1"),
        agent.run_task("task 2"),
        agent.run_task("task 3")
    ]

    results = await asyncio.gather(*tasks)
    return results
```

### 5. 缓存利用

```python
# PreprocessorPlugin 自动缓存重复数据
async def cache_example():
    preprocessor = PreprocessorPlugin()
    await preprocessor.initialize()

    data = {"values": [1.0, 2.0, 3.0]}

    # 第一次: 计算
    result1 = await preprocessor.execute(
        operation="normalize",
        data=data
    )

    # 第二次: 使用缓存 (更快)
    result2 = await preprocessor.execute(
        operation="normalize",
        data=data
    )

    assert result2.get("from_cache") is True
```

---

## 故障排查

### 问题 1: 代理初始化失败

**症状**: `RuntimeError: Failed to initialize agent`

**解决方案**:
```python
# 检查配置
from agents import ConfigManager
config = ConfigManager.create(agent_name="test")
print(config)

# 检查依赖
try:
    from agents import SimpleAgent
    agent = SimpleAgent.from_preset("default")
except Exception as e:
    print(f"初始化失败: {e}")
```

### 问题 2: 任务超时

**症状**: `TimeoutError: Task execution timeout`

**解决方案**:
```python
# 增加超时时间
import asyncio

async def timeout_task():
    agent = SimpleAgent.from_preset("default")
    try:
        result = await asyncio.wait_for(
            agent.run_task("complex task"),
            timeout=60.0  # 60 秒超时
        )
        return result
    except asyncio.TimeoutError:
        print("任务执行超时")
        return None
```

### 问题 3: 内存占用过高

**症状**: `MemoryError` 或内存持续增长

**解决方案**:
```python
# 确保清理资源
async def memory_efficient():
    for i in range(1000):
        agent = SimpleAgent.from_preset("default")
        try:
            result = await agent.run_task("task")
        finally:
            # 显式清理
            await agent.cleanup()

        # 偶尔休息
        if i % 100 == 0:
            print(f"处理 {i} 个任务，清理内存")
```

### 问题 4: 插件不可用

**症状**: `KeyError: Plugin not found`

**解决方案**:
```python
# 检查插件是否注册
from agents import PluginRegistry
from agents import PreprocessorPlugin

registry = PluginRegistry()

# 确保插件已初始化和注册
plugin = PreprocessorPlugin()
await plugin.initialize()
registry.register(plugin.name, plugin)

# 现在可以使用
retrieved = registry.get("preprocessor")
```

---

## 下一步

- 查看 [API 参考](API_REFERENCE.md) 获取完整的 API 文档
- 查看 [开发者指南](DEVELOPER_GUIDE.md) 了解架构设计
- 查看 [架构文档](ARCHITECTURE.md) 了解系统设计

---

*用户指南版本 1.0.0 - 2026-04-04*
