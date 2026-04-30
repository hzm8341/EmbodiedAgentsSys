:orphan:

# PhyAgentOS Integration Design - EmbodiedAgentsSys v3.0

**Version**: 1.0
**Date**: 2026-04-09
**Status**: Draft
**Author**: Claude Code

---

## 1. 背景与目标

### 1.1 项目背景

EmbodiedAgentsSys 和 PhyAgentOS 都是具身智能框架，但设计理念各有优势：

| 维度 | EmbodiedAgentsSys | PhyAgentOS |
|------|-------------------|------------|
| 安全机制 | Seven Iron Rules + Two-Level Validation | LESSONS.md + Critic |
| 软硬件通信 | 内存数据流 | Markdown 文件 (State-as-a-File) |
| 硬件抽象 | Tool Adapter | HAL BaseDriver + 插件 |
| 多机器人 | Event Bus 扩展 | Fleet Workspace 拓扑 |
| 测试覆盖 | 720+ 测试 | 基础测试 |
| VLA 集成 | 多适配器 (ACT/GR00T/LeRobot) | ReKep 集成 |

### 1.2 整合目标

通过渐进式融合，EmbodiedAgentsSys 吸收 PhyAgentOS 的最佳特性：

1. **HAL 硬件抽象层** - 标准化的硬件驱动接口
2. **State-as-a-File 协议** - 透明性和可审计性
3. **Skills Loader** - 技能热加载和复用
4. **Critic Validator** - 动作校验和经验避坑
5. **Fleet Topology** - 多机器人协同

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    EmbodiedAgentsSys v3.0                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐    ┌───────────────────────────────────────┐ │
│  │  Perception   │    │         Cognition Layer                │ │
│  │   Layer       │    │  ├─ Planning Layer                      │ │
│  │               │    │  ├─ Reasoning Layer                     │ │
│  │ RobotObserv.  │    │  ├─ Learning Layer                      │ │
│  └───────────────┘    │  └─ Critic Validator (NEW)             │ │
│                       └───────────────────────────────────────┘ │
│  ┌───────────────┐    ┌───────────────────────────────────────┐ │
│  │   Execution   │    │         HAL Layer (NEW)               │ │
│  │    Layer      │    │  ├─ HAL Watchdog                       │ │
│  │               │    │  ├─ BaseDriver Interface               │ │
│  │ Two-Level     │    │  └─ Driver Registry                    │ │
│  │ Validation    │    └───────────────────────────────────────┘ │
│  └───────────────┘    ┌───────────────────────────────────────┐ │
│                       │       State Protocol (NEW)              │ │
│  ┌───────────────┐    │  ├─ ACTION.md                          │ │
│  │   Feedback    │    │  ├─ ENVIRONMENT.md                    │ │
│  │    Layer      │    │  ├─ EMBODIED.md                       │ │
│  │               │    │  └─ LESSONS.md                        │ │
│  │ Audit Trail   │    └───────────────────────────────────────┘ │
│  └───────────────┘    ┌───────────────────────────────────────┐ │
│                       │     Skills System (ENHANCED)           │ │
│  ┌───────────────┐    │  ├─ Skill Loader (NEW)                │ │
│  │    Fleet      │    │  ├─ Skill Registry (NEW)               │ │
│  │  Topology     │    │  └─ Skill Base (NEW)                   │ │
│  │   (NEW)       │    └───────────────────────────────────────┘ │
│  └───────────────┘                                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 HAL 层 (新增)

**目录结构**:
```
embodiedagentsys/hal/
├── __init__.py
├── base_driver.py          # BaseDriver 抽象基类
├── driver_registry.py      # 驱动注册表
├── hal_watchdog.py         # 看门狗守护进程
└── drivers/
    ├── __init__.py
    ├── simulation_driver.py
    └── lerobot_driver.py
```

**BaseDriver 接口**:
```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

class BaseDriver(ABC):
    """硬件驱动基类，定义标准化硬件接口"""

    @abstractmethod
    def get_profile_path(self) -> Path:
        """返回机器人 embodiment profile 路径"""
        pass

    @abstractmethod
    def execute_action(self, action_type: str, params: dict) -> str:
        """执行单个动作，返回结果描述"""
        pass

    @abstractmethod
    def get_scene(self) -> dict[str, dict]:
        """获取当前场景状态"""
        pass

    def load_scene(self, scene: dict[str, dict]) -> None:
        """加载场景状态"""
        pass

    def connect(self) -> bool:
        """连接硬件"""
        return True

    def disconnect(self) -> None:
        """断开硬件连接"""
        pass

    def is_connected(self) -> bool:
        """检查连接状态"""
        return False

    def health_check(self) -> dict:
        """健康检查"""
        return {"status": "ok"}

    def get_runtime_state(self) -> dict:
        """获取运行时状态"""
        return {}
```

**DriverRegistry**:
```python
class DriverRegistry:
    """驱动注册表，管理所有可用驱动"""

    def __init__(self):
        self._drivers: dict[str, type[BaseDriver]] = {}

    def register(self, name: str, driver_class: type[BaseDriver]) -> None:
        """注册驱动"""
        self._drivers[name] = driver_class

    def get(self, name: str) -> Optional[type[BaseDriver]]:
        """获取驱动类"""
        return self._drivers.get(name)

    def create(self, name: str, **kwargs) -> Optional[BaseDriver]:
        """创建驱动实例"""
        driver_class = self.get(name)
        return driver_class(**kwargs) if driver_class else None

    def list_drivers(self) -> list[str]:
        """列出所有注册驱动"""
        return list(self._drivers.keys())
```

#### 2.2.2 State Protocol (新增)

**目录结构**:
```
embodiedagentsys/state/
├── __init__.py
├── state_manager.py          # 状态管理器
├── workspace.py              # Workspace 上下文
├── protocols/
│   ├── __init__.py
│   ├── action_protocol.py
│   ├── environment_protocol.py
│   ├── embodied_protocol.py
│   └── lessons_protocol.py
└── templates/
    ├── ACTION.md
    ├── ENVIRONMENT.md
    ├── EMBODIED.md
    └── LESSONS.md
```

**StateManager**:
```python
from pathlib import Path
from typing import Optional, Callable, Awaitable
import asyncio
import json

class StateManager:
    """状态管理器，支持可选的磁盘持久化"""

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        enable_state_files: bool = False
    ):
        """
        Args:
            workspace_path: 工作区路径，默认 ~/.embodiedagents/workspace/
            enable_state_files: 是否启用磁盘持久化，默认 False 保持内存流
        """
        self._workspace = workspace_path or Path.home() / ".embodiedagents" / "workspace"
        self._enable_files = enable_state_files
        self._memory_cache: dict[str, dict] = {}

    @property
    def workspace(self) -> Path:
        return self._workspace

    async def read_protocol(self, protocol_type: str) -> dict:
        """读取协议数据"""
        if self._enable_files:
            return await self._read_file(protocol_type)
        return self._memory_cache.get(protocol_type, {})

    async def write_protocol(self, protocol_type: str, data: dict) -> None:
        """写入协议数据"""
        self._memory_cache[protocol_type] = data
        if self._enable_files:
            await self._write_file(protocol_type, data)

    async def watch_protocol(
        self,
        protocol_type: str,
        callback: Callable[[dict], Awaitable[None]]
    ) -> None:
        """监听协议文件变化"""
        # 实现使用 watchdog 库
        pass

    async def sync_with_hal(self, driver: BaseDriver) -> None:
        """与 HAL Watchdog 同步状态"""
        scene = driver.get_scene()
        await self.write_protocol("environment", scene)
```

#### 2.2.3 Skills System (增强)

**目录结构**:
```
embodiedagentsys/skills/
├── __init__.py
├── skill_loader.py           # 技能加载器 (新增)
├── skill_registry.py          # 技能注册表 (新增)
├── skill_base.py             # 技能基类 (新增)
└── builtin/
    ├── __init__.py
    ├── grasp_skill.py
    ├── move_skill.py
    └── ...
```

**SkillBase**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class SkillContext:
    """技能执行上下文"""
    workspace_path: Path
    embodied_profile: dict
    environment: dict
    lessons: list[dict]

@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    message: str
    data: Any = None
    error: str = None

class Skill(ABC):
    """技能基类"""

    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    @abstractmethod
    async def execute(self, context: SkillContext, **params) -> SkillResult:
        """执行技能"""
        pass

    async def validate(self, params: dict) -> bool:
        """验证参数"""
        return True

    async def load_from_markdown(cls, md_path: Path) -> "Skill":
        """从 Markdown 模板加载"""
        # 解析 SKILL.md 格式
        pass
```

**SkillLoader**:
```python
class SkillLoader:
    """技能加载器，支持热加载"""

    def __init__(self, skills_path: Optional[Path] = None):
        self._skills_path = skills_path or Path(__file__).parent / "builtin"
        self._loaded_skills: dict[str, Skill] = {}

    def load_skill(self, skill_name: str) -> Optional[Skill]:
        """加载技能"""
        if skill_name in self._loaded_skills:
            return self._loaded_skills[skill_name]

        # 尝试从 builtin 加载
        skill_module = importlib.import_module(
            f"embodiedagents.skills.builtin.{skill_name}"
        )
        skill_class = getattr(skill_module, "Skill", None)
        if skill_class:
            skill = skill_class()
            self._loaded_skills[skill_name] = skill
            return skill
        return None

    def load_from_directory(self, dir_path: Path) -> list[Skill]:
        """从目录加载所有技能"""
        skills = []
        for md_file in dir_path.glob("**/*.md"):
            skill = self.load_from_markdown(md_file)
            if skill:
                skills.append(skill)
        return skills

    def reload(self, skill_name: str) -> Optional[Skill]:
        """热重载技能"""
        if skill_name in self._loaded_skills:
            del self._loaded_skills[skill_name]
        return self.load_skill(skill_name)
```

#### 2.2.4 Critic Validator (新增)

**目录结构**:
```
embodiedagentsys/execution/validators/
├── __init__.py
├── critic_validator.py           # Critic 校验器 (新增)
├── embodied_constraint_checker.py # 约束检查 (新增)
└── lessons_checker.py            # 经验检查 (新增)
```

**CriticValidator**:
```python
class CriticValidator:
    """动作 Critic 校验器"""

    def __init__(
        self,
        embodied_profile: dict,
        lessons: list[dict]
    ):
        self._embodied = embodied_profile
        self._lessons = lessons

    async def validate(self, action: ActionProposal) -> ValidationResult:
        """
        校验动作提案

        1. 检查动作类型是否在 EMBODIED.md 支持列表中
        2. 检查参数是否在安全范围内
        3. 查询 LESSONS.md 避免重复失败
        """
        # 约束检查
        constraint_result = await self._check_constraints(action)
        if not constraint_result.valid:
            return ValidationResult(
                valid=False,
                reason=constraint_result.reason
            )

        # 经验检查
        lesson_result = await self._check_lessons(action)
        if not lesson_result.valid:
            return ValidationResult(
                valid=False,
                reason=lesson_result.reason,
                warning="This action previously failed"
            )

        return ValidationResult(valid=True)

    async def _check_constraints(self, action: ActionProposal) -> CheckResult:
        """检查是否满足约束"""
        allowed_actions = self._embodied.get("supported_actions", [])
        if action.action_type not in allowed_actions:
            return CheckResult(
                valid=False,
                reason=f"Action {action.action_type} not in allowed list"
            )
        # 更多约束检查...
        return CheckResult(valid=True)

    async def _check_lessons(self, action: ActionProposal) -> CheckResult:
        """检查历史失败经验"""
        for lesson in self._lessons:
            if self._action_matches_lesson(action, lesson):
                return CheckResult(
                    valid=False,
                    reason=f"Previously failed: {lesson.get('reason')}"
                )
        return CheckResult(valid=True)
```

---

## 3. 目录结构变更

### 3.1 新增目录

```
embodiedagentsys/
├── hal/                              # 新增: HAL 抽象层
│   ├── __init__.py
│   ├── base_driver.py
│   ├── driver_registry.py
│   ├── hal_watchdog.py
│   └── drivers/
│       ├── __init__.py
│       └── simulation_driver.py
├── state/                            # 新增: State Protocol
│   ├── __init__.py
│   ├── state_manager.py
│   ├── workspace.py
│   ├── protocols/
│   │   ├── __init__.py
│   │   ├── action_protocol.py
│   │   ├── environment_protocol.py
│   │   ├── embodied_protocol.py
│   │   └── lessons_protocol.py
│   └── templates/
│       ├── ACTION.md
│       ├── ENVIRONMENT.md
│       ├── EMBODIED.md
│       └── LESSONS.md
└── skills/
    ├── skill_loader.py               # 新增
    ├── skill_registry.py             # 新增
    ├── skill_base.py                 # 新增
    └── builtin/                     # 内置技能
```

### 3.2 现有目录保持不变

```
embodiedagentsys/
├── agents/                           # 保持
├── cognition/                        # 保持
├── execution/                        # 扩展 validators/
├── feedback/                         # 保持
├── channels/                         # 扩展 fleet_bus
├── clients/                          # 保持
├── components/                       # 保持
├── config/                           # 保持
├── data/                             # 保持
├── events/                           # 保持
├── extensions/                       # 保持
├── hardware/                         # 适配到 HAL
├── skills/                           # 扩展
└── tests/                            # 扩展
```

---

## 4. 向后兼容性

### 4.1 API 兼容性

**关键原则**: 现有 API 保持不变，新增功能可选。

```python
# ✅ 现有代码无需修改 - 保持工作
from embodiedagents import SimpleAgent, GripperTool

agent = SimpleAgent.from_preset("default")
result = await agent.run_task("pick up object")

# ✅ 新功能可选启用
from embodiedagents.hal import HALWatcher
from embodiedagents.state import StateManager
from embodiedagents.skills import SkillLoader

# StateManager 默认禁用，保持内存流
config = AgentConfig(
    enable_state_files=False,  # 默认 False
    hal_enabled=False,          # 默认 False
)
```

### 4.2 配置兼容性

```yaml
# config.yaml - 新增可选配置
agent:
  name: "robot_001"
  max_steps: 50

# 新增: HAL 配置
hal:
  enabled: false
  driver: "simulation"
  workspace: "~/.embodiedagents/workspace"

# 新增: State Protocol 配置
state:
  enabled: false
  workspace: "~/.embodiedagents/workspace"
  protocols:
    - action
    - environment
    - embodied
    - lessons

# 新增: Skills 配置
skills:
  auto_load: true
  builtin_path: "embodiedagents/skills/builtin"
  custom_path: "~/.embodiedagents/skills"
```

---

## 5. 实施计划

### Phase 1: 基础设施 (预计 1-2 周)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| HAL BaseDriver | 定义 BaseDriver 接口 | P0 |
| DriverRegistry | 驱动注册表 | P0 |
| SimulationDriver | 仿真驱动实现 | P0 |
| StateManager | 状态管理器基础 | P1 |
| Action Protocol | ACTION.md 协议 | P1 |

**交付物**:
- `embodiedagentsys/hal/base_driver.py`
- `embodiedagentsys/hal/driver_registry.py`
- `embodiedagentsys/hal/drivers/simulation_driver.py`
- `embodiedagentsys/state/state_manager.py`

### Phase 2: 核心功能 (预计 2-3 周)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| CriticValidator | Critic 校验器 | P0 |
| SkillsLoader | 技能加载器 | P1 |
| FleetTopology | Fleet 拓扑支持 | P2 |
| LESSONS Protocol | LESSONS.md 协议 | P1 |

**交付物**:
- `embodiedagentsys/execution/validators/critic_validator.py`
- `embodiedagentsys/skills/skill_loader.py`
- `embodiedagentsys/fleet/`
- `embodiedagentsys/state/protocols/lessons_protocol.py`

### Phase 3: 测试与文档 (预计 1 周)

| 任务 | 描述 | 优先级 |
|------|------|--------|
| HAL 测试 | BaseDriver 实现测试 | P0 |
| State 测试 | 协议读写测试 | P1 |
| Skills 测试 | 技能加载测试 | P1 |
| 集成测试 | 与现有 720+ 测试兼容 | P0 |

**交付物**:
- `tests/test_hal_*.py`
- `tests/test_state_*.py`
- `tests/test_skills_*.py`
- 更新的 ARCHITECTURE.md

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 向后兼容破坏 | 现有用户升级后代码不可用 | 保持 API 不变，新增可选 |
| 性能下降 | 磁盘 IO 影响响应速度 | 默认禁用磁盘持久化 |
| 测试覆盖下降 | 新增代码未充分测试 | 新增独立测试套件 |
| 复杂度增加 | 维护成本上升 | 保持架构清晰，文档完善 |

---

## 7. 成功标准

- [ ] 现有 720+ 测试全部通过
- [ ] 新增 HAL 层可正常工作
- [ ] State-as-a-File 可选启用
- [ ] Skills Loader 可热加载技能
- [ ] Critic Validator 正确校验动作
- [ ] Fleet Topology 支持多实例
- [ ] 向后兼容性保持 100%

---

## 8. 参考

- [PhyAgentOS HAL Design](../PhyAgentOS/hal/base_driver.py)
- [PhyAgentOS Templates](../PhyAgentOS/PhyAgentOS/templates/)
- [EmbodiedAgentsSys Architecture](../ARCHITECTURE.md)
- [PhyAgentOS Plugin Development Guide](../PhyAgentOS/docs/user_development_guide/PLUGIN_DEVELOPMENT_GUIDE.md)

---

*文档版本 1.0 - 2026-04-09*
