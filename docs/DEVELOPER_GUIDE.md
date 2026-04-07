# EmbodiedAgentsSys 开发者指南

**版本**: 1.0.0
**最后更新**: 2026-04-04

---

## 目录

1. [开发环境设置](#开发环境设置)
2. [项目结构](#项目结构)
3. [开发工作流](#开发工作流)
4. [扩展系统](#扩展系统)
5. [测试指南](#测试指南)
6. [代码标准](#代码标准)
7. [性能指标](#性能指标)

---

## 开发环境设置

### 前置要求

```bash
# Python 3.8+
python --version

# pip
pip --version

# Git
git --version
```

### 克隆和设置

```bash
# 克隆仓库
git clone <repo-url>
cd EmbodiedAgentsSys

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 项目依赖

**核心依赖**:
- pydantic >= 2.0: 配置验证
- pyyaml >= 6.0: YAML 配置解析
- typing-extensions: 类型提示扩展

**开发依赖**:
- pytest >= 7.0: 测试框架
- pytest-asyncio >= 0.21: 异步测试支持
- pytest-cov >= 4.0: 代码覆盖率

---

## 项目结构

```
EmbodiedAgentsSys/
├── agents/                      # 核心库
│   ├── __init__.py             # 公共 API 导出
│   ├── core/                   # 核心类型和循环
│   │   ├── types.py            # RobotObservation, SkillResult, AgentConfig
│   │   └── agent_loop.py       # RobotAgentLoop
│   ├── config/                 # 配置管理
│   │   ├── manager.py          # ConfigManager
│   │   ├── schemas.py          # Pydantic schemas
│   │   └── presets/            # 预设 YAML 配置
│   ├── cognition/              # 认知层
│   │   ├── planning.py         # PlanningLayer
│   │   ├── reasoning.py        # ReasoningLayer
│   │   ├── learning.py         # LearningLayer
│   │   └── engine.py           # CognitionEngine
│   ├── execution/              # 执行层
│   │   └── tools/              # 工具框架
│   │       ├── base.py         # ToolBase
│   │       ├── registry.py     # ToolRegistry
│   │       ├── strategy.py     # StrategySelector
│   │       ├── gripper_tool.py
│   │       ├── move_tool.py
│   │       └── vision_tool.py
│   ├── feedback/               # 反馈层
│   │   ├── logger.py           # FeedbackLogger
│   │   ├── analyzer.py         # FeedbackAnalyzer
│   │   └── loop.py             # FeedbackLoop
│   ├── extensions/             # 插件框架
│   │   ├── plugin.py           # PluginBase
│   │   ├── registry.py         # PluginRegistry
│   │   ├── loader.py           # PluginLoader
│   │   ├── preprocessor_plugin.py
│   │   ├── postprocessor_plugin.py
│   │   └── visualization_plugin.py
│   └── simple_agent.py         # 简化接口
├── tests/                      # 测试
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── conftest.py             # Pytest 配置
├── docs/                       # 文档
├── requirements.txt            # 依赖
└── pytest.ini                  # Pytest 配置
```

---

## 开发工作流

### 使用 TDD 添加新功能

遵循 RED-GREEN-REFACTOR 循环：

```python
# 1. RED: 编写失败的测试
def test_new_feature():
    feature = NewFeature()
    result = feature.execute()
    assert result.success is True

# 2. 运行测试确认失败
# pytest tests/unit/test_new_feature.py -v

# 3. GREEN: 编写最小实现
class NewFeature:
    def execute(self):
        return {"success": True}

# 4. 运行测试确认通过
# pytest tests/unit/test_new_feature.py -v

# 5. REFACTOR: 清理代码
# (移除重复, 改进名称等)
```

### 完整开发示例

```python
# 1. 创建测试文件: tests/unit/test_custom_tool.py
import pytest
from agents.execution.tools.base import ToolBase

def test_custom_tool_basic():
    tool = CustomTool()
    assert tool.name == "custom"

@pytest.mark.asyncio
async def test_custom_tool_execute():
    tool = CustomTool()
    result = await tool.execute(param="value")
    assert result.get("success") is True

# 2. 创建实现文件: agents/execution/tools/custom_tool.py
from typing import Optional, Dict, Any
from .base import ToolBase

class CustomTool(ToolBase):
    name = "custom"
    keywords = ["custom", "tool"]

    async def execute(self, **kwargs) -> dict:
        param = kwargs.get("param")
        return {
            "success": True,
            "message": f"Executed with {param}",
            "data": {"param": param}
        }

# 3. 在 agents/__init__.py 中导出
from agents.execution.tools.custom_tool import CustomTool

__all__ = [
    "CustomTool",
    # ... 其他导出
]

# 4. 运行测试
# pytest tests/unit/test_custom_tool.py -v

# 5. 注册工具
from agents import CustomTool, ToolRegistry

registry = ToolRegistry()
registry.register("custom", CustomTool())
```

---

## 扩展系统

### 创建自定义工具

```python
from agents.execution.tools.base import ToolBase

class MyRobotTool(ToolBase):
    name = "my_tool"
    keywords = ["my", "custom", "action"]
    description = "My custom robot tool"

    async def execute(self, **kwargs) -> dict:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            dict: 执行结果
        """
        try:
            # 验证参数
            await self.validate(**kwargs)

            # 执行工具逻辑
            result = self._do_something(kwargs)

            return {
                "success": True,
                "message": "Tool executed successfully",
                "data": result
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Tool execution failed: {e}",
                "error": type(e).__name__
            }

    async def validate(self, **kwargs) -> bool:
        """验证参数"""
        if "required_param" not in kwargs:
            raise ValueError("Missing required_param")
        return True

    def _do_something(self, kwargs):
        """实现工具逻辑"""
        return {"result": "data"}

    async def cleanup(self) -> None:
        """清理资源"""
        pass
```

### 创建自定义插件

```python
from agents.extensions.plugin import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"
    description = "My custom plugin"

    def __init__(self):
        self.initialized = False
        self.data = {}

    async def initialize(self, config=None) -> None:
        """初始化插件"""
        self.initialized = True
        self.config = config or {}

    async def execute(self, operation: str = None, **kwargs) -> dict:
        """执行插件操作"""
        if not self.initialized:
            raise RuntimeError("Plugin not initialized")

        if operation == "my_operation":
            return await self._my_operation(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _my_operation(self, **kwargs) -> dict:
        """实现具体操作"""
        result = {"result": "data"}
        return {
            "success": True,
            "operation": "my_operation",
            "data": result
        }

    async def cleanup(self) -> None:
        """清理资源"""
        self.data.clear()
        self.initialized = False
```

### 注册和使用扩展

```python
from agents import ToolRegistry, PluginRegistry
from agents.execution.tools.custom_tool import MyRobotTool
from agents.extensions.custom_plugin import MyPlugin

# 注册工具
tool_registry = ToolRegistry()
tool_registry.register("my_tool", MyRobotTool())

# 注册插件
plugin_registry = PluginRegistry()
plugin = MyPlugin()
await plugin.initialize()
plugin_registry.register(plugin.name, plugin)

# 使用
tool = tool_registry.get("my_tool")
result = await tool.execute(param="value")

plugin = plugin_registry.get("my_plugin")
result = await plugin.execute(operation="my_operation", data={})
```

---

## 测试指南

### 单元测试

```python
# tests/unit/test_my_module.py
import pytest
from agents.core.types import RobotObservation

class TestRobotObservation:
    def test_initialization(self):
        """测试初始化"""
        obs = RobotObservation()
        assert obs is not None
        assert obs.timestamp is not None

    def test_with_parameters(self):
        """测试参数化初始化"""
        obs = RobotObservation(
            gripper_position=0.8,
            state={"joint_0": 0.1}
        )
        assert obs.gripper_position == 0.8
        assert obs.state["joint_0"] == 0.1
```

### 异步测试

```python
# tests/unit/test_async_code.py
import pytest

@pytest.mark.asyncio
async def test_agent_step():
    """测试异步代理步骤"""
    from agents import SimpleAgent

    agent = SimpleAgent.from_preset("default")
    result = await agent.run_task("test task")
    assert result is not None
    assert hasattr(result, "success")
```

### 测试夹具

```python
# tests/conftest.py
import pytest
from agents import AgentConfig

@pytest.fixture
def dummy_config():
    """创建测试用配置"""
    return AgentConfig(
        agent_name="test_agent",
        max_steps=10,
        perception_enabled=False
    )

@pytest.fixture
@pytest.mark.asyncio
async def dummy_llm_provider():
    """创建模拟 LLM 提供者"""
    class DummyLLM:
        async def generate(self, prompt):
            return "dummy response"

    return DummyLLM()
```

### 运行测试

```bash
# 运行所有单元测试
pytest tests/unit/

# 运行特定测试文件
pytest tests/unit/test_my_module.py

# 运行特定测试
pytest tests/unit/test_my_module.py::TestClass::test_method

# 显示覆盖率
pytest tests/ --cov=agents

# 详细输出
pytest tests/ -v

# 显示打印输出
pytest tests/ -s
```

---

## 代码标准

### 类型提示

```python
# ✅ 推荐: 完整的类型提示
from typing import Optional, Dict, List

def process_data(
    data: List[float],
    threshold: float = 0.5
) -> Dict[str, float]:
    """处理数据并返回统计信息"""
    return {"mean": sum(data) / len(data)}

# ❌ 避免: 缺少类型提示
def process_data(data, threshold=0.5):
    return {"mean": sum(data) / len(data)}
```

### 文档字符串

```python
# ✅ 推荐: 完整的文档字符串
class MyClass:
    """简短描述"""

    async def my_method(self, param: str) -> dict:
        """
        方法的详细描述

        Args:
            param: 参数描述

        Returns:
            dict: 返回值描述，包含以下字段：
                - key1: 值1的描述
                - key2: 值2的描述

        Raises:
            ValueError: 当参数无效时抛出
        """
        pass
```

### 命名约定

```python
# ✅ 推荐
robot_config = {...}        # 变量: snake_case
RobotAgent = ...            # 类: PascalCase
def execute_task():         # 函数: snake_case
CONSTANT_VALUE = 100        # 常量: UPPER_CASE

# ❌ 避免
robotConfig = {...}         # 混合大小写
robot_Agent = ...           # 不一致
executeTask():              # 混合风格
```

### 导入组织

```python
# ✅ 推荐: 分组导入
import asyncio
import json
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel

from agents.core.types import RobotObservation
from agents.config.manager import ConfigManager
```

---

## 性能指标

### 性能目标

| 指标 | 目标 | 当前 |
|------|------|------|
| 初始化时间 | < 50ms | ✅ < 20ms |
| 单步执行 | < 100ms | ✅ < 100ms |
| 内存占用 | < 50MB | ✅ < 15MB |
| 并发任务 | 10+ | ✅ 支持 20+ |

### 性能监测

```python
import time
import tracemalloc

# 监测执行时间
start = time.time()
result = await agent.run_task("task")
elapsed = time.time() - start
print(f"执行时间: {elapsed*1000:.2f}ms")

# 监测内存使用
tracemalloc.start()
agent = SimpleAgent.from_preset("default")
current, peak = tracemalloc.get_traced_memory()
print(f"峰值内存: {peak/1024/1024:.1f}MB")
tracemalloc.stop()
```

### 性能优化建议

1. **使用异步并发**: 多个任务使用 `asyncio.gather()`
2. **启用缓存**: PreprocessorPlugin 自动缓存重复数据
3. **监控内存**: 定期检查和清理大数据对象
4. **批处理**: 使用批处理模式处理多个数据

---

## 提交代码

### Git 工作流

```bash
# 创建特性分支
git checkout -b feature/my-feature

# 提交更改
git add .
git commit -m "feat: add my feature"

# 推送分支
git push origin feature/my-feature

# 创建 Pull Request
# (在 GitHub 上)

# 合并到 main
git checkout main
git merge feature/my-feature
```

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- feat: 新功能
- fix: 修复 bug
- docs: 文档更改
- style: 代码格式（不影响功能）
- refactor: 重构代码
- test: 添加或更新测试
- perf: 性能优化

**示例**:
```
feat(tools): add custom robot tool

Implement CustomRobotTool that supports real-time
sensor data processing with 50ms latency.

Closes #123
```

---

## 常见开发任务

### 添加新工具

1. 创建测试文件
2. 编写测试用例
3. 实现工具类
4. 在 `agents/__init__.py` 中导出
5. 运行全部测试确认通过

### 添加新插件

1. 创建测试文件
2. 编写测试用例
3. 实现插件类
4. 在 `agents/__init__.py` 中导出
5. 运行全部测试确认通过

### 更新 API

1. 修改接口定义
2. 更新所有实现
3. 更新测试用例
4. 更新文档
5. 更新 CHANGELOG

---

## 调试技巧

### 使用 print 调试

```python
import asyncio
from agents import SimpleAgent

async def debug_task():
    agent = SimpleAgent.from_preset("default")

    # 添加调试输出
    print(f"代理配置: {agent.config}")
    print(f"代理类型: {type(agent)}")

    result = await agent.run_task("test")

    # 检查结果
    print(f"结果: {result}")
    print(f"成功: {result.success}")
    if result.data:
        print(f"数据: {result.data}")

asyncio.run(debug_task())
```

### 使用日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MyTool:
    async def execute(self, **kwargs):
        logger.debug(f"执行工具，参数: {kwargs}")
        try:
            result = await self._do_work()
            logger.info(f"工具执行成功: {result}")
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            raise
```

---

## 下一步

- 查看 [架构文档](ARCHITECTURE.md) 了解系统设计
- 查看 [API 参考](API_REFERENCE.md) 获取完整 API 文档
- 查看 [用户指南](USER_GUIDE.md) 了解常见使用场景

---

*开发者指南版本 1.0.0 - 2026-04-04*
