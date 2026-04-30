:orphan:

# 架构实施计划（TDD 驱动）
## 修订 4 层架构的完整测试驱动实施方案

**日期**: 2026-04-04
**范围**: 架构重组的完整实施流程（TDD 方法）
**开发模式**: 个人开发者，每周 1-2 个功能单元
**工作流程**: RED (测试) → GREEN (实施) → REFACTOR (优化)

---

## 目录

1. [概述](#概述)
2. [第 1 周计划：基础设施](#第-1-周计划基础设施)
3. [第 2 周计划：分离关注点](#第-2-周计划分离关注点)
4. [第 3 周计划：扩展点框架](#第-3-周计划扩展点框架)
5. [第 4 周计划：ROS2 解耦](#第-4-周计划ros2-解耦)
6. [第 5-6 周计划：完善和验证](#第-5-6-周计划完善和验证)
7. [完整的测试代码框架](#完整的测试代码框架)
8. [验收标准清单](#验收标准清单)

---

## 概述

### 核心原则

**TDD 工作流（Red-Green-Refactor）**：

```
1. RED: 编写失败的测试（描述期望行为）
2. Verify RED: 确认测试失败原因正确
3. GREEN: 编写最小实现代码
4. Verify GREEN: 所有测试通过
5. REFACTOR: 清理代码，保持测试通过
```

### 实施分解

```
总工作量：6 周（针对个人开发者）

第 1 周 (P1)：建立基础设施
  ├─ Task 1.1: 创建 agents/core/ 纯 Python 核心
  ├─ Task 1.2: 创建 ConfigManager 统一配置
  └─ Task 1.3: 创建 SimpleAgent 快速开始类

第 2 周 (P2)：分离 Cognition 层
  ├─ Task 2.1: 分解 Cognition 为三个子层
  ├─ Task 2.2: 定义清晰的层级接口
  └─ Task 2.3: 提取 feedback_loop

第 3 周 (P3)：创建扩展框架
  ├─ Task 3.1: 创建 agents/extensions/ 目录
  ├─ Task 3.2: 实现 PluginLoader
  └─ Task 3.3: 编写示例扩展

第 4 周 (P4)：创建工具层
  ├─ Task 4.1: 添加 execution/tools/ 层
  ├─ Task 4.2: 实现 strategy_selector
  └─ Task 4.3: 验证工具调用

第 5-6 周 (P5)：ROS2 解耦和完善
  ├─ Task 5.1: ROS2 解耦
  ├─ Task 5.2: 集成测试验证
  └─ Task 5.3: 文档和示例
```

---

## 第 1 周计划：基础设施

### Task 1.1: 创建 agents/core/ 纯 Python 核心

**目标**：建立不依赖 ROS2 的核心执行引擎

#### 测试计划（RED）

```python
# tests/unit/test_core_types.py
"""Test agents/core/types.py - 基础类型定义"""

def test_robot_observation_creation():
    """RobotObservation 可以创建"""
    obs = RobotObservation(
        image=None,
        state={"joint_0": 0.5},
        gripper={"position": 0.8},
        timestamp=1000.0
    )
    assert obs.state["joint_0"] == 0.5
    assert obs.timestamp == 1000.0

def test_skill_result_success():
    """SkillResult 可以表示成功"""
    result = SkillResult(
        success=True,
        message="Task completed",
        data={"xyz": [1, 2, 3]}
    )
    assert result.success is True
    assert result.data["xyz"] == [1, 2, 3]

def test_agent_config_validation():
    """AgentConfig 可以验证配置"""
    # 有效配置
    config = AgentConfig(
        agent_name="test_agent",
        max_steps=100,
        llm_model="qwen",
        perception_enabled=True
    )
    assert config.agent_name == "test_agent"

    # 无效配置应该抛出异常
    with pytest.raises(ValidationError):
        AgentConfig(max_steps=-1)  # 负数无效

# tests/unit/test_core_agent_loop.py
"""Test agents/core/agent_loop.py - 代理主循环"""

@pytest.mark.asyncio
async def test_agent_loop_initialization():
    """RobotAgentLoop 可以初始化"""
    config = AgentConfig(agent_name="test")
    loop = RobotAgentLoop(
        llm_provider=DummyLLMProvider(),
        perception_provider=DummyPerceptionProvider(),
        executor=DummyExecutor(),
        config=config
    )
    assert loop.config.agent_name == "test"

@pytest.mark.asyncio
async def test_agent_loop_basic_cycle():
    """代理循环可以执行基本的 observe-think-act 周期"""
    # 设置
    obs_provider = DummyPerceptionProvider(
        return_value=RobotObservation(state={"ready": True})
    )
    llm_provider = DummyLLMProvider(
        return_code="print('executing')"
    )
    executor = DummyExecutor(
        return_value=SkillResult(success=True, message="done")
    )

    config = AgentConfig(agent_name="test", max_steps=1)
    loop = RobotAgentLoop(
        llm_provider=llm_provider,
        perception_provider=obs_provider,
        executor=executor,
        config=config
    )

    # 执行一步
    result = await loop.step()

    # 验证
    assert obs_provider.called is True
    assert llm_provider.called is True
    assert executor.called is True
    assert result.success is True

@pytest.mark.asyncio
async def test_agent_loop_no_ros2_dependency():
    """RobotAgentLoop 不依赖 ROS2"""
    # 这个测试验证可以在纯 Python 环境中创建循环
    # 不需要任何 ROS2 mocking
    import sys
    assert 'rclpy' not in sys.modules  # ROS2 未导入

    config = AgentConfig(agent_name="pure_python_test")
    loop = RobotAgentLoop(
        llm_provider=DummyLLMProvider(),
        perception_provider=DummyPerceptionProvider(),
        executor=DummyExecutor(),
        config=config
    )

    assert loop is not None

# tests/unit/test_core_messages.py
"""Test agents/core/messages.py - 消息系统"""

def test_observation_message_creation():
    """可以创建观察消息"""
    msg = ObservationMessage(
        source="perception",
        timestamp=1000.0,
        observation=RobotObservation(state={})
    )
    assert msg.source == "perception"
    assert isinstance(msg.observation, RobotObservation)

def test_action_message_creation():
    """可以创建动作消息"""
    msg = ActionMessage(
        source="reasoning",
        action_type="code",
        action_data="arm.reach(target=[0.5, 0.2, 0.3])"
    )
    assert msg.action_type == "code"

def test_result_message_creation():
    """可以创建结果消息"""
    msg = ResultMessage(
        source="executor",
        success=True,
        result_data={"status": "completed"}
    )
    assert msg.success is True
```

#### 实施步骤（GREEN）

**1. 创建 agents/core/types.py**

```python
# agents/core/types.py
"""基础类型定义 - 不依赖 ROS2"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import numpy as np
from datetime import datetime

@dataclass
class RobotObservation:
    """机器人观察数据"""
    image: Optional[np.ndarray] = None
    state: Dict[str, float] = field(default_factory=dict)
    gripper: Dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()

@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class AgentConfig:
    """代理配置"""
    agent_name: str
    max_steps: int = 100
    llm_model: str = "qwen"
    perception_enabled: bool = True

    def __post_init__(self):
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")
```

**2. 创建 agents/core/messages.py**

```python
# agents/core/messages.py
"""代理间消息系统"""

from dataclasses import dataclass
from typing import Any, Dict, Literal
from datetime import datetime

@dataclass
class Message:
    """基础消息类"""
    source: str
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()

@dataclass
class ObservationMessage(Message):
    """观察消息"""
    observation: 'RobotObservation' = None

@dataclass
class ActionMessage(Message):
    """动作消息"""
    action_type: Literal["skill", "code", "command"] = "skill"
    action_data: Any = None

@dataclass
class ResultMessage(Message):
    """结果消息"""
    success: bool = True
    result_data: Dict[str, Any] = None
```

**3. 创建 agents/core/agent_loop.py**

```python
# agents/core/agent_loop.py
"""核心代理循环 - 纯 Python，无 ROS2 依赖"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RobotAgentLoop(ABC):
    """核心代理循环抽象"""

    def __init__(self, llm_provider, perception_provider, executor, config):
        self.llm_provider = llm_provider
        self.perception_provider = perception_provider
        self.executor = executor
        self.config = config
        self.step_count = 0

    async def step(self) -> 'SkillResult':
        """执行一步 observe-think-act 循环"""
        if self.step_count >= self.config.max_steps:
            return SkillResult(success=False, message="Max steps exceeded")

        # 1. 观察
        observation = await self.perception_provider.get_observation()

        # 2. 思考
        action = await self.llm_provider.generate_action(observation)

        # 3. 执行
        result = await self.executor.execute(action)

        self.step_count += 1
        return result
```

#### 验收标准

- [ ] agents/core/types.py 存在且包含所有基础类型
- [ ] agents/core/messages.py 存在且消息系统完整
- [ ] agents/core/agent_loop.py 存在且 RobotAgentLoop 可以初始化
- [ ] **所有测试通过**：`pytest tests/unit/test_core_*.py -v`
- [ ] 无需导入任何 ROS2 模块

---

### Task 1.2: 创建 ConfigManager 统一配置

**目标**：统一管理配置，支持多种加载方式（YAML、环境变量、代码）

#### 测试计划（RED）

```python
# tests/unit/test_config_manager.py
"""Test ConfigManager 统一配置管理"""

def test_config_manager_load_preset_default():
    """可以加载默认预设"""
    config = ConfigManager.load_preset("default")
    assert config is not None
    assert hasattr(config, 'agent_name')

def test_config_manager_load_preset_vla_plus():
    """可以加载 vla_plus 预设"""
    config = ConfigManager.load_preset("vla_plus")
    assert config.llm_model == "qwen"  # 继承默认值

def test_config_manager_environment_override():
    """环境变量可以覆盖配置"""
    import os
    os.environ['AGENT_LLM_MODEL'] = 'gpt-4'

    config = ConfigManager.load_preset("default")
    assert config.llm_model == 'gpt-4'

    del os.environ['AGENT_LLM_MODEL']

def test_config_manager_validation():
    """无效配置应该抛出异常"""
    with pytest.raises(ValidationError):
        ConfigManager.create(max_steps=-1)

def test_config_manager_load_yaml():
    """可以从 YAML 文件加载配置"""
    # 创建临时 YAML 文件
    yaml_content = """
agent_name: test_agent
max_steps: 50
llm_model: gpt-4
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()

        config = ConfigManager.load_yaml(f.name)
        assert config.agent_name == "test_agent"
        assert config.max_steps == 50

        os.unlink(f.name)
```

#### 实施步骤（GREEN）

**1. 创建 agents/config/schemas.py**

```python
# agents/config/schemas.py
"""配置 Schema（使用 Pydantic 验证）"""

from pydantic import BaseModel, Field, validator
from typing import Optional

class AgentConfigSchema(BaseModel):
    """代理配置 Schema"""
    agent_name: str = "default_agent"
    max_steps: int = Field(100, ge=1)
    llm_model: str = "qwen"
    perception_enabled: bool = True

    class Config:
        extra = 'allow'

class PerceptionConfigSchema(BaseModel):
    """感知配置 Schema"""
    vision_model: str = "sam3"
    enabled: bool = True

class CognitionConfigSchema(BaseModel):
    """认知配置 Schema"""
    llm_provider: str = "ollama"
    code_generation_enabled: bool = True
    memory_size: int = 8000
```

**2. 创建 agents/config/manager.py**

```python
# agents/config/manager.py
"""统一配置管理器"""

import os
import yaml
from typing import Optional, Dict, Any
from .schemas import AgentConfigSchema

class ConfigManager:
    """统一的配置加载和管理"""

    PRESETS_DIR = os.path.join(os.path.dirname(__file__), 'presets')

    @classmethod
    def load_preset(cls, preset_name: str):
        """从预设加载配置"""
        preset_file = os.path.join(cls.PRESETS_DIR, f'{preset_name}.yaml')
        config = cls.load_yaml(preset_file)

        # 应用环境变量覆盖
        config = cls._apply_env_overrides(config)

        return config

    @classmethod
    def load_yaml(cls, filepath: str):
        """从 YAML 文件加载配置"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        return AgentConfigSchema(**data)

    @classmethod
    def create(cls, **kwargs):
        """从关键字参数创建配置"""
        return AgentConfigSchema(**kwargs)

    @staticmethod
    def _apply_env_overrides(config):
        """应用环境变量覆盖"""
        for key, value in os.environ.items():
            if key.startswith('AGENT_'):
                attr_name = key[6:].lower()
                if hasattr(config, attr_name):
                    # 尝试转换类型
                    setattr(config, attr_name, value)

        return config
```

#### 验收标准

- [ ] agents/config/schemas.py 存在且所有 Schema 定义完整
- [ ] agents/config/manager.py 存在且支持三种加载方式
- [ ] 所有测试通过：`pytest tests/unit/test_config_manager.py -v`

---

### Task 1.3: 创建 SimpleAgent 快速开始类

**目标**：提供用户友好的快速开始接口

#### 测试计划（RED）

```python
# tests/unit/test_simple_agent.py
"""Test SimpleAgent 快速开始类"""

@pytest.mark.asyncio
async def test_simple_agent_from_preset():
    """可以从预设创建 SimpleAgent"""
    agent = SimpleAgent.from_preset("default")
    assert agent is not None
    assert hasattr(agent, 'run_task')

@pytest.mark.asyncio
async def test_simple_agent_initialization():
    """可以用配置初始化 SimpleAgent"""
    config = ConfigManager.load_preset("default")
    agent = SimpleAgent(config)
    assert agent.config == config

@pytest.mark.asyncio
async def test_simple_agent_run_task():
    """SimpleAgent 可以运行任务"""
    # Mock 所有组件
    agent = SimpleAgent(
        config=ConfigManager.load_preset("default"),
        llm_provider=DummyLLMProvider(),
        perception_provider=DummyPerceptionProvider(),
        executor=DummyExecutor()
    )

    result = await agent.run_task("test task")
    assert result.success is True

@pytest.mark.asyncio
async def test_simple_agent_composability():
    """SimpleAgent 封装了所有必需的子系统"""
    agent = SimpleAgent.from_preset("default")

    # 验证所有子系统都已初始化
    assert hasattr(agent, 'perception')
    assert hasattr(agent, 'cognition')
    assert hasattr(agent, 'execution')
    assert hasattr(agent, 'feedback')
    assert hasattr(agent, 'loop')
```

#### 实施步骤（GREEN）

```python
# agents/simple_agent.py
"""快速开始的简化接口"""

from typing import Optional
from .core import RobotAgentLoop
from .config import ConfigManager
from .perception.provider import PerceptionProvider
from .cognition.engine import CognitionEngine
from .execution.executor import Executor
from .execution.vdm import VDMAnalyzer

class SimpleAgent:
    """简化的代理接口，3-5 行代码入门"""

    def __init__(
        self,
        config,
        llm_provider=None,
        perception_provider=None,
        executor=None
    ):
        self.config = config

        # 自动初始化子系统
        self.perception = perception_provider or PerceptionProvider(config.perception)
        self.cognition = CognitionEngine(config.cognition, llm_provider)
        self.execution = executor or Executor(config.execution)
        self.feedback = VDMAnalyzer()  # 反馈系统

        # 创建核心循环
        self.loop = RobotAgentLoop(
            llm_provider=self.cognition.llm,
            perception_provider=self.perception,
            executor=self.execution,
            config=config
        )

    @classmethod
    def from_preset(cls, preset_name: str = "default"):
        """从预设快速创建"""
        config = ConfigManager.load_preset(preset_name)
        return cls(config)

    async def run_task(self, task: str):
        """运行一个任务"""
        return await self.loop.step()
```

#### 验收标准

- [ ] agents/simple_agent.py 存在
- [ ] SimpleAgent 可以用 3 行代码初始化和运行
- [ ] 所有测试通过：`pytest tests/unit/test_simple_agent.py -v`
- [ ] **第 1 周验收**：能在纯 Python 环境中创建和运行代理

---

## 第 2 周计划：分离关注点

### Task 2.1: 分解 Cognition 为三个子层

**目标**：将单一的 Cognition 层分解为 Planning、Reasoning、Learning 三个清晰的子层

#### 测试计划（RED）

```python
# tests/unit/test_cognition_layers.py
"""Test Cognition 层的三个子层"""

def test_planning_layer_exists():
    """Planning 层存在且可以初始化"""
    from agents.cognition.planning import PlanningLayer
    planner = PlanningLayer()
    assert planner is not None

def test_reasoning_layer_exists():
    """Reasoning 层存在且可以初始化"""
    from agents.cognition.reasoning import ReasoningLayer
    reasoner = ReasoningLayer()
    assert reasoner is not None

def test_learning_layer_exists():
    """Learning 层存在且可以初始化"""
    from agents.cognition.learning import LearningLayer
    learner = LearningLayer()
    assert learner is not None

@pytest.mark.asyncio
async def test_cognition_engine_uses_three_layers():
    """CognitionEngine 使用三个子层"""
    from agents.cognition.engine import CognitionEngine
    engine = CognitionEngine(config)

    # 执行认知步骤
    result = await engine.think(
        observation=RobotObservation(state={"ready": True}),
        task="pick up object"
    )

    # 验证三个层都被调用了
    assert engine.planning.called
    assert engine.reasoning.called
    # learning 在反馈时调用

@pytest.mark.asyncio
async def test_layer_data_flow():
    """数据在三层之间正确流动"""
    engine = CognitionEngine(config)

    # Planning: 任务 -> 计划
    plan = await engine.planning.generate_plan("pick up red object")
    assert plan is not None

    # Reasoning: 计划 + 观察 -> 代码/技能
    observation = RobotObservation(state={"ready": True})
    action = await engine.reasoning.generate_action(plan, observation)
    assert action is not None

    # Learning: 反馈 -> 改进
    feedback = {"success": True, "steps": 3}
    improved = await engine.learning.improve(action, feedback)
    assert improved is not None
```

#### 实施步骤（GREEN）

**1. 创建三个子层的基类**

```python
# agents/cognition/planning/base.py
from abc import ABC, abstractmethod

class PlanningLayer(ABC):
    """规划子层 - 任务 -> 计划"""

    @abstractmethod
    async def generate_plan(self, task: str) -> dict:
        """生成任务计划"""
        pass

# agents/cognition/reasoning/base.py
class ReasoningLayer(ABC):
    """推理子层 - 计划 + 观察 -> 动作"""

    @abstractmethod
    async def generate_action(self, plan: dict, observation) -> str:
        """生成动作（代码或技能）"""
        pass

# agents/cognition/learning/base.py
class LearningLayer(ABC):
    """学习子层 - 失败 -> 改进"""

    @abstractmethod
    async def improve(self, action: str, feedback: dict) -> str:
        """改进动作"""
        pass
```

**2. 创建 CognitionEngine**

```python
# agents/cognition/engine.py
class CognitionEngine:
    """认知引擎 - 协调三个子层"""

    def __init__(self, config, llm_provider=None):
        self.config = config
        self.planning = PlanningLayer(config)
        self.reasoning = ReasoningLayer(config, llm_provider)
        self.learning = LearningLayer(config)
        self.memory = MemoryManager(config)

    async def think(self, observation, task: str):
        """完整的认知步骤"""
        # 1. 规划
        plan = await self.planning.generate_plan(task)

        # 2. 推理
        action = await self.reasoning.generate_action(plan, observation)

        return action

    async def learn(self, action, result):
        """学习和改进"""
        if not result.success:
            improved_action = await self.learning.improve(action, result)
            return improved_action
        return action
```

#### 验收标准

- [ ] agents/cognition/planning/ 存在且包含规划逻辑
- [ ] agents/cognition/reasoning/ 存在且包含推理逻辑
- [ ] agents/cognition/learning/ 存在且包含学习逻辑
- [ ] agents/cognition/engine.py 正确协调三层
- [ ] 所有测试通过：`pytest tests/unit/test_cognition_layers.py -v`

---

### Task 2.2: 定义清晰的层级接口

**目标**：使用 ABC 和 Protocol 定义各层之间的清晰接口

（因篇幅，省略详细测试和实施代码，遵循相同模式）

#### 验收标准

- [ ] agents/core/interfaces.py 定义所有层的 ABC
- [ ] 每个 ABC 都有清晰的方法签名和文档
- [ ] 所有现有实现都实现这些 ABC

---

### Task 2.3: 提取 feedback_loop

**目标**：将反馈循环显式化为单独的模块

#### 测试计划和实施

```python
# tests/unit/test_feedback_loop.py
"""Test 显式反馈循环"""

@pytest.mark.asyncio
async def test_feedback_loop_analyzes_failure():
    """反馈循环可以分析失败"""
    from agents.cognition.feedback_loop import FeedbackLoop

    loop = FeedbackLoop()
    failure_info = SkillResult(
        success=False,
        message="Grasp failed"
    )

    analysis = await loop.analyze_failure(failure_info)
    assert analysis.reason is not None
    assert analysis.suggestion is not None

@pytest.mark.asyncio
async def test_feedback_loop_improves_code():
    """反馈循环可以改进代码"""
    loop = FeedbackLoop()

    original_code = "arm.reach(target=[0.5, 0.2, 0.3])"
    failure_analysis = {"reason": "target unreachable"}

    improved_code = await loop.improve_code(
        original_code,
        failure_analysis
    )

    assert improved_code != original_code
    assert "reach" in improved_code
```

#### 验收标准

- [ ] agents/cognition/feedback_loop.py 存在
- [ ] 包含 analyze_failure 和 improve_code 方法
- [ ] 所有测试通过

---

## 第 3 周计划：扩展框架

### Task 3.1: 创建 agents/extensions/ 目录

**目标**：为用户提供明确的扩展点

#### 测试计划（RED）

```python
# tests/unit/test_extensions_framework.py
"""Test 扩展框架"""

def test_extensions_directory_exists():
    """extensions 目录存在"""
    import os
    ext_dir = 'agents/extensions'
    assert os.path.isdir(ext_dir)
    assert os.path.isfile(os.path.join(ext_dir, 'README.md'))

def test_custom_perception_example_works():
    """自定义感知扩展示例可以工作"""
    from agents.extensions.custom_perception import example
    # 应该能导入不出错
    assert hasattr(example, 'MyVisionProvider')

def test_custom_skill_example_works():
    """自定义技能扩展示例可以工作"""
    from agents.extensions.custom_skills import example
    assert hasattr(example, 'MySkill')

def test_plugin_loader_can_load_extensions():
    """PluginLoader 可以动态加载扩展"""
    from agents.utils.plugin_loader import PluginLoader

    loader = PluginLoader('agents.extensions.custom_perception')
    module = loader.load()

    assert module is not None
```

#### 实施步骤（GREEN）

**1. 创建目录结构**

```bash
mkdir -p agents/extensions/{custom_perception,custom_skills,custom_reasoning,custom_hardware}
touch agents/extensions/README.md
touch agents/extensions/__init__.py
```

**2. 创建 README.md**

```markdown
# 扩展框架

## 如何添加自定义感知

见 custom_perception/ 中的 example.py

## 如何添加自定义技能

见 custom_skills/ 中的 example.py

...（更多说明）
```

**3. 创建 PluginLoader**

```python
# agents/utils/plugin_loader.py
"""动态插件加载器"""

import importlib
from typing import Any

class PluginLoader:
    """动态加载用户扩展"""

    def __init__(self, module_path: str):
        self.module_path = module_path

    def load(self) -> Any:
        """动态导入模块"""
        try:
            return importlib.import_module(self.module_path)
        except ImportError as e:
            raise ImportError(f"Failed to load plugin: {self.module_path}") from e
```

#### 验收标准

- [ ] agents/extensions/ 目录存在且包含 4 个子目录
- [ ] 每个子目录都有 __init__.py 和 example.py
- [ ] agents/extensions/README.md 提供清晰的扩展指南
- [ ] PluginLoader 可以动态加载扩展
- [ ] 所有测试通过

---

### Task 3.2-3.3: 实现示例扩展

（遵循相同的 TDD 模式）

**验收标准**：
- [ ] custom_perception/example.py 展示如何添加视觉模型
- [ ] custom_skills/example.py 展示如何添加技能
- [ ] custom_reasoning/example.py 展示如何集成 LLM
- [ ] custom_hardware/example.py 展示如何添加硬件

---

## 第 4 周计划：工具层和策略选择

### Task 4.1: 添加 execution/tools/ 层

#### 测试计划（RED）

```python
# tests/unit/test_execution_tools.py
"""Test execution tools 层"""

def test_perception_tools_exist():
    """感知工具存在"""
    from agents.execution.tools.perception_tools import SegmentationTool
    tool = SegmentationTool()
    assert tool is not None

def test_planning_tools_exist():
    """规划工具存在"""
    from agents.execution.tools.planning_tools import MotionPlanner
    planner = MotionPlanner()
    assert planner is not None

def test_execution_tools_exist():
    """执行工具存在"""
    from agents.execution.tools.execution_tools import ArmController
    controller = ArmController()
    assert controller is not None

@pytest.mark.asyncio
async def test_tools_are_callable_from_generated_code():
    """工具可以从生成的代码中调用"""
    # 生成的代码示例
    code = """
import agents.execution.tools as tools

segmentation = tools.perception_tools.segment(image)
grasps = tools.planning_tools.plan_grasps(segmentation)
trajectory = tools.planning_tools.motion_plan(target_grasp)
result = tools.execution_tools.arm_move(trajectory)
"""
    # 验证代码可以执行（带 mock）
    assert "tools.perception_tools" in code
    assert "tools.planning_tools" in code
    assert "tools.execution_tools" in code
```

#### 实施步骤（GREEN）

```python
# agents/execution/tools/__init__.py
"""执行工具层 - 代码可直接调用的低层工具"""

from . import perception_tools
from . import planning_tools
from . import execution_tools

__all__ = ['perception_tools', 'planning_tools', 'execution_tools']

# agents/execution/tools/perception_tools.py
class SegmentationTool:
    """图像分割工具（SAM3）"""
    async def segment(self, image):
        """分割图像"""
        pass

class DetectionTool:
    """目标检测工具（YOLO）"""
    async def detect(self, image):
        """检测目标"""
        pass

# agents/execution/tools/planning_tools.py
class GraspPlanner:
    """抓取规划工具"""
    async def plan_grasps(self, segmentation):
        """规划抓取"""
        pass

class MotionPlanner:
    """运动规划工具"""
    async def plan_trajectory(self, start, target):
        """规划轨迹"""
        pass

# agents/execution/tools/execution_tools.py
class ArmController:
    """机械臂控制工具"""
    async def move(self, trajectory):
        """执行运动"""
        pass
```

#### 验收标准

- [ ] agents/execution/tools/ 目录存在
- [ ] 包含三个子模块：perception_tools、planning_tools、execution_tools
- [ ] 所有工具都可以从生成的代码中导入和调用
- [ ] 所有测试通过

---

### Task 4.2: 实现 strategy_selector

#### 测试计划（RED）

```python
# tests/unit/test_strategy_selector.py
"""Test 策略选择器"""

@pytest.mark.asyncio
async def test_strategy_selector_simple_task():
    """简单任务选择 VLA 策略"""
    from agents.cognition.reasoning import StrategySelector

    selector = StrategySelector()
    strategy = await selector.select(
        task="pick up the cube",
        observation=RobotObservation()
    )

    assert strategy == ExecutionStrategy.VLA

@pytest.mark.asyncio
async def test_strategy_selector_complex_task():
    """复杂任务选择 CaP 策略"""
    selector = StrategySelector()
    strategy = await selector.select(
        task="place the red cube on top of the blue cube on the high shelf",
        observation=RobotObservation()
    )

    assert strategy == ExecutionStrategy.CAP

@pytest.mark.asyncio
async def test_strategy_selector_returns_correct_type():
    """返回值类型正确"""
    selector = StrategySelector()
    strategy = await selector.select("test task", RobotObservation())

    assert strategy in [ExecutionStrategy.VLA, ExecutionStrategy.HYBRID, ExecutionStrategy.CAP]
```

#### 实施步骤（GREEN）

```python
# agents/cognition/reasoning/strategy_selector.py
from enum import Enum

class ExecutionStrategy(Enum):
    """执行策略"""
    VLA = "vla"           # 简单 - 快速、能耗低
    HYBRID = "hybrid"     # 中等 - VLA + CaP 配合
    CAP = "cap"          # 复杂 - 代码生成、自改进

class StrategySelector:
    """根据任务复杂度选择执行策略"""

    async def select(self, task: str, observation) -> ExecutionStrategy:
        """选择执行策略"""
        complexity = await self._estimate_complexity(task)

        if complexity < 0.3:
            return ExecutionStrategy.VLA
        elif complexity < 0.7:
            return ExecutionStrategy.HYBRID
        else:
            return ExecutionStrategy.CAP

    async def _estimate_complexity(self, task: str) -> float:
        """评估任务复杂度 (0-1)"""
        # 简单启发式：任务长度、关键词等
        complexity = len(task) / 100

        complex_keywords = ['on top of', 'arrange', 'sequence', 'precise']
        for keyword in complex_keywords:
            if keyword in task.lower():
                complexity += 0.2

        return min(complexity, 1.0)
```

#### 验收标准

- [ ] agents/cognition/reasoning/strategy_selector.py 存在
- [ ] ExecutionStrategy enum 定义清晰
- [ ] 复杂度评估工作
- [ ] 所有测试通过

---

## 第 5-6 周计划：完善和验证

### Task 5.1: ROS2 解耦

**目标**：使核心可以独立于 ROS2 运行

#### 测试计划（RED）

```python
# tests/unit/test_ros2_decoupling.py
"""Test ROS2 解耦"""

def test_core_agents_module_no_ros2_import():
    """agents.core 模块不导入 ROS2"""
    import sys

    # 清除任何现有的 ROS2 导入
    for key in list(sys.modules.keys()):
        if 'ros' in key or 'rclpy' in key:
            del sys.modules[key]

    # 导入 core 模块
    from agents import core

    # 验证 ROS2 没有被导入
    assert 'rclpy' not in sys.modules
    assert 'ros2' not in sys.modules

def test_ros2_adapter_layer_exists():
    """ROS2 适配层存在"""
    import os
    assert os.path.isdir('agents/integrations/ros2')
    assert os.path.isfile('agents/integrations/ros2/component.py')

@pytest.mark.asyncio
async def test_pure_python_agent_runs():
    """纯 Python 代理可以运行（无 ROS2）"""
    # 这个测试在纯 Python 环境中运行
    from agents import SimpleAgent

    agent = SimpleAgent.from_preset("default")
    # 验证可以初始化，不需要 ROS2
    assert agent is not None
```

#### 实施步骤（GREEN）

创建 agents/integrations/ros2/ 适配层，将 ROS2 依赖隔离到这个目录。

#### 验收标准

- [ ] agents/core/ 可以在纯 Python 环境中运行
- [ ] agents/integrations/ros2/ 包含所有 ROS2 相关代码
- [ ] conftest.py 中的 ROS2 stub 从 50% 减少
- [ ] 所有单元测试通过（无需 ROS2）

---

### Task 5.2: 集成测试验证

**目标**：验证所有层之间的协作

#### 测试计划（RED）

```python
# tests/integration/test_full_architecture.py
"""Test 完整架构集成"""

@pytest.mark.asyncio
async def test_full_agent_loop():
    """完整的代理循环工作"""
    # 使用 SimpleAgent 创建完整系统
    agent = SimpleAgent.from_preset("default")

    # 运行一个任务
    result = await agent.run_task("test task")

    # 验证所有层都被调用了
    assert agent.perception.called
    assert agent.cognition.planning.called
    assert agent.cognition.reasoning.called
    assert agent.execution.called

@pytest.mark.asyncio
async def test_extension_integration():
    """自定义扩展可以集成"""
    from agents.extensions.custom_perception import example

    # 加载自定义感知模块
    agent = SimpleAgent.from_preset("default")
    agent.perception = example.MyVisionProvider()

    # 运行任务
    result = await agent.run_task("test")
    assert result.success

@pytest.mark.asyncio
async def test_tool_layer_integration():
    """工具层可以从生成的代码调用"""
    from agents.execution.tools import perception_tools, planning_tools

    # 模拟生成的代码
    image = create_test_image()
    segmentation = await perception_tools.segment(image)

    grasps = await planning_tools.plan_grasps(segmentation)
    assert grasps is not None
```

#### 验收标准

- [ ] 完整的代理循环工作
- [ ] 所有层能够正确通信
- [ ] 扩展可以无缝集成
- [ ] 工具层可以被调用
- [ ] 所有集成测试通过

---

### Task 5.3: 文档和示例

**目标**：提供清晰的文档和可运行的示例

#### 测试计划（RED）

```python
# tests/integration/test_examples.py
"""Test 示例代码可以运行"""

@pytest.mark.asyncio
async def test_quick_start_example():
    """快速开始示例可以运行"""
    # 这个测试运行 examples/ 中的代码
    # 类似于：
    # from agents import SimpleAgent
    # agent = SimpleAgent.from_preset("default")
    # result = await agent.run_task("example task")

    # 示例应该在 5 分钟内完成

def test_extension_example():
    """扩展示例清晰明了"""
    # 验证 examples/custom_perception.py 是清晰的
    import examples.custom_perception

    # 应该能够按照示例创建自己的扩展
```

#### 实施步骤（GREEN）

创建：
- `docs/ARCHITECTURE.md` — 系统概览
- `examples/01_quick_start.py` — 最简单的示例
- `examples/02_custom_perception.py` — 扩展示例
- 等等（见用户友好性评估）

#### 验收标准

- [ ] 所有示例代码可以独立运行
- [ ] 文档清晰完整
- [ ] 新用户可以 15 分钟内上手
- [ ] 示例覆盖主要用例

---

## 完整的测试代码框架

### 目录结构

```
tests/
├── conftest.py                    # 共享 fixtures 和 mocks
├── unit/
│   ├── __init__.py
│   ├── test_core_types.py        # Task 1.1
│   ├── test_core_agent_loop.py
│   ├── test_core_messages.py
│   ├── test_config_manager.py    # Task 1.2
│   ├── test_simple_agent.py      # Task 1.3
│   ├── test_cognition_layers.py  # Task 2.1
│   ├── test_extensions_framework.py  # Task 3.1
│   ├── test_execution_tools.py   # Task 4.1
│   ├── test_strategy_selector.py # Task 4.2
│   ├── test_ros2_decoupling.py   # Task 5.1
│   └── ...
└── integration/
    ├── __init__.py
    ├── test_full_architecture.py
    ├── test_examples.py
    └── ...
```

### conftest.py 模板

```python
# tests/conftest.py
"""共享的测试 fixtures 和 mocks"""

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def dummy_config():
    """虚拟配置"""
    from agents.core.types import AgentConfig
    return AgentConfig(agent_name="test_agent", max_steps=1)

@pytest.fixture
def dummy_observation():
    """虚拟观察"""
    from agents.core.types import RobotObservation
    return RobotObservation(state={"ready": True})

@pytest.fixture
def dummy_llm_provider():
    """虚拟 LLM 提供者"""
    mock = AsyncMock()
    mock.generate_action = AsyncMock(return_value="mock_action")
    return mock

@pytest.fixture
def dummy_perception_provider():
    """虚拟感知提供者"""
    mock = AsyncMock()
    mock.get_observation = AsyncMock(return_value=dummy_observation())
    return mock

@pytest.fixture
def dummy_executor():
    """虚拟执行器"""
    from agents.core.types import SkillResult
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=SkillResult(success=True, message="ok"))
    return mock
```

---

## 验收标准清单

### 第 1 周验收

- [ ] agents/core/ 存在且包含 types.py, messages.py, agent_loop.py
- [ ] agents/config/ 存在且包含 manager.py, schemas.py
- [ ] agents/simple_agent.py 存在
- [ ] 所有第 1 周测试通过
- [ ] 可以在纯 Python 环境中运行（无需 ROS2）
- [ ] 代码覆盖率 >= 80%

### 第 2 周验收

- [ ] agents/cognition/ 分为 planning/, reasoning/, learning/
- [ ] agents/cognition/engine.py 正确协调三层
- [ ] agents/cognition/feedback_loop.py 存在
- [ ] 所有第 2 周测试通过
- [ ] 三层接口清晰定义

### 第 3 周验收

- [ ] agents/extensions/ 目录完整
- [ ] 包含 4 个子目录和示例
- [ ] PluginLoader 工作
- [ ] README.md 提供清晰指南

### 第 4 周验收

- [ ] agents/execution/tools/ 存在
- [ ] strategy_selector 工作
- [ ] 工具可以从生成的代码调用

### 第 5-6 周验收

- [ ] ROS2 完全解耦
- [ ] 所有集成测试通过
- [ ] 文档完整
- [ ] 示例可运行
- [ ] 代码覆盖率 >= 85%
- [ ] 无 TODO 或 FIXME 注释（除了 future 特性）

---

## TDD 工作流检查清单

对于每一个 Task，遵循 Red-Green-Refactor：

### RED 阶段
- [ ] 编写清晰的测试，描述期望行为
- [ ] 运行测试，确认失败
- [ ] 失败原因是"功能缺失"而不是"语法错误"

### GREEN 阶段
- [ ] 编写最小实现代码
- [ ] 运行测试，确认通过
- [ ] 所有其他测试也通过

### REFACTOR 阶段
- [ ] 清理代码，消除重复
- [ ] 改进名称和结构
- [ ] 确认所有测试仍然通过

### 验证
- [ ] 代码覆盖率 >= 80%
- [ ] 所有 linter 通过（mypy, pylint）
- [ ] 文档字符串完整

---

## 预期时间线

| 周 | Task | 预计时间 | 难度 |
|-----|------|---------|------|
| 1 | 基础设施（core, config, simple_agent） | 40 小时 | ⭐ |
| 2 | 分离 Cognition 层 | 30 小时 | ⭐⭐ |
| 3 | 扩展框架 | 25 小时 | ⭐ |
| 4 | 工具层 + 策略选择 | 30 小时 | ⭐⭐ |
| 5-6 | ROS2 解耦 + 验证 + 文档 | 50 小时 | ⭐⭐⭐ |
| | **总计** | **175 小时** | |

> 每周 40 小时工作 = 6 周完成

---

## 开始实施的检查清单

在开始编写实施代码之前：

- [ ] 阅读并理解此计划
- [ ] 设置测试基础设施（pytest, conftest.py）
- [ ] 创建 tests/ 目录结构
- [ ] 编写第 1 周的所有测试代码
- [ ] 运行测试，确认全部失败（RED）
- [ ] **然后**开始编写实施代码（GREEN）

---

**计划完成**
**下一步**：
1. 确认此计划是否合理
2. 如需调整，请提出
3. 确认后，开始第 1 周的 RED 阶段（编写测试）
