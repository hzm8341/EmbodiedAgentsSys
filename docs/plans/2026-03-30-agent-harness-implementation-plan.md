:orphan:

# Agent Harness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建独立的 Agent Harness 测试+仿真+监控框架，支持分层 mock（Skill/Hardware/VLA）、四维评估（Result/Efficiency/Robustness/Explainability）、运行时追踪和离线回放。

**Architecture:** 独立模块 `agents/harness/`，对现有 `RobotAgentLoop` 零侵入。通过装饰器/拦截层在运行时切换 mock/real 模式，支持在线评估和离线回放。

**Tech Stack:** Python 3.10+, pytest, PyYAML, asyncio

---

## Phase 1: Foundation（基础设施）

### Task 1: Create directory structure

**Files:**
- Create: `agents/harness/__init__.py`
- Create: `agents/harness/core/__init__.py`
- Create: `agents/harness/core/evaluators/__init__.py`
- Create: `agents/harness/mocks/__init__.py`
- Create: `agents/harness/tasks/.gitkeep`
- Create: `agents/harness/traces/.gitkeep`
- Create: `agents/harness/examples/.gitkeep`

**Step 1: Create directories and init files**

```python
# agents/harness/__init__.py
"""Agent Harness - Testing, Simulation, and Monitoring Framework."""

from agents.harness.core.mode import HarnessMode
from agents.harness.core.task_set import TaskSet, Task
from agents.harness.core.config import HarnessConfig
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.core.tracer import HarnessTracer
from agents.harness.core.scorer import HarnessScorer, ScoreReport
from agents.harness.integration import attach_harness

__all__ = [
    "HarnessMode",
    "TaskSet",
    "Task",
    "HarnessConfig",
    "HarnessEnvironment",
    "HarnessTracer",
    "HarnessScorer",
    "ScoreReport",
    "attach_harness",
]
```

**Step 2: Run test to verify import works**

Run: `python -c "from agents.harness import HarnessMode; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add agents/harness/ && git commit -m "feat(harness): create directory structure and init"
```

---

### Task 2: Implement HarnessMode enum

**Files:**
- Create: `agents/harness/core/mode.py`

**Step 1: Write the failing test**

```python
# tests/test_harness_mode.py
import pytest
from agents.harness.core.mode import HarnessMode

def test_harness_mode_enum_values():
    assert HarnessMode.SKILL_MOCK.value == "skill_mock"
    assert HarnessMode.HARDWARE_MOCK.value == "hardware_mock"
    assert HarnessMode.FULL_MOCK.value == "full_mock"
    assert HarnessMode.REAL.value == "real"

def test_harness_mode_from_string():
    assert HarnessMode.from_string("skill_mock") == HarnessMode.SKILL_MOCK
    assert HarnessMode.from_string("hardware_mock") == HarnessMode.HARDWARE_MOCK
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_mode.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/mode.py
from enum import Enum

class HarnessMode(str, Enum):
    """Harness operating mode - controls what is mocked."""
    SKILL_MOCK = "skill_mock"      # Skill-level mock only
    HARDWARE_MOCK = "hardware_mock"  # Hardware adapter mock
    FULL_MOCK = "full_mock"        # Full chain mock (skill + hardware + VLA)
    REAL = "real"                  # Real hardware, tracing only

    @classmethod
    def from_string(cls, value: str) -> "HarnessMode":
        """Parse mode from string, case-insensitive."""
        value = value.lower()
        for mode in cls:
            if mode.value == value:
                return mode
        raise ValueError(f"Unknown HarnessMode: {value}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_mode.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/mode.py tests/test_harness_mode.py && git commit -m "feat(harness): add HarnessMode enum"
```

---

### Task 3: Implement HarnessConfig

**Files:**
- Create: `agents/harness/core/config.py`
- Create: `agents/harness/config.yaml`

**Step 1: Write the failing test**

```python
# tests/test_harness_config.py
import pytest
from agents.harness.core.config import HarnessConfig, MockConfig
from agents.harness.core.mode import HarnessMode

def test_default_config():
    config = HarnessConfig()
    assert config.mode == HarnessMode.HARDWARE_MOCK
    assert config.robot_type == "arm"
    assert config.auto_attach is False
    assert config.tracing_enabled is True

def test_config_from_yaml_dict():
    data = {
        "harness": {
            "mode": "skill_mock",
            "robot_type": "arm",
            "auto_attach": True,
        },
        "skill_mock": {"default_success_rate": 0.9}
    }
    config = HarnessConfig.from_dict(data)
    assert config.mode == HarnessMode.SKILL_MOCK
    assert config.skill_mock.default_success_rate == 0.9
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_config.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/config.py
from dataclasses import dataclass, field
from typing import Optional
import yaml
from agents.harness.core.mode import HarnessMode

@dataclass
class MockConfig:
    """Base mock configuration."""
    default_success_rate: float = 0.85
    latency_ms: int = 50

@dataclass
class SkillMockConfig(MockConfig):
    per_skill_rate: dict = field(default_factory=dict)

@dataclass
class HardwareMockConfig(MockConfig):
    joint_error_rate: float = 0.05
    gripper_slope_rate: float = 0.1
    position_noise: float = 0.005

@dataclass
class FullMockConfig(MockConfig):
    vla_success_rate: float = 0.75
    vla_action_noise: bool = True

@dataclass
class EvaluatorWeights:
    result: float = 0.25
    efficiency: float = 0.25
    robustness: float = 0.25
    explainability: float = 0.25

@dataclass
class HarnessConfig:
    mode: HarnessMode = HarnessMode.HARDWARE_MOCK
    robot_type: str = "arm"
    auto_attach: bool = False
    tracing_enabled: bool = True
    trace_dir: str = "agents/harness/traces"
    auto_append_regression: bool = True

    skill_mock: SkillMockConfig = field(default_factory=SkillMockConfig)
    hardware_mock: HardwareMockConfig = field(default_factory=HardwareMockConfig)
    full_mock: FullMockConfig = field(default_factory=FullMockConfig)

    pass_threshold: float = 0.70
    task_timeout: int = 60

    @classmethod
    def from_dict(cls, data: dict) -> "HarnessConfig":
        h = data.get("harness", {})
        mode = HarnessMode.from_string(h.get("mode", "hardware_mock"))
        cfg = cls(mode=mode)
        cfg.robot_type = h.get("robot_type", "arm")
        cfg.auto_attach = h.get("auto_attach", False)
        cfg.tracing_enabled = h.get("tracing_enabled", True)
        cfg.trace_dir = h.get("trace_dir", "agents/harness/traces")
        cfg.auto_append_regression = h.get("auto_append_regression", True)

        if "skill_mock" in data:
            sm = data["skill_mock"]
            cfg.skill_mock = SkillMockConfig(
                default_success_rate=sm.get("default_success_rate", 0.85),
                per_skill_rate=sm.get("per_skill_rate", {})
            )
        if "hardware_mock" in data:
            hm = data["hardware_mock"]
            cfg.hardware_mock = HardwareMockConfig(
                default_success_rate=hm.get("default_success_rate", 0.85),
                latency_ms=hm.get("latency_ms", 50),
                joint_error_rate=hm.get("joint_error_rate", 0.05),
                gripper_slope_rate=hm.get("gripper_slope_rate", 0.1),
                position_noise=hm.get("position_noise", 0.005)
            )
        if "full_mock" in data:
            fm = data["full_mock"]
            cfg.full_mock = FullMockConfig(
                default_success_rate=fm.get("default_success_rate", 0.85),
                latency_ms=fm.get("latency_ms", 50),
                vla_success_rate=fm.get("vla_success_rate", 0.75),
                vla_action_noise=fm.get("vla_action_noise", True)
            )
        return cfg

    @classmethod
    def from_yaml(cls, path: str) -> "HarnessConfig":
        with open(path) as f:
            return cls.from_dict(yaml.safe_load(f))
```

```yaml
# agents/harness/config.yaml
harness:
  mode: "hardware_mock"
  robot_type: "arm"
  auto_attach: false
  tracing_enabled: true
  trace_dir: "agents/harness/traces"
  auto_append_regression: true

skill_mock:
  default_success_rate: 0.85
  per_skill_rate:
    manipulation.grasp: 0.80
    manipulation.place: 0.90
    manipulation.reach: 0.95

hardware_mock:
  default_success_rate: 0.85
  latency_ms: 50
  joint_error_rate: 0.05
  gripper_slope_rate: 0.10
  position_noise: 0.005

full_mock:
  default_success_rate: 0.85
  latency_ms: 50
  vla_success_rate: 0.75
  vla_action_noise: true

evaluator:
  weights:
    result: 0.25
    efficiency: 0.25
    robustness: 0.25
    explainability: 0.25
  pass_threshold: 0.70
  task_timeout: 60
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_harness_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/config.py agents/harness/config.yaml tests/test_harness_config.py && git commit -m "feat(harness): add HarnessConfig"
```

---

## Phase 2: TaskSet（任务管理）

### Task 4: Implement Task and TaskSet data structures

**Files:**
- Create: `agents/harness/core/task_set.py`
- Create: `tests/test_task_set.py`

**Step 1: Write the failing test**

```python
# tests/test_task_set.py
import pytest
from agents.harness.core.task_set import Task, TaskSet, SceneObject, SuccessCriteria

def test_task_creation():
    task = Task(
        task_id="test_001",
        description="抓取红色方块",
        robot_type="arm",
        scene={"objects": []},
        expected_skills=["manipulation.grasp"],
    )
    assert task.task_id == "test_001"
    assert task.robot_type == "arm"

def test_task_from_yaml_dict():
    data = {
        "task_id": "pick_001",
        "description": "Pick red cube",
        "robot_type": "arm",
        "scene": {
            "objects": [
                {"id": "cube", "type": "cube", "color": "red", "initial_position": [0.3, -0.1, 0.05]}
            ]
        },
        "expected_skills": ["manipulation.reach", "manipulation.grasp"],
        "success_criteria": {
            "result": {"type": "position_match", "object": "cube", "target": "zone_b", "tolerance": 0.02},
            "efficiency": {"max_duration_seconds": 30},
            "robustness": {"max_retry_count": 2, "allowed_failures": ["gripper_slope"]}
        }
    }
    task = Task.from_dict(data)
    assert task.task_id == "pick_001"
    assert len(task.scene.objects) == 1
    assert task.success_criteria.efficiency.max_duration_seconds == 30
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_set.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/task_set.py
from dataclasses import dataclass, field
from typing import Any

@dataclass
class SceneObject:
    id: str
    type: str
    color: str = ""
    initial_position: list = field(default_factory=lambda: [0, 0, 0])
    size: list = field(default_factory=lambda: [0.05, 0.05, 0.05])

@dataclass
class SceneSpec:
    objects: list[SceneObject] = field(default_factory=list)
    workspace: dict = field(default_factory=dict)

@dataclass
class ResultCriteria:
    type: str = "position_match"
    object: str = ""
    target: str = ""
    tolerance: float = 0.02

@dataclass
class EfficiencyCriteria:
    max_duration_seconds: int = 30

@dataclass
class RobustnessCriteria:
    max_retry_count: int = 2
    allowed_failures: list = field(default_factory=list)

@dataclass
class SuccessCriteria:
    result: ResultCriteria = field(default_factory=ResultCriteria)
    efficiency: EfficiencyCriteria = field(default_factory=EfficiencyCriteria)
    robustness: RobustnessCriteria = field(default_factory=RobustnessCriteria)

@dataclass
class Task:
    task_id: str
    description: str
    robot_type: str
    scene: dict = field(default_factory=dict)
    expected_skills: list = field(default_factory=list)
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    is_regression: bool = False
    tags: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        objects = [SceneObject(**obj) for obj in data.get("scene", {}).get("objects", [])]
        scene = {
            "objects": objects,
            "workspace": data.get("scene", {}).get("workspace", {})
        }

        sc = data.get("success_criteria", {})
        success_criteria = SuccessCriteria(
            result=ResultCriteria(**sc.get("result", {})),
            efficiency=EfficiencyCriteria(**sc.get("efficiency", {})),
            robustness=RobustnessCriteria(**sc.get("robustness", {}))
        )

        return cls(
            task_id=data["task_id"],
            description=data.get("description", ""),
            robot_type=data.get("robot_type", "arm"),
            scene=scene,
            expected_skills=data.get("expected_skills", []),
            success_criteria=success_criteria,
            is_regression=data.get("is_regression", False),
            tags=data.get("tags", [])
        )

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "robot_type": self.robot_type,
            "scene": {
                "objects": [obj.__dict__ for obj in self.scene.get("objects", [])],
                "workspace": self.scene.get("workspace", {})
            },
            "expected_skills": self.expected_skills,
            "success_criteria": {
                "result": self.success_criteria.result.__dict__,
                "efficiency": self.success_criteria.efficiency.__dict__,
                "robustness": self.success_criteria.robustness.__dict__
            },
            "is_regression": self.is_regression,
            "tags": self.tags
        }

class TaskSet:
    declarative: list[Task] = field(default_factory=list)
    regression: list[Task] = field(default_factory=list)
    custom: list[Task] = field(default_factory=list)

    def filter(self, tags: list[str]) -> "TaskSet":
        result = TaskSet()
        result.declarative = [t for t in self.declarative if any(tag in t.tags for tag in tags)]
        result.regression = [t for t in self.regression if any(tag in t.tags for tag in tags)]
        result.custom = [t for t in self.custom if any(tag in t.tags for tag in tags)]
        return result

    def merge(self, other: "TaskSet") -> "TaskSet":
        result = TaskSet()
        result.declarative = self.declarative + other.declarative
        result.regression = self.regression + other.regression
        result.custom = self.custom + other.custom
        return result

    def all_tasks(self) -> list[Task]:
        return self.declarative + self.regression + self.custom
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_task_set.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/task_set.py tests/test_task_set.py && git commit -m "feat(harness): add Task and TaskSet data structures"
```

---

### Task 5: Implement TaskLoader (YAML loading + failure data)

**Files:**
- Create: `agents/harness/core/task_loader.py`
- Create: `agents/harness/tasks/pick_place_basic.yaml`
- Create: `agents/harness/tasks/inspect_task.yaml`
- Create: `tests/test_task_loader.py`

**Step 1: Write the failing test**

```python
# tests/test_task_loader.py
import pytest
from pathlib import Path
from agents.harness.core.task_loader import TaskLoader

def test_load_tasks_from_dir(tmp_path):
    # Create a test task YAML
    task_yaml = tmp_path / "test_task.yaml"
    task_yaml.write_text("""
task_id: "test_task_001"
description: "Test task"
robot_type: "arm"
scene:
  objects: []
expected_skills: []
success_criteria:
  result: {}
  efficiency: {}
  robustness: {}
""")
    loader = TaskLoader()
    task_set = loader.load_from_dir(tmp_path)
    assert len(task_set.declarative) == 1
    assert task_set.declarative[0].task_id == "test_task_001"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_task_loader.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/task_loader.py
import yaml
from pathlib import Path
from typing import Optional
from agents.harness.core.task_set import TaskSet, Task

class TaskLoader:
    def load_from_dir(self, dir_path: str | Path) -> TaskSet:
        dir_path = Path(dir_path)
        task_set = TaskSet()

        for yaml_file in dir_path.glob("*.yaml"):
            if yaml_file.name == ".gitkeep":
                continue
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                if data and "task_id" in data:
                    task_set.declarative.append(Task.from_dict(data))
            except Exception:
                continue

        return task_set

    def load_from_failure_logs(self, failure_dir: str | Path) -> TaskSet:
        """Build Task from FailureRecorder output."""
        failure_dir = Path(failure_dir)
        task_set = TaskSet()

        for timestamp_dir in failure_dir.iterdir():
            if not timestamp_dir.is_dir():
                continue
            try:
                metadata = timestamp_dir / "metadata.json"
                scene_spec = timestamp_dir / "scene_spec.yaml"
                plan = timestamp_dir / "plan.yaml"

                if not metadata.exists():
                    continue

                import json
                meta = json.loads(metadata.read_text())

                task = Task(
                    task_id=f"regression_{timestamp_dir.name}",
                    description=meta.get("task_description", "regression task"),
                    robot_type=meta.get("robot_type", "arm"),
                    scene={},
                    expected_skills=[],
                    is_regression=True,
                    tags=["regression"]
                )
                task_set.regression.append(task)
            except Exception:
                continue

        return task_set
```

```yaml
# agents/harness/tasks/pick_place_basic.yaml
task_id: "pick_place_basic_001"
description: "抓取红色方块并放置到B区"
robot_type: "arm"
tags: ["basic", "manipulation"]

scene:
  objects:
    - id: "red_cube"
      type: "cube"
      color: "red"
      initial_position: [0.3, -0.1, 0.05]
    - id: "zone_b"
      type: "target_zone"
      position: [0.5, 0.2, 0.0]
      size: [0.1, 0.1, 0.0]
  workspace:
    table_height: 0.0

expected_skills:
  - "manipulation.reach"
  - "manipulation.grasp"
  - "manipulation.place"

success_criteria:
  result:
    type: "position_match"
    object: "red_cube"
    target: "zone_b"
    tolerance: 0.02
  efficiency:
    max_duration_seconds: 30
  robustness:
    max_retry_count: 2
    allowed_failures: ["gripper_slope"]
```

```yaml
# agents/harness/tasks/inspect_task.yaml
task_id: "inspect_task_001"
description: "检测工作台上的物体"
robot_type: "arm"
tags: ["vision", "inspection"]

scene:
  objects:
    - id: "target_object"
      type: "unknown"
      initial_position: [0.3, 0.0, 0.1]
  workspace:
    table_height: 0.0

expected_skills:
  - "manipulation.reach"
  - "vision.inspect"

success_criteria:
  result:
    type: "object_detected"
    object: "target_object"
  efficiency:
    max_duration_seconds: 20
  robustness:
    max_retry_count: 1
    allowed_failures: []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_task_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/task_loader.py agents/harness/tasks/*.yaml tests/test_task_loader.py && git commit -m "feat(harness): add TaskLoader and sample task YAMLs"
```

---

## Phase 3: HarnessEnvironment（分层 Mock）

### Task 6: Implement HarnessEnvironment base class

**Files:**
- Create: `agents/harness/core/harness_env.py`
- Create: `tests/test_harness_env.py`

**Step 1: Write the failing test**

```python
# tests/test_harness_env.py
import pytest
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode

def test_create_skill_mock_env():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    env = HarnessEnvironment.create(config)
    assert env.mode == HarnessMode.SKILL_MOCK

def test_create_hardware_mock_env():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    env = HarnessEnvironment.create(config)
    assert env.mode == HarnessMode.HARDWARE_MOCK

def test_env_has_mock_registry():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    env = HarnessEnvironment.create(config)
    assert env.skill_registry is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_env.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/harness_env.py
from dataclasses import dataclass
from agents.harness.core.mode import HarnessMode
from agents.harness.core.config import HarnessConfig

class HarnessEnvironment:
    mode: HarnessMode
    config: HarnessConfig
    skill_registry: dict = {}

    @classmethod
    def create(cls, config: HarnessConfig) -> "HarnessEnvironment":
        env = cls()
        env.config = config
        env.mode = config.mode
        env.skill_registry = {}
        return env
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_env.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/harness_env.py tests/test_harness_env.py && git commit -m "feat(harness): add HarnessEnvironment base class"
```

---

### Task 7: Implement SkillMocks

**Files:**
- Create: `agents/harness/mocks/skill_mocks.py`
- Modify: `agents/harness/core/harness_env.py`
- Create: `tests/test_skill_mocks.py`

**Step 1: Write the failing test**

```python
# tests/test_skill_mocks.py
import pytest
import asyncio
from agents.harness.mocks.skill_mocks import MockSkillRegistry, MockGraspSkill, MockPlaceSkill

def test_mock_grasp_returns_configured_result():
    skill = MockGraspSkill(success_rate=1.0)
    assert skill.execute_sync() is True

def test_mock_grasp_respects_success_rate():
    skill = MockGraspSkill(success_rate=0.0)
    # With 0% success rate, should fail
    result = skill.execute_sync()
    assert result is False

def test_mock_skill_registry():
    registry = MockSkillRegistry(default_success_rate=0.9)
    result = registry.call_skill("manipulation.grasp", {})
    assert result.success is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_mocks.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/mocks/skill_mocks.py
import random
from dataclasses import dataclass
from typing import Any

@dataclass
class SkillResult:
    success: bool
    content: str
    data: dict = {}

class MockSkillRegistry:
    def __init__(self, default_success_rate: float = 0.85, per_skill_rate: dict = None):
        self.default_success_rate = default_success_rate
        self.per_skill_rate = per_skill_rate or {}

    def call_skill(self, skill_id: str, args: dict) -> SkillResult:
        rate = self.per_skill_rate.get(skill_id, self.default_success_rate)
        success = random.random() < rate
        return SkillResult(
            success=success,
            content=f"[mock] {skill_id} {'succeeded' if success else 'failed'}",
            data={"skill_id": skill_id, "success": success}
        )

class MockGraspSkill:
    def __init__(self, success_rate: float = 0.85):
        self.success_rate = success_rate

    def execute_sync(self) -> bool:
        return random.random() < self.success_rate

    async def execute(self) -> SkillResult:
        return SkillResult(
            success=self.execute_sync(),
            content="[mock] GraspSkill executed"
        )

class MockPlaceSkill:
    def __init__(self, success_rate: float = 0.85):
        self.success_rate = success_rate

    def execute_sync(self) -> bool:
        return random.random() < self.success_rate

    async def execute(self) -> SkillResult:
        return SkillResult(
            success=self.execute_sync(),
            content="[mock] PlaceSkill executed"
        )
```

```python
# Update agents/harness/core/harness_env.py to import and use mocks
from agents.harness.mocks.skill_mocks import MockSkillRegistry

class HarnessEnvironment:
    # ... existing code ...

    def setup_skill_mocks(self):
        if self.mode == HarnessMode.SKILL_MOCK:
            cfg = self.config.skill_mock
            self.skill_registry = MockSkillRegistry(
                default_success_rate=cfg.default_success_rate,
                per_skill_rate=cfg.per_skill_rate
            )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_skill_mocks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/mocks/skill_mocks.py agents/harness/core/harness_env.py tests/test_skill_mocks.py && git commit -m "feat(harness): add SkillMocks implementation"
```

---

### Task 8: Implement HardwareMocks (MockArmAdapter)

**Files:**
- Create: `agents/harness/mocks/hardware_mocks.py`
- Create: `tests/test_hardware_mocks.py`

**Step 1: Write the failing test**

```python
# tests/test_hardware_mocks.py
import pytest
import asyncio
from agents.harness.mocks.hardware_mocks import MockArmAdapter
from agents.hardware.arm_adapter import Pose6D, RobotState

@pytest.mark.asyncio
async def test_mock_arm_move_to_pose():
    arm = MockArmAdapter()
    pose = Pose6D(x=0.3, y=0.0, z=0.2, roll=0, pitch=0, yaw=0)
    result = await arm.move_to_pose(pose)
    assert isinstance(result, bool)

@pytest.mark.asyncio
async def test_mock_arm_get_state():
    arm = MockArmAdapter()
    state = await arm.get_state()
    assert isinstance(state, RobotState)
    assert 0.0 <= state.gripper_opening <= 1.0

def test_mock_arm_is_ready():
    arm = MockArmAdapter()
    assert arm.is_ready_sync() is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_hardware_mocks.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/mocks/hardware_mocks.py
import random
import asyncio
from agents.hardware.arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities

class MockArmAdapter(ArmAdapter):
    def __init__(
        self,
        joint_error_rate: float = 0.05,
        gripper_slope_rate: float = 0.1,
        position_noise: float = 0.005,
        latency_ms: int = 50
    ):
        self._joint_error_rate = joint_error_rate
        self._gripper_slope_rate = gripper_slope_rate
        self._position_noise = position_noise
        self._latency_ms = latency_ms
        self._gripper_open = 0.0
        self._joints = [0.0] * 7

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        # Simulate joint error
        if random.random() < self._joint_error_rate:
            return False
        self._joints = [0.1] * 7
        return True

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = angles
        return True

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        await asyncio.sleep(self._latency_ms / 2000.0)
        if random.random() < self._gripper_slope_rate:
            return False
        self._gripper_open = max(0.0, min(1.0, opening))
        return True

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=self._joints,
            end_effector_pose=Pose6D(x=0.3, y=0.0, z=0.2, roll=0, pitch=0, yaw=0),
            gripper_opening=self._gripper_open,
            is_moving=False,
            error_code=0
        )

    async def is_ready(self) -> bool:
        return True

    def is_ready_sync(self) -> bool:
        return True

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=["manipulation.grasp", "manipulation.place", "manipulation.reach"]
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_hardware_mocks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/mocks/hardware_mocks.py tests/test_hardware_mocks.py && git commit -m "feat(harness): add HardwareMocks (MockArmAdapter)"
```

---

### Task 9: Implement VLAMocks

**Files:**
- Create: `agents/harness/mocks/vla_mocks.py`
- Create: `tests/test_vla_mocks.py`

**Step 1: Write the failing test**

```python
# tests/test_vla_mocks.py
import pytest
import asyncio
from agents.harness.mocks.vla_mocks import MockVLAAdapter

@pytest.mark.asyncio
async def test_mock_vla_act():
    adapter = MockVLAAdapter(success_rate=0.8)
    obs = {"image": "test", "joint_positions": [0.0] * 7}
    action = await adapter.act(obs, "grasp(object=cube)")
    assert action is not None
    assert len(action) == 7

def test_mock_vla_reset():
    adapter = MockVLAAdapter()
    adapter.reset()
    assert True  # No exception
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_vla_mocks.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/mocks/vla_mocks.py
import random
from typing import Any

class MockVLAAdapter:
    def __init__(self, success_rate: float = 0.75, action_noise: bool = True):
        self.success_rate = success_rate
        self.action_noise = action_noise

    def reset(self) -> None:
        pass

    async def act(self, observation: dict, instruction: str) -> list[float]:
        # Return mock action: 7 DOF (6 joints + gripper)
        base_action = [0.1, 0.0, 0.2, 0.0, 0.0, 0.0, 0.5]

        if self.action_noise:
            import numpy as np
            noise = np.random.randn(7) * 0.01
            base_action = [a + n for a, n in zip(base_action, noise)]

        return base_action

    async def execute(self, action: list[float]) -> dict:
        success = random.random() < self.success_rate
        return {"success": success, "action_executed": action}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_vla_mocks.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/mocks/vla_mocks.py tests/test_vla_mocks.py && git commit -m "feat(harness): add VLAMocks"
```

---

## Phase 4: Tracer（追踪）

### Task 10: Implement Tracer and trace data structures

**Files:**
- Create: `agents/harness/core/tracer.py`
- Create: `tests/test_tracer.py`

**Step 1: Write the failing test**

```python
# tests/test_tracer.py
import pytest
from agents.harness.core.tracer import HarnessTracer, HarnessTrace, TaskStatus, ToolCallRecord
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode

def test_tracer_creation():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    tracer = HarnessTracer(config)
    assert tracer.config == config

def test_tracer_records_tool_call():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    tracer = HarnessTracer(config)
    tracer.record_tool_call("start_policy", {}, "success")
    assert len(tracer._trace.tool_calls) == 1
    assert tracer._trace.tool_calls[0].tool_name == "start_policy"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_tracer.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/tracer.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode

class TaskStatus:
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ABORTED = "aborted"

@dataclass
class ToolCallRecord:
    timestamp: datetime
    tool_name: str
    args: dict
    result: str
    duration_ms: int = 0

@dataclass
class ObservationRecord:
    timestamp: datetime
    content: str

@dataclass
class CoTDecisionRecord:
    timestamp: datetime
    task_state: str
    action_type: str
    action_name: str
    action_args: dict
    reasoning: str

@dataclass
class SubtaskRecord:
    subtask_id: str
    status: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    failure_reason: Optional[str] = None

@dataclass
class MemorySnapshot:
    timestamp: datetime
    role: str
    task_graph_summary: str
    current_skill: Optional[str] = None

@dataclass
class HarnessTrace:
    task_id: str
    session_id: str
    mode: HarnessMode
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    subtask_graph: list[SubtaskRecord] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    observations: list[ObservationRecord] = field(default_factory=list)
    cot_decisions: list[CoTDecisionRecord] = field(default_factory=list)
    memory_snapshots: list[MemorySnapshot] = field(default_factory=list)
    final_status: str = TaskStatus.FAILED
    failure_reason: Optional[str] = None

class HarnessTracer:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self._trace: HarnessTrace | None = None
        self._enabled = config.tracing_enabled

    def start_trace(self, task_id: str, session_id: str) -> None:
        self._trace = HarnessTrace(
            task_id=task_id,
            session_id=session_id,
            mode=self.config.mode,
            start_time=datetime.now()
        )

    def stop_trace(self, status: str = TaskStatus.COMPLETED, failure_reason: str | None = None) -> HarnessTrace:
        if self._trace is None:
            raise RuntimeError("Trace not started")
        self._trace.end_time = datetime.now()
        if self._trace.start_time and self._trace.end_time:
            self._trace.duration_ms = int((self._trace.end_time - self._trace.start_time).total_seconds() * 1000)
        self._trace.final_status = status
        self._trace.failure_reason = failure_reason
        return self._trace

    def record_tool_call(self, name: str, args: dict, result: str, duration_ms: int = 0) -> None:
        if self._trace:
            self._trace.tool_calls.append(ToolCallRecord(
                timestamp=datetime.now(),
                tool_name=name,
                args=args,
                result=result,
                duration_ms=duration_ms
            ))

    def record_observation(self, content: str) -> None:
        if self._trace:
            self._trace.observations.append(ObservationRecord(
                timestamp=datetime.now(),
                content=content
            ))

    def record_cot_decision(self, task_state: str, action_type: str, action_name: str, action_args: dict, reasoning: str) -> None:
        if self._trace:
            self._trace.cot_decisions.append(CoTDecisionRecord(
                timestamp=datetime.now(),
                task_state=task_state,
                action_type=action_type,
                action_name=action_name,
                action_args=action_args,
                reasoning=reasoning
            ))

    def get_trace(self) -> HarnessTrace | None:
        return self._trace
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_tracer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/tracer.py tests/test_tracer.py && git commit -m "feat(harness): add HarnessTracer and trace data structures"
```

---

### Task 11: Implement TraceReplayer

**Files:**
- Create: `agents/harness/core/trace_replayer.py`
- Create: `tests/test_trace_replayer.py`

**Step 1: Write the failing test**

```python
# tests/test_trace_replayer.py
import pytest
from pathlib import Path
from agents.harness.core.trace_replayer import TraceReplayer
from agents.harness.core.tracer import HarnessTrace

def test_replayer_reconstructs_trace(tmp_path):
    # Create a minimal trace file
    import json
    trace_data = {
        "task_id": "test_001",
        "session_id": "sess_001",
        "mode": "hardware_mock",
        "start_time": "2026-03-30T10:00:00",
        "tool_calls": []
    }
    trace_file = tmp_path / "trace_test_001.json"
    trace_file.write_text(json.dumps(trace_data))

    replayer = TraceReplayer()
    trace = replayer.replay_from_file(trace_file)
    assert trace.task_id == "test_001"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_trace_replayer.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/trace_replayer.py
import json
from pathlib import Path
from typing import Optional
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.mode import HarnessMode

class TraceReplayer:
    def replay_from_file(self, trace_path: Path | str) -> HarnessTrace:
        with open(trace_path) as f:
            data = json.load(f)

        return HarnessTrace(
            task_id=data.get("task_id", ""),
            session_id=data.get("session_id", ""),
            mode=HarnessMode.from_string(data.get("mode", "real")),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            final_status=data.get("final_status", TaskStatus.FAILED)
        )

    def replay_from_dir(self, dir_path: Path | str) -> list[HarnessTrace]:
        dir_path = Path(dir_path)
        traces = []
        for trace_file in dir_path.glob("*.json"):
            try:
                traces.append(self.replay_from_file(trace_file))
            except Exception:
                continue
        return traces
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_trace_replayer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/trace_replayer.py tests/test_trace_replayer.py && git commit -m "feat(harness): add TraceReplayer"
```

---

## Phase 5: Evaluators（四维评估）

### Task 12: Implement Evaluator base class

**Files:**
- Create: `agents/harness/core/evaluators/base.py`
- Create: `tests/test_evaluator_base.py`

**Step 1: Write the failing test**

```python
# tests/test_evaluator_base.py
import pytest
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore

def test_evaluation_score_dataclass():
    score = EvaluationScore(
        dimension="result",
        score=0.85,
        weight=0.25,
        details={"note": "good"},
        passed=True
    )
    assert score.score == 0.85
    assert score.weight == 0.25

def test_evaluator_base_interface():
    class DummyEvaluator(Evaluator):
        def _do_evaluate(self, trace, task) -> EvaluationScore:
            return EvaluationScore("dummy", 1.0, 1.0, {}, True)

    evaluator = DummyEvaluator()
    assert evaluator.dimension == "dummy"
    assert evaluator.weight == 1.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_evaluator_base.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/evaluators/base.py
from dataclasses import dataclass
from typing import Any
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace

@dataclass
class EvaluationScore:
    dimension: str
    score: float
    weight: float
    details: dict
    passed: bool

class Evaluator:
    """Base class for all evaluators."""
    dimension: str = "base"
    weight: float = 1.0

    def evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        return self._do_evaluate(trace, task)

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        raise NotImplementedError
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_evaluator_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/evaluators/base.py tests/test_evaluator_base.py && git commit -m "feat(harness): add Evaluator base class"
```

---

### Task 13: Implement ResultEvaluator

**Files:**
- Create: `agents/harness/core/evaluators/result_eval.py`
- Create: `tests/test_result_eval.py`

**Step 1: Write the failing test**

```python
# tests/test_result_eval.py
import pytest
from agents.harness.core.evaluators.result_eval import ResultEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode
from datetime import datetime

def test_result_eval_completed_task():
    evaluator = ResultEvaluator()
    trace = HarnessTrace(
        task_id="test_001",
        session_id="sess_001",
        mode=HarnessMode.REAL,
        start_time=datetime.now(),
        final_status=TaskStatus.COMPLETED
    )
    task = Task(task_id="test_001", description="test", robot_type="arm")

    score = evaluator.evaluate(trace, task)
    assert score.dimension == "result"
    assert score.score >= 0.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_result_eval.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/evaluators/result_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace, TaskStatus

class ResultEvaluator(Evaluator):
    dimension = "result"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        # 1. Check final status
        if trace.final_status == TaskStatus.COMPLETED:
            base_score = 1.0
        elif trace.final_status == TaskStatus.FAILED:
            base_score = 0.0
        else:
            base_score = 0.3

        # 2. Skill coverage
        expected = set(task.expected_skills)
        called = {tc.tool_name for tc in trace.tool_calls}
        skill_coverage = len(expected & called) / len(expected) if expected else 1.0

        final_score = base_score * skill_coverage
        passed = final_score >= 0.5

        return EvaluationScore(
            dimension=self.dimension,
            score=final_score,
            weight=self.weight,
            details={
                "base_score": base_score,
                "skill_coverage": skill_coverage,
                "expected_skills": list(expected),
                "called_skills": list(called)
            },
            passed=passed
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_result_eval.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/evaluators/result_eval.py tests/test_result_eval.py && git commit -m "feat(harness): add ResultEvaluator"
```

---

### Task 14: Implement EfficiencyEvaluator

**Files:**
- Create: `agents/harness/core/evaluators/efficiency_eval.py`
- Create: `tests/test_efficiency_eval.py`

**Step 1: Write the failing test**

```python
# tests/test_efficiency_eval.py
import pytest
from agents.harness.core.evaluators.efficiency_eval import EfficiencyEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.task_set import Task, SuccessCriteria, EfficiencyCriteria
from agents.harness.core.mode import HarnessMode
from datetime import datetime, timedelta

def test_efficiency_eval_fast_task():
    evaluator = EfficiencyEvaluator()
    start = datetime.now()
    end = start + timedelta(seconds=10)

    trace = HarnessTrace(
        task_id="test_001",
        session_id="sess_001",
        mode=HarnessMode.REAL,
        start_time=start,
        end_time=end,
        duration_ms=10000,
        final_status=TaskStatus.COMPLETED
    )
    task = Task(
        task_id="test_001",
        description="test",
        robot_type="arm",
        success_criteria=SuccessCriteria(
            efficiency=EfficiencyCriteria(max_duration_seconds=30)
        )
    )

    score = evaluator.evaluate(trace, task)
    assert score.dimension == "efficiency"
    assert score.score == 1.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_efficiency_eval.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/evaluators/efficiency_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace, TaskStatus

class EfficiencyEvaluator(Evaluator):
    dimension = "efficiency"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        duration_sec = (trace.duration_ms or 0) / 1000
        max_duration = task.success_criteria.efficiency.max_duration_seconds

        # Time efficiency
        if duration_sec <= max_duration:
            time_score = 1.0
        elif duration_sec <= max_duration * 1.5:
            time_score = 0.5
        else:
            time_score = 0.0

        # Tool call efficiency
        expected_count = len(task.expected_skills)
        actual_count = len(trace.tool_calls)
        tool_ratio = expected_count / max(actual_count, 1)
        tool_score = min(tool_ratio, 1.0)

        final_score = time_score * 0.7 + tool_score * 0.3
        passed = final_score >= 0.5

        return EvaluationScore(
            dimension=self.dimension,
            score=final_score,
            weight=self.weight,
            details={
                "duration_seconds": duration_sec,
                "max_allowed_seconds": max_duration,
                "time_score": time_score,
                "tool_ratio": tool_ratio
            },
            passed=passed
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_efficiency_eval.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/evaluators/efficiency_eval.py tests/test_efficiency_eval.py && git commit -m "feat(harness): add EfficiencyEvaluator"
```

---

### Task 15: Implement RobustnessEvaluator

**Files:**
- Create: `agents/harness/core/evaluators/robustness_eval.py`
- Create: `tests/test_robustness_eval.py`

**Step 1: Write the failing test**

```python
# tests/test_robustness_eval.py
import pytest
from agents.harness.core.evaluators.robustness_eval import RobustnessEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, SubtaskRecord
from agents.harness.core.task_set import Task, SuccessCriteria, RobustnessCriteria
from agents.harness.core.mode import HarnessMode
from datetime import datetime

def test_robustness_eval_no_failures():
    evaluator = RobustnessEvaluator()
    trace = HarnessTrace(
        task_id="test_001",
        session_id="sess_001",
        mode=HarnessMode.REAL,
        start_time=datetime.now(),
        subtask_graph=[],
        final_status=TaskStatus.COMPLETED
    )
    task = Task(
        task_id="test_001",
        description="test",
        robot_type="arm",
        success_criteria=SuccessCriteria(
            robustness=RobustnessCriteria(max_retry_count=2, allowed_failures=[])
        )
    )

    score = evaluator.evaluate(trace, task)
    assert score.dimension == "robustness"
    assert score.score == 1.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_robustness_eval.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/evaluators/robustness_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace, TaskStatus

class RobustnessEvaluator(Evaluator):
    dimension = "robustness"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        allowed_failures = set(task.success_criteria.robustness.allowed_failures)
        max_retries = task.success_criteria.robustness.max_retry_count

        # Count retries from tool calls (retry via same skill)
        retry_count = sum(1 for tc in trace.tool_calls if "retry" in tc.result.lower())

        # Retry score
        retry_score = 1.0 if retry_count <= max_retries else 0.0

        # Failure handling score
        failed_subtasks = [s for s in trace.subtask_graph if s.status == "failed"]
        if not failed_subtasks:
            failure_handling_score = 1.0
        else:
            # Check if call_human was invoked on failure
            human_called = any(tc.tool_name == "call_human" for tc in trace.tool_calls)
            failure_handling_score = 1.0 if human_called else 0.5

        # Unexpected failures
        unexpected = retry_count > max_retries
        unexpected_score = 0.0 if unexpected else 1.0

        final_score = (retry_score + failure_handling_score + unexpected_score) / 3
        passed = final_score >= 0.5

        return EvaluationScore(
            dimension=self.dimension,
            score=final_score,
            weight=self.weight,
            details={
                "retry_count": retry_count,
                "max_retries": max_retries,
                "failed_subtasks": len(failed_subtasks),
                "failure_handling_score": failure_handling_score
            },
            passed=passed
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_robustness_eval.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/evaluators/robustness_eval.py tests/test_robustness_eval.py && git commit -m "feat(harness): add RobustnessEvaluator"
```

---

### Task 16: Implement ExplainabilityEvaluator

**Files:**
- Create: `agents/harness/core/evaluators/explainability_eval.py`
- Create: `tests/test_explainability_eval.py`

**Step 1: Write the failing test**

```python
# tests/test_explainability_eval.py
import pytest
from agents.harness.core.evaluators.explainability_eval import ExplainabilityEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, CoTDecisionRecord
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode
from datetime import datetime

def test_explainability_eval_complete_cot():
    evaluator = ExplainabilityEvaluator()
    trace = HarnessTrace(
        task_id="test_001",
        session_id="sess_001",
        mode=HarnessMode.REAL,
        start_time=datetime.now(),
        cot_decisions=[
            CoTDecisionRecord(
                timestamp=datetime.now(),
                task_state="progressing",
                action_type="skill",
                action_name="grasp",
                action_args={},
                reasoning="Step 1: Observe environment..."
            )
        ],
        final_status=TaskStatus.COMPLETED
    )
    task = Task(task_id="test_001", description="test", robot_type="arm")

    score = evaluator.evaluate(trace, task)
    assert score.dimension == "explainability"
    assert score.score > 0.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_explainability_eval.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/evaluators/explainability_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace, TaskStatus

class ExplainabilityEvaluator(Evaluator):
    dimension = "explainability"
    weight = 0.25

    REQUIRED_COT_STEPS = ["observe", "objective", "success", "evaluate", "action"]

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        if not trace.cot_decisions:
            return EvaluationScore(
                dimension=self.dimension,
                score=0.0,
                weight=self.weight,
                details={"reason": "no cot decisions recorded"},
                passed=False
            )

        # Completeness: check if CoT has required steps
        cot_text = " ".join(d.reasoning.lower() for d in trace.cot_decisions)
        steps_found = sum(1 for step in self.REQUIRED_COT_STEPS if step in cot_text)
        completeness = steps_found / len(self.REQUIRED_COT_STEPS)

        # Decision alignment: action name should be consistent with reasoning
        alignment_count = 0
        for d in trace.cot_decisions:
            if d.action_name and d.action_name.lower() in d.reasoning.lower():
                alignment_count += 1
        alignment = alignment_count / len(trace.cot_decisions)

        # Coherence: reasoning should have reasonable length
        coherence = 0.5
        for d in trace.cot_decisions:
            if len(d.reasoning) > 50:
                coherence = 1.0
                break

        final_score = completeness * 0.4 + alignment * 0.3 + coherence * 0.3
        passed = final_score >= 0.4

        return EvaluationScore(
            dimension=self.dimension,
            score=final_score,
            weight=self.weight,
            details={
                "completeness": completeness,
                "alignment": alignment,
                "coherence": coherence,
                "cot_decision_count": len(trace.cot_decisions)
            },
            passed=passed
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_explainability_eval.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/evaluators/explainability_eval.py tests/test_explainability_eval.py && git commit -m "feat(harness): add ExplainabilityEvaluator"
```

---

## Phase 6: Scorer（汇总报告）

### Task 17: Implement HarnessScorer

**Files:**
- Create: `agents/harness/core/scorer.py`
- Create: `tests/test_scorer.py`

**Step 1: Write the failing test**

```python
# tests/test_scorer.py
import pytest
from agents.harness.core.scorer import HarnessScorer, ScoreReport, EvaluationResult
from agents.harness.core.evaluators.base import EvaluationScore
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode
from datetime import datetime

def test_scorer_single_result():
    scorer = HarnessScorer(pass_threshold=0.7)

    trace = HarnessTrace(
        task_id="test_001",
        session_id="sess_001",
        mode=HarnessMode.REAL,
        start_time=datetime.now(),
        final_status=TaskStatus.COMPLETED
    )
    task = Task(task_id="test_001", description="test", robot_type="arm")

    result = EvaluationResult(
        task_id="test_001",
        trace=trace,
        result_score=EvaluationScore("result", 1.0, 0.25, {}, True),
        efficiency_score=EvaluationScore("efficiency", 1.0, 0.25, {}, True),
        robustness_score=EvaluationScore("robustness", 1.0, 0.25, {}, True),
        explainability_score=EvaluationScore("explainability", 1.0, 0.25, {}, True),
        total_score=1.0,
        overall_passed=True,
        recommendation=""
    )

    report = scorer.score([result])
    assert report.total_tasks == 1
    assert report.passed == 1
    assert report.pass_rate == 1.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scorer.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/core/scorer.py
from dataclasses import dataclass, field
from typing import list
from agents.harness.core.evaluators.base import EvaluationScore
from agents.harness.core.tracer import HarnessTrace
from agents.harness.core.task_set import Task

@dataclass
class EvaluationResult:
    task_id: str
    trace: HarnessTrace
    result_score: EvaluationScore
    efficiency_score: EvaluationScore
    robustness_score: EvaluationScore
    explainability_score: EvaluationScore
    total_score: float
    overall_passed: bool
    recommendation: str = ""

    def __post_init__(self):
        self.total_score = (
            self.result_score.score * self.result_score.weight +
            self.efficiency_score.score * self.efficiency_score.weight +
            self.robustness_score.score * self.robustness_score.weight +
            self.explainability_score.score * self.explainability_score.weight
        )

@dataclass
class ScoreReport:
    total_tasks: int
    passed: int
    pass_rate: float
    avg_result_score: float
    avg_efficiency_score: float
    avg_robustness_score: float
    avg_explainability_score: float
    detailed_results: list[EvaluationResult] = field(default_factory=list)
    regression_failures: list[EvaluationResult] = field(default_factory=list)

class HarnessScorer:
    def __init__(self, pass_threshold: float = 0.70):
        self.pass_threshold = pass_threshold

    def score(self, results: list[EvaluationResult]) -> ScoreReport:
        if not results:
            return ScoreReport(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

        total = len(results)
        passed = sum(1 for r in results if r.overall_passed)

        return ScoreReport(
            total_tasks=total,
            passed=passed,
            pass_rate=passed / total,
            avg_result_score=sum(r.result_score.score for r in results) / total,
            avg_efficiency_score=sum(r.efficiency_score.score for r in results) / total,
            avg_robustness_score=sum(r.robustness_score.score for r in results) / total,
            avg_explainability_score=sum(r.explainability_score.score for r in results) / total,
            detailed_results=results,
            regression_failures=[r for r in results if r.task_id.startswith("regression_")]
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scorer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/core/scorer.py tests/test_scorer.py && git commit -m "feat(harness): add HarnessScorer and ScoreReport"
```

---

## Phase 7: Integration（集成）

### Task 18: Implement attach_harness integration

**Files:**
- Create: `agents/harness/integration.py`
- Create: `tests/test_integration.py`

**Step 1: Write the failing test**

```python
# tests/test_integration.py
import pytest
from agents.harness.integration import attach_harness, FailureDataIntegrator
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode
from agents.channels.agent_loop import RobotAgentLoop
from agents.channels.bus import MessageBus
from agents.llm.provider import LLMProvider

def test_attach_harness_returns_tuple():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    bus = MessageBus()
    provider = LLMProvider()

    loop = RobotAgentLoop(bus=bus, provider=provider)

    wrapped_loop, tracer = attach_harness(loop, config)
    assert wrapped_loop is not None
    assert tracer is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# agents/harness/integration.py
from agents.channels.agent_loop import RobotAgentLoop
from agents.harness.core.config import HarnessConfig
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.core.tracer import HarnessTracer
from agents.harness.mocks.hardware_mocks import MockArmAdapter

def attach_harness(
    loop: RobotAgentLoop,
    config: HarnessConfig,
) -> tuple[RobotAgentLoop, HarnessTracer]:
    """
    Attach Harness capabilities to an existing RobotAgentLoop.
    Returns the wrapped loop and tracer instance.
    """
    tracer = HarnessTracer(config)

    if config.mode != HarnessMode.REAL:
        env = HarnessEnvironment.create(config)
        if config.mode == HarnessMode.HARDWARE_MOCK:
            # Wrap tool registry with hardware mocks
            loop = _wrap_with_hardware_mock(loop, env)

    # Attach tracer to loop
    loop = tracer.wrap_agent_loop(loop)

    return loop, tracer

def _wrap_with_hardware_mock(loop: RobotAgentLoop, env: HarnessEnvironment) -> RobotAgentLoop:
    # TODO: Replace tool handlers with mock implementations
    return loop
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/integration.py tests/test_integration.py && git commit -m "feat(harness): add attach_harness integration"
```

---

### Task 19: Implement FailureDataIntegrator

**Files:**
- Modify: `agents/harness/integration.py`

**Step 1: Write the failing test**

```python
# tests/test_failure_integrator.py
import pytest
from pathlib import Path
from agents.harness.integration import FailureDataIntegrator
from agents.harness.core.task_set import TaskSet

def test_integrator_syncs_failure_logs(tmp_path):
    # Create a fake failure directory
    failure_dir = tmp_path / "failure_data"
    failure_dir.mkdir()

    ts_dir = failure_dir / "2026-03-30_10-00-00"
    ts_dir.mkdir()
    (ts_dir / "metadata.json").write_text('{"task_description": "failed task", "robot_type": "arm"}')

    integrator = FailureDataIntegrator(failure_dir)
    task_set = integrator.sync_regression_tasks(TaskSet())

    assert len(task_set.regression) == 1
    assert task_set.regression[0].task_id.startswith("regression_")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_failure_integrator.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# Add to agents/harness/integration.py

class FailureDataIntegrator:
    """Sync failure data from FailureRecorder to TaskSet regression tasks."""

    def __init__(self, failure_log_dir: str | Path):
        self.failure_log_dir = Path(failure_log_dir)

    def sync_regression_tasks(self, task_set: TaskSet) -> TaskSet:
        for failure_dir in self.failure_log_dir.iterdir():
            if not failure_dir.is_dir():
                continue

            task_id = f"regression_{failure_dir.name}"
            if any(t.task_id == task_id for t in task_set.regression):
                continue

            metadata_file = failure_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            import json
            try:
                meta = json.loads(metadata_file.read_text())
                from agents.harness.core.task_set import Task
                task = Task(
                    task_id=task_id,
                    description=meta.get("task_description", "regression task"),
                    robot_type=meta.get("robot_type", "arm"),
                    scene={},
                    expected_skills=[],
                    is_regression=True,
                    tags=["regression"]
                )
                task_set.regression.append(task)
            except Exception:
                continue

        return task_set
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_failure_integrator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/harness/integration.py tests/test_failure_integrator.py && git commit -m "feat(harness): add FailureDataIntegrator"
```

---

## Phase 8: Examples（示例和完整测试）

### Task 20: Create run_harness example

**Files:**
- Create: `agents/harness/examples/run_harness.py`

**Step 1: Write example script**

```python
#!/usr/bin/env python3
"""Run a single harness task for evaluation."""

import asyncio
import argparse
from pathlib import Path

from agents.harness.core.config import HarnessConfig
from agents.harness.core.task_loader import TaskLoader
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.core.tracer import HarnessTracer
from agents.harness.core.evaluators.result_eval import ResultEvaluator
from agents.harness.core.evaluators.efficiency_eval import EfficiencyEvaluator
from agents.harness.core.evaluators.robustness_eval import RobustnessEvaluator
from agents.harness.core.evaluators.explainability_eval import ExplainabilityEvaluator
from agents.harness.core.scorer import HarnessScorer, EvaluationResult


async def run_task(task, config):
    """Run a single task with harness."""
    env = HarnessEnvironment.create(config)
    tracer = HarnessTracer(config)

    tracer.start_trace(task.task_id, session_id=f"session_{task.task_id}")

    # TODO: Execute task via agent loop or mock

    trace = tracer.stop_trace()
    return trace


def main():
    parser = argparse.ArgumentParser(description="Run Agent Harness evaluation")
    parser.add_argument("--task", required=True, help="Task YAML file path")
    parser.add_argument("--config", default="agents/harness/config.yaml", help="Config file")
    parser.add_argument("--mode", default=None, help="Override harness mode")
    args = parser.parse_args()

    # Load config
    config = HarnessConfig.from_yaml(args.config)
    if args.mode:
        from agents.harness.core.mode import HarnessMode
        config.mode = HarnessMode.from_string(args.mode)

    # Load task
    loader = TaskLoader()
    task_set = loader.load_from_dir(Path(args.task).parent)
    task = next((t for t in task_set.declarative if t.task_id + ".yaml" in args.task), None)
    if not task:
        print(f"Task not found: {args.task}")
        return

    # Run
    trace = asyncio.run(run_task(task, config))

    # Evaluate
    evaluators = [
        ResultEvaluator(),
        EfficiencyEvaluator(),
        RobustnessEvaluator(),
        ExplainabilityEvaluator(),
    ]

    from agents.harness.core.scorer import HarnessScorer
    scorer = HarnessScorer(pass_threshold=config.pass_threshold)

    scores = [e.evaluate(trace, task) for e in evaluators]
    result = EvaluationResult(
        task_id=task.task_id,
        trace=trace,
        result_score=scores[0],
        efficiency_score=scores[1],
        robustness_score=scores[2],
        explainability_score=scores[3],
        total_score=0.0,
        overall_passed=False,
    )
    result.total_score = (
        result.result_score.score * result.result_score.weight +
        result.efficiency_score.score * result.efficiency_score.weight +
        result.robustness_score.score * result.robustness_score.weight +
        result.explainability_score.score * result.explainability_score.weight
    )
    result.overall_passed = result.total_score >= config.pass_threshold

    # Report
    report = scorer.score([result])
    print(f"\n{'='*50}")
    print(f"Task: {task.task_id}")
    print(f"Score: {report.avg_result_score:.2f} (Result), {report.avg_efficiency_score:.2f} (Efficiency)")
    print(f"       {report.avg_robustness_score:.2f} (Robustness), {report.avg_explainability_score:.2f} (Explainability)")
    print(f"Total: {result.total_score:.2f} - {'PASS' if result.overall_passed else 'FAIL'}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
```

**Step 2: Run example to verify it works**

Run: `python agents/harness/examples/run_harness.py --task agents/harness/tasks/pick_place_basic.yaml`
Expected: Script runs without import errors

**Step 3: Commit**

```bash
git add agents/harness/examples/run_harness.py && git commit -m "feat(harness): add run_harness example script"
```

---

## Summary

| Phase | Tasks | Priority |
|-------|-------|----------|
| 1: Foundation | 1-3 | High |
| 2: TaskSet | 4-5 | High |
| 3: HarnessEnv | 6-9 | High |
| 4: Tracer | 10-11 | High |
| 5: Evaluators | 12-16 | High |
| 6: Scorer | 17 | Medium |
| 7: Integration | 18-19 | Medium |
| 8: Examples | 20 | Low |

**Total: 20 tasks**

---

## Dependencies

- Phase 1 must complete before Phase 2
- Phase 2 must complete before Phase 3
- Phase 3 (HarnessEnv) is prerequisite for Phase 7 (Integration)
- Phase 4 (Tracer) can be developed in parallel with Phase 3
- Phase 5 (Evaluators) depends on Phase 4 (Tracer data structures)
- Phase 6 (Scorer) depends on Phase 5
- Phase 7 (Integration) depends on Phase 1-4
- Phase 8 (Examples) depends on all previous phases
