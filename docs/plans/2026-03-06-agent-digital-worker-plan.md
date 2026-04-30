:orphan:

# Agent数字员工 - 统一实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于EmbodiedAgentsSys框架，整合VLA支持，开发Agent数字员工的语音示教、上料/预组装、柔性装配三大场景功能

**Architecture:** 采用层级式Agent架构 - 用户层→任务理解层→任务规划层→技能执行层→学习进化层。以ros-agents为基础框架，集成agent_skill_VLA_ROS2的VLA支持，新增任务规划组件、机械臂控制Skill、力控模块。

**Tech Stack:**
- 基础框架: EmbodiedAgentsSys (ROS2 + Python + Sugarcoat)
- 语音: SpeechToText + ASR服务
- 理解: LLM (GPT-4/Claude/Qwen)
- 视觉: Vision组件 + 3DGS重建
- 机械臂: pyAgxArm / ABB EGM / Fanuc J519
- VLA: LeRobot / ACT / GR00T
- 学习: LoRA微调

---

## 阶段一：框架整合与基础设施

### Task 1: 环境搭建与依赖安装

**Files:**
- Modify: `/media/hzm/data_disk/EmbodiedAgentsSys/pyproject.toml`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/config/vla_config.yaml`

**Step 1: 创建环境验证测试**

```python
# tests/test_environment.py
import pytest

def test_embodied_agents_import():
    """验证EmbodiedAgentsSys框架可用"""
    from agents import Agent
    assert Agent is not None

def test_sugarcoat_import():
    """验证Sugarcoat依赖可用"""
    from sugarcoat import Node
    assert Node is not None
```

**Step 2: 运行测试**

Run: `cd /media/hzm/data_disk/EmbodiedAgentsSys && pytest tests/test_environment.py -v`
Expected: 可能 FAIL（需要先安装依赖）

**Step 3: 更新pyproject.toml**

```toml
# pyproject.toml 添加依赖
[project]
dependencies = [
    "sugarcoat>=0.5.0",
    "lerobot>=0.1.0",
    # ... 现有依赖
]
```

**Step 4: 验证安装**

Run: `pip install -e /media/hzm/data_disk/EmbodiedAgentsSys && pytest tests/test_environment.py -v`
Expected: PASS

---

### Task 2: VLA Adapter 基类开发

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/clients/vla_adapters/base.py`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/clients/vla_adapters/__init__.py`
- Test: `tests/test_vla_adapter_base.py`

**Step 1: 创建VLA适配器基类测试**

```python
# tests/test_vla_adapter_base.py
import pytest
from abc import ABC
from agents.clients.vla_adapters.base import VLAAdapterBase

def test_vla_adapter_is_abc():
    """验证VLAAdapterBase是抽象基类"""
    assert issubclass(VLAAdapterBase, ABC)

def test_vla_adapter_base_methods():
    """验证基类定义了必要方法"""
    adapter = VLAAdapterBase(config={})
    assert hasattr(adapter, 'reset')
    assert hasattr(adapter, 'act')
    assert hasattr(adapter, 'execute')
```

**Step 2: 运行测试**

Run: `pytest tests/test_vla_adapter_base.py -v`
Expected: FAIL (模块不存在)

**Step 3: 实现VLA适配器基类**

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

**Step 4: 验证通过**

Run: `pytest tests/test_vla_adapter_base.py -v`
Expected: PASS

---

### Task 3: LeRobot VLA 适配器

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/clients/vla_adapters/lerobot.py`
- Test: `tests/test_lerobot_adapter.py`

**Step 1: 创建LeRobot适配器测试**

```python
# tests/test_lerobot_adapter.py
import pytest
from agents.clients.vla_adapters.lerobot import LeRobotVLAAdapter

def test_lerobot_adapter_init():
    """验证LeRobot适配器初始化"""
    adapter = LeRobotVLAAdapter(config={
        "policy_name": "test_policy",
        "checkpoint": "test/checkpoint",
        "host": "127.0.0.1",
        "port": 8080
    })
    assert adapter.config["policy_name"] == "test_policy"
```

**Step 2: 运行测试**

Run: `pytest tests/test_lerobot_adapter.py -v`
Expected: FAIL

**Step 3: 实现LeRobot适配器**

```python
# agents/clients/vla_adapters/lerobot.py

from .base import VLAAdapterBase
from typing import Dict, Any, Optional
import numpy as np
import asyncio

class LeRobotVLAAdapter(VLAAdapterBase):
    """LeRobot VLA 适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.policy_name = config.get("policy_name")
        self.checkpoint = config.get("checkpoint")
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8080)
        self._client = None

    def reset(self):
        """重置VLA状态"""
        if self._client:
            # 调用LeRobot reset
            pass

    def act(
        self,
        observation: Dict[str, Any],
        skill_token: str,
        termination: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """生成动作"""
        # 调用VLA推理
        # 返回动作数组
        return np.zeros(self.action_dim)

    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作"""
        # 发送到机械臂执行
        return {"status": "executed"}

    @property
    def action_dim(self) -> int:
        """动作维度"""
        return 7  # 7 DOF机械臂
```

**Step 4: 验证通过**

Run: `pytest tests/test_lerobot_adapter.py -v`
Expected: PASS

---

### Task 4: VLA Skill 基类开发

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/skills/vla_skill.py`
- Test: `tests/test_vla_skill.py`

**Step 1: 创建VLASkill测试**

```python
# tests/test_vla_skill.py
import pytest
from agents.skills.vla_skill import VLASkill, SkillResult, SkillStatus

def test_skill_status_enum():
    """验证技能状态枚举"""
    assert SkillStatus.IDLE.value == "idle"
    assert SkillStatus.RUNNING.value == "running"
    assert SkillStatus.SUCCESS.value == "success"
    assert SkillStatus.FAILED.value == "failed"

def test_skill_result_dataclass():
    """验证技能结果数据结构"""
    result = SkillResult(status=SkillStatus.SUCCESS, output={"key": "value"})
    assert result.status == SkillStatus.SUCCESS
    assert result.output["key"] == "value"
```

**Step 2: 运行测试**

Run: `pytest tests/test_vla_skill.py -v`
Expected: FAIL

**Step 3: 实现VLASkill基类**

```python
# agents/skills/vla_skill.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

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
    metadata: Dict[str, Any] = field(default_factory=dict)

class VLASkill(ABC):
    """基于 VLA 的 Skill 抽象基类"""

    required_inputs: List[str] = []
    produced_outputs: List[str] = []
    default_vla: Optional[str] = None
    max_steps: int = 100

    def __init__(self, vla_adapter=None, **kwargs):
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

    async def execute(self, observation: Dict) -> SkillResult:
        """执行 Skill（异步封装同步逻辑）"""
        self._status = SkillStatus.RUNNING

        try:
            # 检查前置条件
            if not self.check_preconditions(observation):
                return SkillResult(
                    status=SkillStatus.FAILED,
                    error="Preconditions not met"
                )

            skill_token = self.build_skill_token()

            for step in range(self.max_steps):
                # 检查终止条件
                if self.check_termination(observation):
                    return SkillResult(
                        status=SkillStatus.SUCCESS,
                        output={"steps": step + 1}
                    )

                # VLA 推理
                action = self.vla.act(observation, skill_token)

                # 执行动作
                result = self.vla.execute(action)

                # 更新观察（需要子类实现）
                observation = await self._get_observation()

            return SkillResult(
                status=SkillStatus.SUCCESS,
                output={"steps": self.max_steps}
            )

        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(
                status=SkillStatus.FAILED,
                error=str(e)
            )

    async def _get_observation(self) -> Dict:
        """获取观察（子类可覆盖）"""
        return {}
```

**Step 4: 验证通过**

Run: `pytest tests/test_vla_skill.py -v`
Expected: PASS

---

## 阶段二：核心Skill开发

### Task 5: GraspSkill 抓取技能

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/skills/manipulation/grasp.py`
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/skills/manipulation/__init__.py`
- Test: `tests/test_grasp_skill.py`

**Step 1: 创建GraspSkill测试**

```python
# tests/test_grasp_skill.py
import pytest
from agents.skills.manipulation.grasp import GraspSkill
from agents.skills.vla_skill import SkillStatus

def test_grasp_skill_init():
    """验证GraspSkill初始化"""
    skill = GraspSkill(object_name="cube")
    assert skill.object_name == "cube"
    assert skill.max_steps == 50

def test_build_skill_token():
    """验证技能令牌构建"""
    skill = GraspSkill(object_name="cube")
    assert skill.build_skill_token() == "grasp cube"
```

**Step 2: 运行测试**

Run: `pytest tests/test_grasp_skill.py -v`
Expected: FAIL

**Step 3: 实现GraspSkill**

```python
# agents/skills/manipulation/grasp.py

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any

class GraspSkill(VLASkill):
    """抓取技能"""

    required_inputs = ["object_name", "observation"]
    produced_outputs = ["success", "grasp_position"]
    max_steps = 50

    def __init__(self, object_name: str, **kwargs):
        super().__init__(**kwargs)
        self.object_name = object_name

    def build_skill_token(self) -> str:
        return f"grasp {self.object_name}"

    def check_preconditions(self, observation: Dict) -> bool:
        # 检查物体是否在视野内
        return observation.get("object_detected", False)

    def check_termination(self, observation: Dict) -> bool:
        # 检查是否抓取成功（通过力传感器或夹爪状态）
        return observation.get("grasp_success", False)
```

**Step 4: 验证通过**

Run: `pytest tests/test_grasp_skill.py -v`
Expected: PASS

---

### Task 6: PlaceSkill 放置技能

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/skills/manipulation/place.py`
- Test: `tests/test_place_skill.py`

**Step 1: 创建测试**

```python
# tests/test_place_skill.py
from agents.skills.manipulation.place import PlaceSkill

def test_place_skill_init():
    skill = PlaceSkill(target_position=[0.5, 0.0, 0.1])
    assert skill.target_position == [0.5, 0.0, 0.1]

def test_build_skill_token():
    skill = PlaceSkill(target_position=[0.5, 0.0, 0.1])
    assert "place" in skill.build_skill_token()
```

**Step 2: 运行测试**

Run: `pytest tests/test_place_skill.py -v`
Expected: FAIL

**Step 3: 实现PlaceSkill**

```python
# agents/skills/manipulation/place.py

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List

class PlaceSkill(VLASkill):
    """放置技能"""

    required_inputs = ["target_position", "observation"]
    produced_outputs = ["success", "place_position"]
    max_steps = 50

    def __init__(self, target_position: List[float], **kwargs):
        super().__init__(**kwargs)
        self.target_position = target_position

    def build_skill_token(self) -> str:
        return f"place at {self.target_position}"

    def check_preconditions(self, observation: Dict) -> bool:
        return observation.get("object_held", False)

    def check_termination(self, observation: Dict) -> bool:
        return observation.get("placement_success", False)
```

**Step 4: 验证通过**

Run: `pytest tests/test_place_skill.py -v`
Expected: PASS

---

### Task 7: ReachSkill 到达技能

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/skills/manipulation/reach.py`
- Test: `tests/test_reach_skill.py`

---

### Task 8: 语音输入通道搭建

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/voice_command.py`
- Test: `tests/test_voice_command.py`

**Step 1: 创建语音命令测试**

```python
# tests/test_voice_command.py
import pytest
from agents.components.voice_command import VoiceCommand

def test_voice_command_init():
    component = VoiceCommand(
        component_name="voice_command",
        trigger_topic="audio_input"
    )
    assert component.name == "voice_command"
```

**Step 2: 运行测试**

Run: `pytest tests/test_voice_command.py -v`
Expected: FAIL

**Step 3: 实现语音命令组件**

```python
# agents/components/voice_command.py
from agents.components.component_base import BaseComponent

class VoiceCommand(BaseComponent):
    """语音命令理解组件"""

    def __init__(self, component_name: str, trigger_topic: str, **kwargs):
        super().__init__(component_name)
        self.trigger_topic = trigger_topic

    async def process(self, audio_data):
        # ASR识别 + 语义解析
        pass
```

**Step 4: 验证通过**

Run: `pytest tests/test_voice_command.py -v`
Expected: PASS

---

### Task 9: 语义解析器实现

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/semantic_parser.py`
- Test: `tests/test_semantic_parser.py`

**Step 1: 编写语义解析测试**

```python
# tests/test_semantic_parser.py
from agents.components.semantic_parser import SemanticParser

def test_parse_motion_command():
    parser = SemanticParser()
    result = parser.parse("向前20厘米")
    assert result["intent"] == "motion"
    assert result["direction"] == "forward"
    assert result["distance"] == 0.2
```

**Step 2: 运行测试**

Run: `pytest tests/test_semantic_parser.py -v`
Expected: FAIL

**Step 3: 实现语义解析器**

```python
# agents/components/semantic_parser.py

from typing import Dict, Any
import re

class SemanticParser:
    """语义解析器 - 解析语音指令为结构化动作"""

    DIRECTION_MAP = {
        "前": "forward", "后": "backward",
        "上": "up", "下": "down",
        "左": "left", "右": "right"
    }

    def parse(self, text: str) -> Dict[str, Any]:
        # 解析意图
        intent = self._parse_intent(text)

        # 解析参数
        params = self._parse_params(text)

        return {"intent": intent, **params}

    def _parse_intent(self, text: str) -> str:
        if any(kw in text for kw in ["前", "后", "上", "下", "左", "右"]):
            return "motion"
        if "抓" in text or "拿" in text:
            return "grasp"
        if "放" in text or "置" in text:
            return "place"
        return "unknown"

    def _parse_params(self, text: str) -> Dict[str, Any]:
        params = {}

        # 解析方向
        for cn, en in self.DIRECTION_MAP.items():
            if cn in text:
                params["direction"] = en
                break

        # 解析距离
        match = re.search(r"(\d+\.?\d*)\s*(厘米|cm|毫米|mm|m|米)", text)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            if unit in ["厘米", "cm"]:
                params["distance"] = value / 100
            elif unit in ["毫米", "mm"]:
                params["distance"] = value / 1000
            elif unit in ["米", "m"]:
                params["distance"] = value

        return params
```

**Step 4: 验证通过**

Run: `pytest tests/test_semantic_parser.py -v`
Expected: PASS

---

### Task 10: 任务规划器

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/agents/components/task_planner.py`
- Test: `tests/test_task_planner.py`

**Step 1: 创建任务规划测试**

```python
# tests/test_task_planner.py
import pytest
from agents.components.task_planner import TaskPlanner, PlanningStrategy

def test_task_planner_init():
    planner = TaskPlanner(strategy=PlanningStrategy.RULE_BASED)
    assert planner.strategy == PlanningStrategy.RULE_BASED

def test_rule_based_planning():
    planner = TaskPlanner()
    task = planner.plan("抓取杯子放到桌子上")
    assert "grasp" in task.skills
    assert "place" in task.skills
```

**Step 2: 运行测试**

Run: `pytest tests/test_task_planner.py -v`
Expected: FAIL

**Step 3: 实现TaskPlanner**

```python
# agents/components/task_planner.py

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
        strategy: PlanningStrategy = PlanningStrategy.RULE_BASED
    ):
        self.llm_client = llm_client
        self.strategy = strategy
        self._rules = self._init_rules()

    def _init_rules(self) -> Dict:
        """初始化规则库"""
        return {
            "抓取": ["reach", "grasp"],
            "放置": ["reach", "place"],
            "搬运": ["reach", "grasp", "reach", "place"],
        }

    def plan(self, instruction: str) -> Task:
        """从自然语言指令生成任务"""
        if self.strategy == PlanningStrategy.LLM and self.llm_client:
            return self._plan_with_llm(instruction)
        else:
            return self._plan_with_rules(instruction)

    def _plan_with_rules(self, instruction: str) -> Task:
        """使用规则进行任务规划"""
        skills = []
        for keyword, skill_list in self._rules.items():
            if keyword in instruction:
                skills.extend(skill_list)

        if not skills:
            skills = ["reach"]  # 默认

        return Task(name=instruction, skills=skills, parameters={})

    async def _plan_with_llm(self, instruction: str) -> Task:
        """使用LLM进行任务规划"""
        # TODO: 实现LLM规划
        return self._plan_with_rules(instruction)
```

**Step 4: 验证通过**

Run: `pytest tests/test_task_planner.py -v`
Expected: PASS

---

### Task 11: 语音示教端到端集成

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/examples/voice_teaching_agent.py`
- Test: `tests/test_voice_teaching_integration.py`

---

## 阶段三：高级功能与场景开发

### Task 12: 视觉感知Skill

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/vision/perception_skill.py`
- Test: `tests/test_vision_skill.py`

---

### Task 13: 力控模块

**Files:**
- Create: `/media/hzm/data_disk/EmbodiedAgentsSys/skills/force_control/force_control.py`
- Test: `tests/test_force_control.py`

---

## 实施顺序总结

| 阶段 | 优先级 | 任务数 | 预计时间 |
|-----|-------|-------|---------|
| Phase 1 | P0 | 4个 | 2周 |
| Phase 2 | P1 | 4个 | 3周 |
| Phase 3 | P2 | 3个 | 3周 |
| **总计** | - | **11个** | **8周** |

---

## 依赖关系图

```
Phase 1 (框架整合)
├── Task 1: 环境搭建
├── Task 2: VLA Adapter 基类
├── Task 3: LeRobot 适配器
└── Task 4: VLASkill 基类

Phase 2 (核心Skill + 语音示教)
├── Task 5: GraspSkill ← Task 4依赖
├── Task 6: PlaceSkill ← Task 4依赖
├── Task 7: ReachSkill ← Task 4依赖
├── Task 8: 语音输入通道
├── Task 9: 语义解析 ← Task 8依赖
└── Task 10: 任务规划 ← Task 9依赖

Phase 3 (高级功能)
├── Task 11: 端到端集成 ← Phase 1-2
├── Task 12: 视觉感知 ← Task 4依赖
└── Task 13: 力控模块 ← Task 4依赖
```

---

## 验收标准

### Phase 1 验收
- [ ] VLA Adapter基类可用
- [ ] LeRobot适配器工作正常
- [ ] VLASkill基类实现完成

### Phase 2 验收
- [ ] 基础抓取/放置/到达Skill可用
- [ ] 语音输入识别准确率 > 90%
- [ ] 语义解析准确率 > 85%
- [ ] 基础运动指令执行响应 < 500ms

### Phase 3 验收
- [ ] 语音示教端到端可用
- [ ] 视觉识别准确率 > 95%
- [ ] 抓取成功率 > 93%
- [ ] 力控响应时间 < 10ms
