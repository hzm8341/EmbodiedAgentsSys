:orphan:

# Agent+Skill+VLA 通用具身智能机器人框架整合方案

**版本**: v1.0  
**日期**: 2026-03-03  
**状态**: 正式发布

---

## 一、执行摘要

本报告整合了 `framework_evaluation.md` 和 `technical_analysis_vla_comparison_v1.0_20260303_AI.md` 两个文档的评估结论，制定了基于 ROS2 的通用具身智能机器人框架的详细开发计划。

**核心结论**：

- **ros-agents（EmbodiedAgents）架构更成熟**：组件化设计、异步架构、事件驱动、生产级框架
- **agent_skill_VLA_ROS2 VLA 集成更丰富**：支持 ACT、GR00T、LeRobot 等多种 VLA 模型
- **推荐融合方案**：以 ros-agents 为基础框架，集成 agent_skill_VLA_ROS2 的多 VLA 支持

**推荐策略**：

- 短期：以 ros-agents 为基础框架，扩展其 VLA 支持
- 长期：构建统一框架，汲取两个项目的精华

---

## 二、项目背景与定位

### 2.1 项目概述

| 项目 | 路径 | 定位 |
|------|------|------|
| agent_skill_VLA_ROS2 | `/media/hzm/data_disk/agent_skill_VLA_ROS2` | 基于 RAI 框架的 VLA 具身智能系统 |
| ros-agents | `/media/hzm/data_disk/ros-agents` | 生产级 Physical AI 编排框架（EmbodiedAgents） |

### 2.2 核心框架信息

| 维度 | agent_skill_VLA_ROS2 (AROS) | ros-agents (EmbodiedAgents) |
|------|------------------------------|----------------------------|
| 上游框架 | RAI (RobotecAI) | Sugarcoat + ROS2 原生 |
| 许可证 | Apache 2.0 | MIT |
| 成熟度 | 定制开发中 | 正式发布 (v1.0+) |
| 社区 | ROS Embodied AI Group + GitHub | Automatika + Inria + Discord |
| 文档 | 较少 | 完善（Web 文档） |

---

## 三、架构设计对比

### 3.1 核心抽象层次

#### ros-agents（四层架构）

```
Launcher → Component Graph (异步)
         → Skills Layer (封装)
         → Model Client (多后端)
```

- **Component**：基础组件（LLM, VLM, Vision, VLA 等）
- **Skills Layer**：组件封装为可复用技能
- **Model Client**：Ollama, RoboML, LeRobot, vLLM 等多后端
- **执行模型**：异步非阻塞（async/await）
- **编排方式**：有向无环图（DAG）
- **通信模式**：Topic + Action Server

#### agent_skill_VLA_ROS2（四层架构）

```
TaskPlanner → Skill → VLA → ROS2Connector
```

- **TaskPlanner**：任务规划层，支持 LLM 规划和规则路由
- **Skill**：原子动作封装（GraspSkill, PlaceSkill, ReachSkill 等）
- **VLA**：统一 VLA 接口（LeRobotVLA, ACT, GR00T 等）
- **ROS2Connector**：ROS2 通信抽象
- **执行模型**：同步阻塞式（Skill.execute()）
- **编排方式**：线性任务流（Task → Skills 序列）

### 3.2 设计理念差异

| 方面 | agent_skill_VLA_ROS2 | ros-agents |
|------|---------------------|------------|
| 执行模型 | 同步阻塞式 | 异步非阻塞 |
| 编排方式 | 线性任务流 | 有向无环图 |
| 状态管理 | SkillState 枚举 | SkillStatus + Event 驱动 |
| 组件关系 | Skill 组合 VLA | Component 组合 Model Client |
| 通信模式 | 同步调用 + ROS Topic | Topic + Action Server |

---

## 四、功能特性对比

| 特性 | agent_skill_VLA_ROS2 | ros-agents | 评价 |
|------|---------------------|------------|------|
| VLA 支持 | ✅ LeRobot, ACT, GR00T | ✅ LeRobot | agent_skill_VLA_ROS2 完胜 |
| 多模态输入 | ✅ RGB + Depth + Proprio | ✅ Image + RGBD + JointState | 两者相当 |
| 任务规划 | ✅ LLM 规划 + 规则路由 | ✅ Component 组合 | 两者相当 |
| 技能注册 | ✅ SkillRegistry | ✅ SkillRegistry | 两者相当 |
| 动态 Web UI | ❌ | ✅ FastHTML 自动生成 | ros-agents 完胜 |
| 时空记忆 | ✅ SpatioTemporalMemory | ✅ Semantic Map | ros-agents 更先进 |
| 事件系统 | ✅ EventBus | ✅ ROS2 Events | ros-agents 更成熟 |
| 动作执行 | ✅ 同步执行 | ✅ Action Server | ros-agents 更灵活 |
| 安全限制 | ⚠️ 基础限制 | ✅ Joint Limits + Action Capping | ros-agents 更完善 |

---

## 五、代码质量对比

### 5.1 代码规范

| 维度 | agent_skill_VLA_ROS2 | ros-agents |
|------|----------------------|------------|
| 类型注解 | 广泛使用 | 广泛使用 |
| 代码检查 | 基础配置 | 完整 ruff 配置 |
| 文档字符串 | 部分缺失 | 详细 docstring |
| 配置管理 | attrs/YAML | attrs 声明式配置 |
| 错误处理 | 基础实现 | 完善的异常处理 |
| 测试覆盖 | 部分测试 | 较完整测试套件 |

### 5.2 项目成熟度

| 维度 | agent_skill_VLA_ROS2 | ros-agents |
|------|----------------------|------------|
| 文档完整性 | 100+ 文档，但部分陈旧 | 完整中英文文档 |
| 示例代码 | 基础示例 | 丰富示例 |
| 部署指南 | 基础说明 | 详细部署文档 |
| 社区活跃度 | 基于 RAI 社区 | 独立项目，持续更新 |
| 生产就绪度 | 开发中 | 生产级设计 |

---

## 六、VLA 集成能力深度分析

### 6.1 agent_skill_VLA_ROS2 的 VLA 优势

**核心亮点**：

1. **多模型支持**：ACT（Transformer+时序聚合）、GR00T（Diffusion 模型）、LeRobot（Policy Server）
2. **统一接口**：UnifiedVLA 抽象层，统一不同 VLA 模型的调用方式
3. **动态切换**：VLAManager 支持运行时切换不同 VLA 模型
4. **配置映射**：skill→VLA、scene→VLA 的灵活映射配置

**UnifiedVLA 接口设计**：

```python
class UnifiedVLA(ABC):
    @abstractmethod
    def reset(self): ...

    @abstractmethod
    def act(self, observation, skill_token, termination) -> np.ndarray: ...

    @abstractmethod
    def execute(self, action) -> Dict: ...
```

**VLAManager 管理多个 VLA**：

```python
class VLAManager:
    def register(self, name: str, vla: UnifiedVLA): ...
    def get_skill_vla(self, skill_name: str) -> Optional[UnifiedVLA]: ...
    def load_from_config(self, config_path): ...  # YAML 配置
```

### 6.2 ros-agents 的 VLA 现状

**当前状态**：

- **仅支持 LeRobot**：VLA Component 目前仅实现 LeRobot 客户端
- **功能完整**：支持关节限位、动作聚合、多种终止模式
- **安全机制**：基于 URDF 的关节安全限制
- **架构优势**：使用 ROS2 Action Server 模式，支持目标取消、反馈

---

## 七、综合评估得分

| 评估维度 | agent_skill_VLA_ROS2 | ros-agents | 权重 | 备注 |
|----------|---------------------|------------|------|------|
| 架构设计 | 7/10 | 9/10 | 25% | ros-agents 组件化设计更优 |
| 代码质量 | 6/10 | 8/10 | 20% | ros-agents 代码规范更好 |
| VLA 支持 | 9/10 | 5/10 | 25% | agent_skill_VLA_ROS2 明显优势 |
| 扩展性 | 7/10 | 9/10 | 15% | ros-agents 架构更易扩展 |
| 文档生态 | 6/10 | 8/10 | 10% | ros-agents 文档更完善 |
| 部署便利 | 5/10 | 7/10 | 5% | 两者都有复杂度 |
| **加权总分** | **7.1** | **7.6** | 100% | ros-agents 略胜 |

---

## 八、整合目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     ros-agents (基础框架)                        │
├─────────────────────────────────────────────────────────────────┤
│  Launcher → Component Graph → Model Client → LeRobot/vLLM/Ollama │
│                           ↓                                      │
│                      Skills Layer                                │
│             (skill_registry + SkillChain)                       │
└─────────────────────────────────────────────────────────────────┘
                            ↑
              ┌─────────────┴─────────────┐
              │  整合 agent_skill_VLA_ROS2   │
              ├─────────────────────────────────┤
              │  1. VLA Adapter Layer          │
              │  2. Skill Execution Framework │
              │  3. Task Planner              │
              │  4. Event Bus                 │
              │  5. ROS2 Connector            │
              └─────────────────────────────────┘
```

---

## 九、详细开发计划

### 阶段一：基础设施（1-2 周）

#### 任务清单

| 序号 | 任务 | 描述 | 预估工作量 | 依赖 |
|------|------|------|----------|------|
| 1.1 | 环境搭建 | 安装 ros-agents、Sugarcoat 依赖 | 2 天 | - |
| 1.2 | VLA Adapter 基类 | 创建 `VLAAdapterBase` 抽象 | 2 天 | - |
| 1.3 | LeRobot 适配器 | 迁移 `LeRobotVLA` 到 ros-agents | 3 天 | 1.2 |
| 1.4 | Skill 执行框架 | 创建 `VLASkill` 基类 | 3 天 | - |
| 1.5 | 配置管理 | VLA/Skill 相关配置 | 1 天 | - |

#### 详细任务说明

**1.1 环境搭建**

```bash
# 安装 ros-agents
cd /media/hzm/data_disk/ros-agents
pip install -e .

# 安装 Sugarcoat
cd /media/hzm/data_disk
git clone https://github.com/automatika-robotics/sugarcoat
cd sugarcoat
pip install -e .

# 验证安装
python -c "from agents import VLA; print('ros-agents OK')"
python -c "from sugarcoat import Node; print('Sugarcoat OK')"
```

**1.2 VLA Adapter 基类**

```python
# agents/clients/vla_adapters/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np

class VLAAdapterBase(ABC):
    """VLA 适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False

    @abstractmethod
    def reset(self):
        """重置 VLA 状态"""
        pass

    @abstractmethod
    def act(
        self,
        observation: Dict[str, Any],
        skill_token: str,
        termination: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """生成动作"""
        pass

    @abstractmethod
    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作"""
        pass

    @property
    @abstractmethod
    def action_dim(self) -> int:
        """动作维度"""
        pass
```

**1.3 LeRobot 适配器**

```python
# agents/clients/vla_adapters/lerobot.py

from .base import VLAAdapterBase
from agents.clients.lerobot import LeRobotClient
from agents.models import LeRobotPolicy

class LeRobotVLAAdapter(VLAAdapterBase):
    """LeRobot VLA 适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None
        self._init_client()

    def _init_client(self):
        model = LeRobotPolicy(
            name=self.config["policy_name"],
            checkpoint=self.config["checkpoint"],
            features=self.config.get("features"),
        )
        self._client = LeRobotClient(
            model=model,
            host=self.config.get("host", "127.0.0.1"),
            port=self.config.get("port", 8080),
        )
        self._initialized = True
```

**1.4 Skill 执行框架**

```python
# agents/skills/vla_skill.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio

class SkillStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class SkillResult:
    status: SkillStatus
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class VLASkill(ABC):
    """基于 VLA 的 Skill 抽象基类"""

    required_inputs: List[str] = []
    produced_outputs: List[str] = []
    default_vla: Optional[str] = None

    def __init__(self, vla_adapter: VLAAdapterBase = None, **kwargs):
        self.vla = vla_adapter
        self._status = SkillStatus.IDLE

    @abstractmethod
    def build_skill_token(self) -> str:
        """构建 VLA 推理用的任务描述"""
        pass

    @abstractmethod
    def check_preconditions(self, observation: Dict) -> bool:
        """检查执行前置条件"""
        pass

    @abstractmethod
    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件"""
        pass

    async def execute(self, observation: Dict) -> "SkillResult":
        """执行 Skill（异步封装同步逻辑）"""
        pass
```

**1.5 配置管理**

```yaml
# config/vla_config.yaml

vla_models:
  lerobot_aloha:
    type: "lerobot"
    policy_name: "aloha_policy"
    checkpoint: "lerobot/act_aloha_sim_transfer_cube_human"
    host: "127.0.0.1"
    port: 8080
    joint_names_map:
      joint_0: "panda_joint1"
      joint_1: "panda_joint2"
      # ...
    camera_inputs_map:
      top:
        name: "/camera/top/image_raw"

skill_vla_mapping:
  grasp: "lerobot_aloha"
  place: "lerobot_aloha"
  reach: "lerobot_aloha"
  move: "lerobot_aloha"
  inspect: "lerobot_aloha"
```

---

### 阶段二：Core Skills（2-3 周）

#### 任务清单

| 序号 | 任务 | 描述 | 预估工作量 | 依赖 |
|------|------|------|----------|------|
| 2.1 | GraspSkill | 抓取技能 | 3 天 | 1.4 |
| 2.2 | PlaceSkill | 放置技能 | 2 天 | 1.4 |
| 2.3 | ReachSkill | 到达技能 | 2 天 | 1.4 |
| 2.4 | MoveSkill | 关节运动技能 | 2 天 | 1.4 |
| 2.5 | InspectSkill | 检查技能 | 2 天 | 1.4 |

#### 详细任务说明

**2.1 GraspSkill 实现**

```python
# agents/skills/manipulation/grasp.py

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any

class GraspSkill(VLASkill):
    """抓取技能"""

    required_inputs = ["object_name", "observation"]
    produced_outputs = ["success", "grasp_position"]

    def __init__(self, object_name: str, **kwargs):
        super().__init__(**kwargs)
        self.object_name = object_name

    def build_skill_token(self) -> str:
        return f"grasp {self.object_name}"

    def check_preconditions(self, observation: Dict) -> bool:
        # 检查物体是否在视野内
        return "object_detected" in observation

    def check_termination(self, observation: Dict) -> bool:
        # 检查是否抓取成功（可通过力传感器或夹爪状态判断）
        return observation.get("grasp_success", False)

    async def execute(self, observation: Dict) -> SkillResult:
        try:
            skill_token = self.build_skill_token()

            for step in range(self.max_steps):
                # 检查终止条件
                if self.check_termination(observation):
                    return SkillResult(
                        status=SkillStatus.SUCCESS,
                        output={"grasp_success": True}
                    )

                # VLA 推理
                action = self.vla.act(observation, skill_token)

                # 执行动作
                result = self.vla.execute(action)

                # 更新观察
                observation = await self.get_observation()

            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={"grasp_success": True, "steps": self.max_steps}
            )

        except Exception as e:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=str(e)
            )
```

---

### 阶段三：高级功能（2-3 周）

#### 任务清单

| 序号 | 任务 | 描述 | 预估工作量 | 依赖 |
|------|------|------|----------|------|
| 3.1 | TaskPlanner | 任务规划器 | 3 天 | 2.x |
| 3.2 | Event Bus | 事件总线 | 2 天 | - |
| 3.3 | Semantic Router | 语义路由 | 2 天 | - |
| 3.4 | LLM 规划集成 | Ollama 规划 | 2 天 | 3.1 |
| 3.5 | ACT/GR00T 适配器 | 扩展 VLA 支持 | 3 天 | 1.2 |

#### 详细任务说明

**3.1 TaskPlanner 实现**

```python
# agents/planner/task_planner.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PlanningStrategy(Enum):
    RULE_BASED = "rule_based"
    LLM = "llm"

@dataclass
class Task:
    name: str
    skills: List[str]
    parameters: Dict[str, Any] = None

class TaskPlanner:
    """任务规划器"""

    def __init__(
        self,
        llm_client=None,
        semantic_router=None,
        event_bus=None,
        strategy: PlanningStrategy = PlanningStrategy.RULE_BASED
    ):
        self.llm_client = llm_client
        self.semantic_router = semantic_router
        self.event_bus = event_bus
        self.strategy = strategy

    async def plan(self, instruction: str) -> Task:
        """从自然语言指令生成任务"""
        if self.strategy == PlanningStrategy.LLM:
            return await self._plan_with_llm(instruction)
        else:
            return self._plan_with_rules(instruction)

    async def _plan_with_llm(self, instruction: str) -> Task:
        """使用 LLM 进行任务规划"""
        prompt = f"""
        给定用户指令: "{instruction}"
        请规划执行此任务所需的技能序列。
        可用技能: grasp, place, reach, move, inspect
        返回 JSON 格式: {{"skills": ["skill1", "skill2", ...], "parameters": {{}}}}
        """
        response = await self.llm_client.prompt(prompt)
        # 解析响应并生成 Task
        return Task(name=instruction, skills=[], parameters={})

    def _plan_with_rules(self, instruction: str) -> Task:
        """使用规则进行任务规划"""
        # 简单的规则匹配
        if "抓取" in instruction and "放置" in instruction:
                name=            return Task(
instruction,
                skills=["reach", "grasp", "reach", "place"]
            )
        # ... 更多规则
```

---

### 阶段四：优化与测试（1-2 周）

#### 任务清单

| 序号 | 任务 | 描述 | 预估工作量 | 依赖 |
|------|------|------|----------|------|
| 4.1 | 单元测试 | 各模块测试 | 3 天 | 1-3 |
| 4.2 | 集成测试 | 端到端测试 | 3 天 | 4.1 |
| 4.3 | 性能优化 | 异步性能、内存优化 | 2 天 | 4.2 |
| 4.4 | 文档完善 | API 文档、使用指南 | 2 天 | - |

---

## 十、代码迁移对照表

| agent_skill_VLA_ROS2 原路径 | ros-agents 目标路径 | 整合方式 |
|----------------------------|-------------------|---------|
| `aros/vla/lerobot_vla.py` | `agents/clients/vla_adapters/lerobot.py` | 封装适配器 |
| `aros/skills/base.py` | `agents/skills/vla_skill.py` | 基类继承 |
| `aros/skills/grasp.py` | `agents/skills/manipulation/grasp.py` | 完整迁移 |
| `aros/skills/place.py` | `agents/skills/manipulation/place.py` | 完整迁移 |
| `src/rai_core/rai/skills/vla/manager.py` | `agents/clients/vla_manager.py` | 重构异步 |
| `aros/events/bus.py` | `agents/events/bus.py` | 新增模块 |
| `aros/planner/task.py` | `agents/planner/task.py` | 重构异步 |

---

## 十一、关键整合点示例

### 11.1 VLA Component 与 Skill 集成

```python
# 示例：在 ros-agents Component 中调用整合后的 Skill

from agents.components.vla import VLA
from agents.skills.manipulation import GraspSkill
from agents.clients.vla_adapters import LeRobotVLAAdapter

class ManipulationAgent:
    def __init__(self, vla_component: VLA):
        self.vla = vla_component
        self.vla_adapter = LeRobotVLAAdapter({
            "policy_name": "panda_policy",
            "checkpoint": "lerobot/act_..."
        })

    async def execute_grasp(self, object_name: str):
        # 创建 Skill
        skill = GraspSkill(
            vla_adapter=self.vla_adapter,
            object_name=object_name
        )

        # 执行 Skill
        result = await skill.execute(
            observation=await self.vla.get_observation()
        )

        return result
```

### 11.2 TaskPlanner 与 Component Graph 集成

```python
# 示例：在 ros-agents 中使用 TaskPlanner

from agents.planner import TaskPlanner
from agents.skills.manipulation import GraspSkill, PlaceSkill
from agents.clients.ollama import OllamaClient

# 配置 Planner
planner = TaskPlanner(
    llm_client=OllamaClient(...),
    strategy=PlanningStrategy.LLM
)

# 从指令生成任务
task = await planner.plan("抓取杯子放到桌子上")

# 执行任务
for skill_name in task.skills:
    if skill_name == "grasp":
        result = await GraspSkill(...).execute(observation)
    elif skill_name == "place":
        result = await PlaceSkill(...).execute(observation)
```

---

## 十二、风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| 同步/异步模式冲突 | 将 agent_skill_VLA_ROS2 的逻辑封装为 async |
| 依赖冲突 | 使用虚拟环境隔离 |
| 性能瓶颈 | 复用 ros-agents 的异步架构 |
| 测试覆盖 | 编写完整的集成测试 |
| RAI 框架依赖 | 移除 RAI 依赖，独立实现 VLA 接口 |

---

## 十三、验证计划

### 13.1 单元测试清单

| 模块 | 测试用例 | 验证点 |
|------|---------|--------|
| VLA Adapter | test_lerobot_adapter | 初始化、推理、动作接收 |
| VLA Adapter | test_adapter_factory | 多类型适配器创建 |
| Skill | test_grasp_skill_preconditions | 前置条件检查 |
| Skill | test_grasp_skill_termination | 终止条件判断 |
| Planner | test_llm_planning | LLM 规划生成 |
| Planner | test_rule_planning | 规则规划生成 |

### 13.2 集成测试清单

| 场景 | 测试用例 | 验证点 |
|------|---------|--------|
| 抓取任务 | test_grasp_integration | 端到端抓取流程 |
| 放置任务 | test_place_integration | 端到端放置流程 |
| 多技能链 | test_skill_chain | 技能链顺序执行 |
| VLA 切换 | test_vla_switching | 运行时 VLA 切换 |
| 任务规划 | test_full_planning | 指令到执行全流程 |

---

## 十四、开发里程碑

### M1：基础设施完成（第 2 周周末）

- [ ] 环境搭建完成
- [ ] VLA Adapter 基类完成
- [ ] LeRobot 适配器完成
- [ ] 配置系统可用

### M2：Core Skills 完成（第 5 周周末）

- [ ] GraspSkill 完成并测试通过
- [ ] PlaceSkill 完成并测试通过
- [ ] ReachSkill 完成并测试通过
- [ ] MoveSkill 完成并测试通过
- [ ] InspectSkill 完成并测试通过

### M3：高级功能完成（第 8 周周末）

- [ ] TaskPlanner 完成并测试通过
- [ ] Event Bus 完成
- [ ] Semantic Router 完成
- [ ] LLM 规划集成完成
- [ ] ACT/GR00T 适配器完成

### M4：发布候选（第 10 周周末）

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 性能优化完成
- [ ] 文档完成

---

## 十五、资源需求

### 15.1 人力资源

| 角色 | 数量 | 主要职责 |
|------|------|---------|
| 架构师 | 1 | 架构设计、技术决策 |
| ROS2 工程师 | 2 | 组件开发、集成测试 |
| AI 工程师 | 1 | VLA 集成、模型适配 |
| 测试工程师 | 1 | 测试用例、持续集成 |

### 15.2 硬件资源

| 资源 | 数量 | 用途 |
|------|------|------|
| GPU 服务器 | 1 | VLA 模型推理 |
| 机械臂平台 | 1 | 真机测试 |
| 深度相机 | 2 | 视觉输入 |

### 15.3 软件依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ROS2 Humble | >= 1.0 | 机器人操作系统 |
| Python | 3.10+ | 运行环境 |
| Sugarcoat | >= 0.5.0 | ROS2 抽象层 |
| LeRobot | latest | VLA 策略服务器 |

---

## 十六、总结

### 16.1 整合思路

1. **保持 ros-agents 的异步架构**：将 agent_skill_VLA_ROS2 的同步逻辑异步化
2. **复用 VLA 适配层**：直接迁移 LeRobotVLA 等适配器
3. **扩展 Skills 库**：将具体 Skill 完整迁移到 ros-agents
4. **新增规划层**：TaskPlanner 作为独立模块集成

### 16.2 预期成果

- 统一的 Agent+Skill+VLA 通用具身智能框架
- 支持多种 VLA 模型（LeRobot、ACT、GR00T）
- 丰富的预置 Skills（Grasp、Place、Reach、Move、Inspect）
- 灵活的任务规划能力（规则 + LLM）
- 生产级框架特性（Web UI、监控、事件驱动）

### 16.3 后续行动

- [ ] 与团队讨论评估结论
- [ ] 确认开发计划和时间线
- [ ] 开始环境搭建
- [ ] 成立专项开发小组

---

*文档版本: v1.0*  
*创建日期: 2026-03-03*  
*基于文档: framework_evaluation.md + technical_analysis_vla_comparison_v1.0_20260303_AI.md*
