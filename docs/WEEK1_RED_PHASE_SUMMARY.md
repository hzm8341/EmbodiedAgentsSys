# 第 1 周 RED 阶段完成

**日期**: 2026-04-04
**阶段**: RED ✅ (编写失败的测试)
**状态**: 完成，等待 GREEN 阶段（编写实施代码）

---

## 📊 测试统计

| 类别 | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| **Core Types** | test_core_types.py | 11 | ❌ FAIL |
| **Core Loop** | test_core_agent_loop.py | 9 | ❌ FAIL |
| **Config Manager** | test_config_manager.py | 16 | ❌ FAIL |
| **Simple Agent** | test_simple_agent.py | 18 | ❌ FAIL |
| **总计** | - | **54** | **❌ ALL FAIL** |

## ✅ RED 阶段验证

- [x] 编写清晰的测试（描述期望行为）
- [x] 运行测试，所有测试都失败
- [x] 失败原因正确（`ModuleNotFoundError: No module named 'agents.core'`）
- [x] 测试代码已提交到 git

## 📝 已编写的测试

### test_core_types.py （11 个测试）

```python
✅ RobotObservation.creation
✅ RobotObservation.default_timestamp
✅ RobotObservation.empty_state
✅ SkillResult.success
✅ SkillResult.failure
✅ SkillResult.with_complex_data
✅ AgentConfig.creation
✅ AgentConfig.default_values
✅ AgentConfig.validation_max_steps
✅ CoreNoROS2.types_no_ros2_import
✅ CoreNoROS2.can_be_imported_standalone
```

### test_core_agent_loop.py （9 个测试）

```python
✅ initialization
✅ has_required_attributes
✅ basic_observe_think_act_cycle
✅ increments_step_count
✅ respects_max_steps
✅ passes_observation_to_llm
✅ passes_action_to_executor
✅ no_ros2_dependency
```

### test_config_manager.py （16 个测试）

```python
✅ load_preset_default
✅ load_preset_vla_plus
✅ load_invalid_preset (error handling)
✅ environment_override_llm_model
✅ environment_override_max_steps
✅ multiple_environment_overrides
✅ validation_invalid_max_steps
✅ validation_valid_config
✅ validation_required_field
✅ load_yaml
✅ load_yaml_file_not_found (error handling)
✅ load_yaml_invalid_format (error handling)
✅ create_from_kwargs
✅ create_with_defaults
✅ load_and_override
✅ preserves_all_fields
```

### test_simple_agent.py （18 个测试）

```python
✅ from_preset (default)
✅ from_preset (vla_plus)
✅ initialization_with_config
✅ initialization_with_providers
✅ has_all_subsystems (perception, cognition, execution, feedback, loop)
✅ perception_is_callable
✅ cognition_is_callable
✅ execution_is_callable
✅ loop_is_initialized
✅ run_task
✅ run_task_returns_result
✅ multiple_tasks
✅ minimal_code (易用性)
✅ from_preset_is_idiomatic
✅ supports_default_preset
✅ supports_vla_plus_preset
✅ supports_multiple_presets
✅ full_workflow
✅ config_accessible
```

---

## 🎯 GREEN 阶段 (即将开始)

现在需要编写实施代码，使所有 54 个测试都通过。

### 优先级 1：基础类型 (agents/core/types.py)

**应该实现的**：

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import numpy as np

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

**验证命令**：
```bash
python3 -m pytest tests/unit/test_core_types.py -v
```

**预期结果**：11 个测试通过 ✅

---

### 优先级 2：代理主循环 (agents/core/agent_loop.py)

**应该实现的**：

```python
class RobotAgentLoop:
    """核心代理循环"""

    def __init__(self, llm_provider, perception_provider, executor, config):
        self.llm_provider = llm_provider
        self.perception_provider = perception_provider
        self.executor = executor
        self.config = config
        self.step_count = 0

    async def step(self) -> SkillResult:
        """执行一步 observe-think-act 循环"""
        if self.step_count >= self.config.max_steps:
            return SkillResult(success=False, message="Max steps exceeded")

        obs = await self.perception_provider.get_observation()
        action = await self.llm_provider.generate_action(obs)
        result = await self.executor.execute(action)

        self.step_count += 1
        return result
```

**验证命令**：
```bash
python3 -m pytest tests/unit/test_core_agent_loop.py -v
```

**预期结果**：9 个测试通过 ✅

---

### 优先级 3：配置管理 (agents/config/manager.py)

**应该实现的**：

```python
import yaml
import os
from pydantic import BaseModel

class AgentConfigSchema(BaseModel):
    agent_name: str = "default_agent"
    max_steps: int = 100
    llm_model: str = "qwen"
    perception_enabled: bool = True

class ConfigManager:
    """统一配置管理"""

    @classmethod
    def load_preset(cls, preset_name: str):
        preset_file = os.path.join(
            os.path.dirname(__file__),
            'presets',
            f'{preset_name}.yaml'
        )
        config = cls.load_yaml(preset_file)
        return cls._apply_env_overrides(config)

    @classmethod
    def load_yaml(cls, filepath: str):
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return AgentConfigSchema(**data)

    @classmethod
    def create(cls, **kwargs):
        return AgentConfigSchema(**kwargs)

    @staticmethod
    def _apply_env_overrides(config):
        for key, value in os.environ.items():
            if key.startswith('AGENT_'):
                attr_name = key[6:].lower()
                if hasattr(config, attr_name):
                    setattr(config, attr_name, value)
        return config
```

**还需要**：
- agents/config/schemas.py (Pydantic schemas)
- agents/config/presets/default.yaml
- agents/config/presets/vla_plus.yaml

**验证命令**：
```bash
python3 -m pytest tests/unit/test_config_manager.py -v
```

**预期结果**：16 个测试通过 ✅

---

### 优先级 4：快速开始接口 (agents/simple_agent.py)

**应该实现的**：

```python
class SimpleAgent:
    """简化的代理接口"""

    def __init__(self, config, llm_provider=None,
                 perception_provider=None, executor=None):
        self.config = config
        self.perception = perception_provider or PerceptionProvider(config)
        self.cognition = CognitionEngine(config, llm_provider)
        self.execution = executor or Executor(config)
        self.feedback = VDMAnalyzer()
        self.loop = RobotAgentLoop(
            llm_provider=self.cognition.llm,
            perception_provider=self.perception,
            executor=self.execution,
            config=config
        )

    @classmethod
    def from_preset(cls, preset_name: str = "default"):
        config = ConfigManager.load_preset(preset_name)
        return cls(config)

    async def run_task(self, task: str):
        return await self.loop.step()
```

**验证命令**：
```bash
python3 -m pytest tests/unit/test_simple_agent.py -v
```

**预期结果**：18 个测试通过 ✅

---

## 📂 需要创建的文件和目录

```
agents/
├── core/                              # 新建
│   ├── __init__.py
│   ├── types.py                       # 优先级 1
│   ├── agent_loop.py                  # 优先级 2
│   ├── messages.py                    # 可选（先不做）
│   └── exceptions.py                  # 可选（先不做）
│
├── config/                            # 新建
│   ├── __init__.py
│   ├── manager.py                     # 优先级 3
│   ├── schemas.py                     # 优先级 3
│   └── presets/                       # 新建
│       ├── default.yaml               # 优先级 3
│       └── vla_plus.yaml              # 优先级 3
│
├── simple_agent.py                    # 优先级 4
│
└── [其他现有目录保持不变]
```

---

## 🚀 GREEN 阶段工作流

### 步骤 1：创建目录和 __init__.py

```bash
mkdir -p agents/core
mkdir -p agents/config/presets
touch agents/core/__init__.py
touch agents/config/__init__.py
```

### 步骤 2：编写 agents/core/types.py

运行测试验证：
```bash
python3 -m pytest tests/unit/test_core_types.py -v
```

预期：11/11 通过 ✅

### 步骤 3：编写 agents/core/agent_loop.py

运行测试验证：
```bash
python3 -m pytest tests/unit/test_core_agent_loop.py -v
```

预期：9/9 通过 ✅

### 步骤 4：编写 agents/config/

创建：
- agents/config/schemas.py
- agents/config/manager.py
- agents/config/presets/default.yaml
- agents/config/presets/vla_plus.yaml

运行测试验证：
```bash
python3 -m pytest tests/unit/test_config_manager.py -v
```

预期：16/16 通过 ✅

### 步骤 5：编写 agents/simple_agent.py

运行测试验证：
```bash
python3 -m pytest tests/unit/test_simple_agent.py -v
```

预期：18/18 通过 ✅

### 步骤 6：全部测试

```bash
python3 -m pytest tests/unit/test_core_*.py tests/unit/test_config_manager.py tests/unit/test_simple_agent.py -v
```

预期：54/54 通过 ✅

---

## 💡 重要提示

### TDD 核心原则

1. **不要提前创建文件** — 让测试失败指导你创建正确的位置和名称
2. **不要过度设计** — 只写通过测试所需的最少代码
3. **保持测试绿色** — 每次编写代码后运行测试
4. **逐步构建** — 一个模块接一个模块

### 验证步骤

```bash
# 编写完 types.py 后，立即运行：
python3 -m pytest tests/unit/test_core_types.py -v

# 如果全部通过，提交代码：
git add agents/core/types.py
git commit -m "feat(core): implement basic types (RobotObservation, SkillResult, AgentConfig)"

# 然后继续下一个模块
```

---

## 📋 第 1 周完成清单

- [x] RED 阶段：编写 54 个失败的测试 ✅
- [ ] GREEN 阶段：编写实施代码使所有测试通过
  - [ ] agents/core/types.py (11 个测试)
  - [ ] agents/core/agent_loop.py (9 个测试)
  - [ ] agents/config/ (16 个测试)
  - [ ] agents/simple_agent.py (18 个测试)
- [ ] REFACTOR 阶段：清理代码，保持测试通过
- [ ] 提交所有代码到 git

---

**当前状态**: ✅ RED 阶段完成，准备进入 GREEN 阶段

**下一步**: 开始编写 agents/core/types.py
