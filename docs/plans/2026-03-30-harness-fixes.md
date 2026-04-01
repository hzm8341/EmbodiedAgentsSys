# Agent Harness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Agent Harness 设计评估中发现的 7 个漏洞，确保 harness 框架能被正确构建和运行。

**Architecture:** 先修复 P0 数据结构 Bug，再补全 attach_harness 拦截器，修正评分逻辑（skill 命名空间、Explainability 权重、回归任务），最后补充端到端集成入口。所有修改在 `agents/harness/` 目录下，对现有 `RobotAgentLoop` 零侵入。

**Tech Stack:** Python 3.10+, pytest, PyYAML, asyncio, dataclasses

**前置知识：**
- `agents/hardware/arm_adapter.py` 中已存在 `ArmAdapter`, `Pose6D`, `RobotState`, `RobotCapabilities`（接口稳定，可直接继承）
- `agents/channels/agent_loop.py` 中 `RobotAgentLoop` 通过 `_dispatch_action` 调用工具；skill 以 `start_policy(skill_id="manipulation.grasp")` 形式调用，即 tool_name 是 `start_policy`，skill_id 在 args 里
- `agents/memory/failure_log.py` 中 `FailureRecord` 含 `skill_id`, `robot_type`, `task_description` 字段
- harness 目录尚不存在，需要从零创建

---

## 文件结构

```
agents/harness/                        # 新建
├── __init__.py                        # 公开 API + attach_harness
├── config.yaml                        # 默认配置
├── core/
│   ├── __init__.py
│   ├── mode.py                        # HarnessMode enum
│   ├── config.py                      # HarnessConfig dataclass
│   ├── task_set.py                    # Task + TaskSet (@dataclass 修复)
│   ├── task_loader.py                 # YAML + failure log 加载
│   ├── harness_env.py                 # HarnessEnvironment
│   ├── tracer.py                      # HarnessTracer (含 skill_calls 字段)
│   ├── trace_replayer.py              # 离线回放
│   ├── scorer.py                      # HarnessScorer + ScoreReport
│   └── evaluators/
│       ├── __init__.py
│       ├── base.py                    # Evaluator ABC + EvaluationScore
│       ├── result_eval.py             # 修复: 从 start_policy args 提取 skill_id
│       ├── efficiency_eval.py
│       ├── robustness_eval.py
│       └── explainability_eval.py    # 修复: mode-aware 权重
├── mocks/
│   ├── __init__.py
│   ├── skill_mocks.py
│   ├── hardware_mocks.py              # 继承真实 ArmAdapter
│   └── vla_mocks.py
├── integration.py                     # attach_harness 拦截器实现 (新增)
├── runner.py                          # 端到端运行入口 (新增)
├── tasks/
│   ├── pick_place_basic.yaml
│   └── inspect_task.yaml
└── traces/                            # 运行时生成
```

---

## Phase 1: 基础设施

### Task 1: 创建目录结构 + HarnessMode

**Files:**
- Create: `agents/harness/__init__.py`
- Create: `agents/harness/core/__init__.py`
- Create: `agents/harness/core/evaluators/__init__.py`
- Create: `agents/harness/mocks/__init__.py`
- Create: `agents/harness/core/mode.py`
- Create: `tests/test_harness_mode.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p agents/harness/core/evaluators agents/harness/mocks agents/harness/tasks agents/harness/traces
touch agents/harness/__init__.py agents/harness/core/__init__.py agents/harness/core/evaluators/__init__.py agents/harness/mocks/__init__.py
touch agents/harness/tasks/.gitkeep agents/harness/traces/.gitkeep
```

- [ ] **Step 2: 写 failing test**

```python
# tests/test_harness_mode.py
from agents.harness.core.mode import HarnessMode

def test_harness_mode_enum_values():
    assert HarnessMode.SKILL_MOCK.value == "skill_mock"
    assert HarnessMode.HARDWARE_MOCK.value == "hardware_mock"
    assert HarnessMode.FULL_MOCK.value == "full_mock"
    assert HarnessMode.REAL.value == "real"

def test_harness_mode_from_string():
    assert HarnessMode.from_string("skill_mock") == HarnessMode.SKILL_MOCK
    assert HarnessMode.from_string("HARDWARE_MOCK") == HarnessMode.HARDWARE_MOCK

def test_harness_mode_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        HarnessMode.from_string("nonexistent")
```

- [ ] **Step 3: 运行确认 FAIL**

Run: `pytest tests/test_harness_mode.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 4: 实现 HarnessMode**

```python
# agents/harness/core/mode.py
from enum import Enum


class HarnessMode(str, Enum):
    SKILL_MOCK = "skill_mock"
    HARDWARE_MOCK = "hardware_mock"
    FULL_MOCK = "full_mock"
    REAL = "real"

    @classmethod
    def from_string(cls, value: str) -> "HarnessMode":
        v = value.lower()
        for mode in cls:
            if mode.value == v:
                return mode
        raise ValueError(f"Unknown HarnessMode: {value!r}")
```

- [ ] **Step 5: 运行确认 PASS**

Run: `pytest tests/test_harness_mode.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add agents/harness/ tests/test_harness_mode.py
git commit -m "feat(harness): create directory structure and HarnessMode"
```

---

### Task 2: HarnessConfig

**Files:**
- Create: `agents/harness/core/config.py`
- Create: `agents/harness/config.yaml`
- Create: `tests/test_harness_config.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_harness_config.py
import pytest
from agents.harness.core.config import HarnessConfig, SkillMockConfig
from agents.harness.core.mode import HarnessMode

def test_default_config():
    cfg = HarnessConfig()
    assert cfg.mode == HarnessMode.HARDWARE_MOCK
    assert cfg.robot_type == "arm"
    assert cfg.auto_attach is False
    assert cfg.tracing_enabled is True
    assert cfg.pass_threshold == 0.70

def test_config_from_dict():
    data = {
        "harness": {"mode": "skill_mock", "robot_type": "arm", "auto_attach": True},
        "skill_mock": {"default_success_rate": 0.9},
    }
    cfg = HarnessConfig.from_dict(data)
    assert cfg.mode == HarnessMode.SKILL_MOCK
    assert cfg.skill_mock.default_success_rate == 0.9
    assert cfg.auto_attach is True

def test_config_from_yaml(tmp_path):
    import yaml
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("harness:\n  mode: full_mock\n")
    cfg = HarnessConfig.from_yaml(str(yaml_path))
    assert cfg.mode == HarnessMode.FULL_MOCK
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_harness_config.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 HarnessConfig**

```python
# agents/harness/core/config.py
from __future__ import annotations
from dataclasses import dataclass, field
import yaml
from agents.harness.core.mode import HarnessMode


@dataclass
class SkillMockConfig:
    default_success_rate: float = 0.85
    latency_ms: int = 50
    per_skill_rate: dict = field(default_factory=dict)


@dataclass
class HardwareMockConfig:
    default_success_rate: float = 0.85
    latency_ms: int = 50
    joint_error_rate: float = 0.05
    gripper_slope_rate: float = 0.1
    position_noise: float = 0.005


@dataclass
class FullMockConfig:
    default_success_rate: float = 0.85
    latency_ms: int = 50
    vla_success_rate: float = 0.75
    vla_action_noise: bool = True


@dataclass
class HarnessConfig:
    mode: HarnessMode = HarnessMode.HARDWARE_MOCK
    robot_type: str = "arm"
    auto_attach: bool = False
    tracing_enabled: bool = True
    trace_dir: str = "agents/harness/traces"
    auto_append_regression: bool = True
    pass_threshold: float = 0.70
    task_timeout: int = 60

    skill_mock: SkillMockConfig = field(default_factory=SkillMockConfig)
    hardware_mock: HardwareMockConfig = field(default_factory=HardwareMockConfig)
    full_mock: FullMockConfig = field(default_factory=FullMockConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "HarnessConfig":
        h = data.get("harness", {})
        cfg = cls(mode=HarnessMode.from_string(h.get("mode", "hardware_mock")))
        cfg.robot_type = h.get("robot_type", "arm")
        cfg.auto_attach = h.get("auto_attach", False)
        cfg.tracing_enabled = h.get("tracing_enabled", True)
        cfg.trace_dir = h.get("trace_dir", "agents/harness/traces")
        cfg.auto_append_regression = h.get("auto_append_regression", True)
        cfg.pass_threshold = h.get("pass_threshold", 0.70)
        cfg.task_timeout = h.get("task_timeout", 60)

        if sm := data.get("skill_mock"):
            cfg.skill_mock = SkillMockConfig(
                default_success_rate=sm.get("default_success_rate", 0.85),
                latency_ms=sm.get("latency_ms", 50),
                per_skill_rate=sm.get("per_skill_rate", {}),
            )
        if hm := data.get("hardware_mock"):
            cfg.hardware_mock = HardwareMockConfig(
                default_success_rate=hm.get("default_success_rate", 0.85),
                latency_ms=hm.get("latency_ms", 50),
                joint_error_rate=hm.get("joint_error_rate", 0.05),
                gripper_slope_rate=hm.get("gripper_slope_rate", 0.1),
                position_noise=hm.get("position_noise", 0.005),
            )
        if fm := data.get("full_mock"):
            cfg.full_mock = FullMockConfig(
                default_success_rate=fm.get("default_success_rate", 0.85),
                latency_ms=fm.get("latency_ms", 50),
                vla_success_rate=fm.get("vla_success_rate", 0.75),
                vla_action_noise=fm.get("vla_action_noise", True),
            )
        return cfg

    @classmethod
    def from_yaml(cls, path: str) -> "HarnessConfig":
        with open(path) as f:
            return cls.from_dict(yaml.safe_load(f) or {})
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
  pass_threshold: 0.70
  task_timeout: 60

skill_mock:
  default_success_rate: 0.85
  latency_ms: 50
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
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_harness_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/config.py agents/harness/config.yaml tests/test_harness_config.py
git commit -m "feat(harness): add HarnessConfig"
```

---

## Phase 2: TaskSet（修复 P0 Bug）

### Task 3: Task + TaskSet（修复 @dataclass 缺失）

**重要：** 原始实现计划中 `TaskSet` 缺少 `@dataclass` 装饰器，导致 `declarative`/`regression`/`custom` 成为类变量（所有实例共享），多个 TaskSet 实例会互相污染数据。本任务修复此 Bug。

**Files:**
- Create: `agents/harness/core/task_set.py`
- Create: `tests/test_task_set.py`

- [ ] **Step 1: 写 failing test（含 Bug 验证）**

```python
# tests/test_task_set.py
import pytest
from agents.harness.core.task_set import Task, TaskSet, SuccessCriteria, EfficiencyCriteria


def test_task_creation():
    t = Task(task_id="t1", description="test", robot_type="arm")
    assert t.task_id == "t1"
    assert t.expected_skills == []
    assert t.is_regression is False


def test_task_from_dict():
    data = {
        "task_id": "pick_001",
        "description": "Pick red cube",
        "robot_type": "arm",
        "scene": {
            "objects": [
                {"id": "cube", "type": "cube", "color": "red",
                 "initial_position": [0.3, -0.1, 0.05]}
            ]
        },
        "expected_skills": ["manipulation.reach", "manipulation.grasp"],
        "success_criteria": {
            "result": {"type": "position_match", "object": "cube",
                       "target": "zone_b", "tolerance": 0.02},
            "efficiency": {"max_duration_seconds": 30},
            "robustness": {"max_retry_count": 2, "allowed_failures": ["gripper_slope"]},
        },
        "tags": ["basic"],
    }
    t = Task.from_dict(data)
    assert t.task_id == "pick_001"
    assert len(t.scene_objects) == 1
    assert t.success_criteria.efficiency.max_duration_seconds == 30
    assert "manipulation.grasp" in t.expected_skills


def test_task_set_instances_are_independent():
    """Regression: TaskSet must use @dataclass so list fields are per-instance."""
    ts1 = TaskSet()
    ts2 = TaskSet()
    t = Task(task_id="x", description="x", robot_type="arm")
    ts1.declarative.append(t)
    assert len(ts2.declarative) == 0, "TaskSet instances share list — @dataclass missing!"


def test_task_set_all_tasks():
    ts = TaskSet()
    ts.declarative.append(Task(task_id="d1", description="", robot_type="arm"))
    ts.regression.append(Task(task_id="r1", description="", robot_type="arm", is_regression=True))
    assert len(ts.all_tasks()) == 2


def test_task_set_filter_by_tag():
    ts = TaskSet()
    ts.declarative.append(Task(task_id="a", description="", robot_type="arm", tags=["basic"]))
    ts.declarative.append(Task(task_id="b", description="", robot_type="arm", tags=["vision"]))
    filtered = ts.filter(["basic"])
    assert len(filtered.declarative) == 1
    assert filtered.declarative[0].task_id == "a"
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_task_set.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现（含 @dataclass 修复）**

```python
# agents/harness/core/task_set.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SceneObject:
    id: str
    type: str
    color: str = ""
    initial_position: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    size: list = field(default_factory=lambda: [0.05, 0.05, 0.05])


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
    scene_objects: list[SceneObject] = field(default_factory=list)
    expected_skills: list[str] = field(default_factory=list)
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    is_regression: bool = False
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        raw_objects = data.get("scene", {}).get("objects", [])
        objects = [SceneObject(**obj) for obj in raw_objects]

        sc = data.get("success_criteria", {})
        criteria = SuccessCriteria(
            result=ResultCriteria(**sc.get("result", {})),
            efficiency=EfficiencyCriteria(**sc.get("efficiency", {})),
            robustness=RobustnessCriteria(**sc.get("robustness", {})),
        )
        return cls(
            task_id=data["task_id"],
            description=data.get("description", ""),
            robot_type=data.get("robot_type", "arm"),
            scene_objects=objects,
            expected_skills=data.get("expected_skills", []),
            success_criteria=criteria,
            is_regression=data.get("is_regression", False),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "robot_type": self.robot_type,
            "scene": {"objects": [o.__dict__ for o in self.scene_objects]},
            "expected_skills": self.expected_skills,
            "success_criteria": {
                "result": self.success_criteria.result.__dict__,
                "efficiency": self.success_criteria.efficiency.__dict__,
                "robustness": self.success_criteria.robustness.__dict__,
            },
            "is_regression": self.is_regression,
            "tags": self.tags,
        }


@dataclass          # ← 关键修复：必须有 @dataclass，否则 field() 不生效
class TaskSet:
    declarative: list[Task] = field(default_factory=list)
    regression: list[Task] = field(default_factory=list)
    custom: list[Task] = field(default_factory=list)

    def all_tasks(self) -> list[Task]:
        return self.declarative + self.regression + self.custom

    def filter(self, tags: list[str]) -> "TaskSet":
        tag_set = set(tags)
        return TaskSet(
            declarative=[t for t in self.declarative if tag_set & set(t.tags)],
            regression=[t for t in self.regression if tag_set & set(t.tags)],
            custom=[t for t in self.custom if tag_set & set(t.tags)],
        )

    def merge(self, other: "TaskSet") -> "TaskSet":
        return TaskSet(
            declarative=self.declarative + other.declarative,
            regression=self.regression + other.regression,
            custom=self.custom + other.custom,
        )
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_task_set.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/task_set.py tests/test_task_set.py
git commit -m "feat(harness): add Task+TaskSet, fix missing @dataclass on TaskSet"
```

---

### Task 4: TaskLoader（修复回归任务 expected_skills）

**重要：** 原始实现从失败日志提取回归任务时 `expected_skills=[]`，导致 ResultEvaluator 无法评估。`FailureRecord` 中包含 `skill_id` 字段，用它填充 `expected_skills`。

**Files:**
- Create: `agents/harness/core/task_loader.py`
- Create: `agents/harness/tasks/pick_place_basic.yaml`
- Create: `agents/harness/tasks/inspect_task.yaml`
- Create: `tests/test_task_loader.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_task_loader.py
import json
import pytest
from pathlib import Path
from agents.harness.core.task_loader import TaskLoader


def test_load_tasks_from_dir(tmp_path):
    (tmp_path / "t1.yaml").write_text("""
task_id: test_001
description: Test task
robot_type: arm
scene:
  objects: []
expected_skills: ["manipulation.grasp"]
success_criteria:
  result: {}
  efficiency: {}
  robustness: {}
""")
    loader = TaskLoader()
    ts = loader.load_from_dir(tmp_path)
    assert len(ts.declarative) == 1
    assert ts.declarative[0].task_id == "test_001"


def test_load_from_failure_logs_extracts_skill_id(tmp_path):
    """Regression: expected_skills must be populated from FailureRecord.skill_id."""
    record = {
        "timestamp": "2026-03-30T10:00:00+00:00",
        "task_description": "pick apple",
        "subtask_id": "sub_001",
        "subtask_description": "grasp apple",
        "skill_id": "manipulation.grasp",
        "error_type": "grasp_failure",
        "error_detail": "gripper slipped",
        "robot_type": "arm",
        "scene_context": {},
    }
    log_file = tmp_path / "failure_log.ndjson"
    log_file.write_text(json.dumps(record) + "\n")

    loader = TaskLoader()
    ts = loader.load_from_failure_logs(log_file)
    assert len(ts.regression) == 1
    assert "manipulation.grasp" in ts.regression[0].expected_skills
    assert ts.regression[0].robot_type == "arm"


def test_load_skips_invalid_yaml(tmp_path):
    (tmp_path / "bad.yaml").write_text("not: a: task")
    loader = TaskLoader()
    ts = loader.load_from_dir(tmp_path)
    assert len(ts.declarative) == 0
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_task_loader.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 TaskLoader**

```python
# agents/harness/core/task_loader.py
from __future__ import annotations
import json
import yaml
from pathlib import Path
from agents.harness.core.task_set import Task, TaskSet


class TaskLoader:
    def load_from_dir(self, dir_path: str | Path) -> TaskSet:
        dir_path = Path(dir_path)
        ts = TaskSet()
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text())
                if data and "task_id" in data:
                    ts.declarative.append(Task.from_dict(data))
            except Exception:
                continue
        return ts

    def load_from_failure_logs(self, log_path: str | Path) -> TaskSet:
        """Build regression Tasks from FailureLog NDJSON file.

        Each FailureRecord becomes one regression Task.
        skill_id is used to populate expected_skills so ResultEvaluator
        can score skill coverage.
        """
        log_path = Path(log_path)
        ts = TaskSet()
        if not log_path.exists():
            return ts

        for line in log_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                skill_id = rec.get("skill_id")
                expected_skills = [skill_id] if skill_id else []
                task = Task(
                    task_id=f"regression_{rec.get('timestamp', 'unknown').replace(':', '-')}",
                    description=rec.get("task_description", "regression task"),
                    robot_type=rec.get("robot_type", "arm"),
                    expected_skills=expected_skills,
                    is_regression=True,
                    tags=["regression", rec.get("error_type", "unknown")],
                )
                ts.regression.append(task)
            except Exception:
                continue
        return ts
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
      color: ""
      initial_position: [0.5, 0.2, 0.0]
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
      color: ""
      initial_position: [0.3, 0.0, 0.1]
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

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_task_loader.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/task_loader.py agents/harness/tasks/ tests/test_task_loader.py
git commit -m "feat(harness): add TaskLoader, fix regression tasks populate expected_skills from skill_id"
```

---

## Phase 3: Tracer（含 skill_calls 字段）

### Task 5: HarnessTracer

**重要：** Tracer 需要单独记录 `skill_calls`（从 `start_policy` 的 args 中提取 `skill_id`），供 ResultEvaluator 使用。`tool_calls` 记录 MCP 工具名（如 `start_policy`），`skill_calls` 记录 skill ID（如 `manipulation.grasp`）。

**Files:**
- Create: `agents/harness/core/tracer.py`
- Create: `tests/test_tracer.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_tracer.py
import pytest
from datetime import datetime
from agents.harness.core.tracer import HarnessTracer, TaskStatus
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode


def test_tracer_start_stop():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("task_001", "sess_001")
    trace = tracer.stop_trace(TaskStatus.COMPLETED)
    assert trace.task_id == "task_001"
    assert trace.final_status == TaskStatus.COMPLETED
    assert trace.duration_ms is not None
    assert trace.duration_ms >= 0


def test_tracer_records_tool_call():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("t1", "s1")
    tracer.record_tool_call("env_summary", {}, "ok")
    trace = tracer.get_trace()
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "env_summary"


def test_tracer_extracts_skill_from_start_policy():
    """skill_calls must be populated when tool_name == 'start_policy'."""
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("t1", "s1")
    tracer.record_tool_call("start_policy", {"skill_id": "manipulation.grasp"}, "ok")
    trace = tracer.get_trace()
    assert "manipulation.grasp" in trace.skill_calls


def test_tracer_records_cot_decision():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("t1", "s1")
    tracer.record_cot_decision("running", "skill", "start_policy",
                               {"skill_id": "manipulation.reach"}, "reach first")
    trace = tracer.get_trace()
    assert len(trace.cot_decisions) == 1
    assert trace.cot_decisions[0].action_name == "start_policy"


def test_tracer_stop_without_start_raises():
    tracer = HarnessTracer(HarnessConfig())
    with pytest.raises(RuntimeError):
        tracer.stop_trace()
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_tracer.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 HarnessTracer**

```python
# agents/harness/core/tracer.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
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
    # skill_calls: skill IDs extracted from start_policy tool args
    skill_calls: list[str] = field(default_factory=list)
    observations: list[ObservationRecord] = field(default_factory=list)
    cot_decisions: list[CoTDecisionRecord] = field(default_factory=list)
    memory_snapshots: list[MemorySnapshot] = field(default_factory=list)
    final_status: str = TaskStatus.FAILED
    failure_reason: Optional[str] = None


class HarnessTracer:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self._trace: Optional[HarnessTrace] = None

    def start_trace(self, task_id: str, session_id: str) -> None:
        self._trace = HarnessTrace(
            task_id=task_id,
            session_id=session_id,
            mode=self.config.mode,
            start_time=datetime.now(),
        )

    def stop_trace(self, status: str = TaskStatus.COMPLETED,
                   failure_reason: Optional[str] = None) -> HarnessTrace:
        if self._trace is None:
            raise RuntimeError("Trace not started — call start_trace() first")
        self._trace.end_time = datetime.now()
        self._trace.duration_ms = int(
            (self._trace.end_time - self._trace.start_time).total_seconds() * 1000
        )
        self._trace.final_status = status
        self._trace.failure_reason = failure_reason
        return self._trace

    def record_tool_call(self, name: str, args: dict, result: str,
                         duration_ms: int = 0) -> None:
        if self._trace is None:
            return
        self._trace.tool_calls.append(ToolCallRecord(
            timestamp=datetime.now(),
            tool_name=name,
            args=args,
            result=result,
            duration_ms=duration_ms,
        ))
        # Extract skill_id from start_policy / change_policy calls
        if name in ("start_policy", "change_policy"):
            skill_id = args.get("skill_id", "")
            if skill_id and skill_id not in self._trace.skill_calls:
                self._trace.skill_calls.append(skill_id)

    def record_observation(self, content: str) -> None:
        if self._trace:
            self._trace.observations.append(ObservationRecord(
                timestamp=datetime.now(), content=content
            ))

    def record_cot_decision(self, task_state: str, action_type: str,
                            action_name: str, action_args: dict,
                            reasoning: str) -> None:
        if self._trace:
            self._trace.cot_decisions.append(CoTDecisionRecord(
                timestamp=datetime.now(),
                task_state=task_state,
                action_type=action_type,
                action_name=action_name,
                action_args=action_args,
                reasoning=reasoning,
            ))

    def record_memory_snapshot(self, role: str, task_graph_summary: str,
                               current_skill: Optional[str] = None) -> None:
        if self._trace:
            self._trace.memory_snapshots.append(MemorySnapshot(
                timestamp=datetime.now(),
                role=role,
                task_graph_summary=task_graph_summary,
                current_skill=current_skill,
            ))

    def get_trace(self) -> Optional[HarnessTrace]:
        return self._trace
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_tracer.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/tracer.py tests/test_tracer.py
git commit -m "feat(harness): add HarnessTracer with skill_calls extraction from start_policy args"
```

---

### Task 6: TraceReplayer

**Files:**
- Create: `agents/harness/core/trace_replayer.py`
- Create: `tests/test_trace_replayer.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_trace_replayer.py
import json
import pytest
from pathlib import Path
from agents.harness.core.trace_replayer import TraceReplayer
from agents.harness.core.tracer import TaskStatus


def test_replayer_loads_trace(tmp_path):
    trace_data = {
        "task_id": "test_001",
        "session_id": "sess_001",
        "mode": "hardware_mock",
        "start_time": "2026-03-30T10:00:00",
        "tool_calls": [],
        "skill_calls": ["manipulation.grasp"],
        "final_status": "completed",
    }
    (tmp_path / "trace_test_001.json").write_text(json.dumps(trace_data))
    replayer = TraceReplayer()
    trace = replayer.replay_from_file(tmp_path / "trace_test_001.json")
    assert trace.task_id == "test_001"
    assert trace.final_status == TaskStatus.COMPLETED
    assert "manipulation.grasp" in trace.skill_calls


def test_replayer_loads_dir(tmp_path):
    for i in range(3):
        (tmp_path / f"trace_{i}.json").write_text(json.dumps({
            "task_id": f"t{i}", "session_id": "s", "mode": "real",
            "start_time": "2026-03-30T10:00:00", "tool_calls": [],
            "skill_calls": [], "final_status": "completed",
        }))
    replayer = TraceReplayer()
    traces = replayer.replay_from_dir(tmp_path)
    assert len(traces) == 3
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_trace_replayer.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 TraceReplayer**

```python
# agents/harness/core/trace_replayer.py
from __future__ import annotations
import json
from pathlib import Path
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.mode import HarnessMode


class TraceReplayer:
    def replay_from_file(self, trace_path: Path | str) -> HarnessTrace:
        data = json.loads(Path(trace_path).read_text())
        from datetime import datetime
        start = data.get("start_time")
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(start)
            except ValueError:
                start = datetime.now()

        trace = HarnessTrace(
            task_id=data.get("task_id", ""),
            session_id=data.get("session_id", ""),
            mode=HarnessMode.from_string(data.get("mode", "real")),
            start_time=start,
            final_status=data.get("final_status", TaskStatus.FAILED),
            skill_calls=data.get("skill_calls", []),
        )
        return trace

    def replay_from_dir(self, dir_path: Path | str) -> list[HarnessTrace]:
        traces = []
        for f in sorted(Path(dir_path).glob("*.json")):
            try:
                traces.append(self.replay_from_file(f))
            except Exception:
                continue
        return traces
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_trace_replayer.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/trace_replayer.py tests/test_trace_replayer.py
git commit -m "feat(harness): add TraceReplayer"
```

---

## Phase 4: Evaluators（修复评分逻辑）

### Task 7: Evaluator 基类 + EvaluationScore

**Files:**
- Create: `agents/harness/core/evaluators/base.py`
- Create: `tests/test_evaluator_base.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_evaluator_base.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore


def test_evaluation_score():
    s = EvaluationScore(dimension="result", score=0.8, weight=0.25,
                        details={"note": "ok"}, passed=True)
    assert s.weighted_score == pytest.approx(0.8 * 0.25)

def test_evaluator_abstract():
    import pytest
    with pytest.raises(TypeError):
        Evaluator()  # abstract

import pytest
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_evaluator_base.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现基类**

```python
# agents/harness/core/evaluators/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.harness.core.task_set import Task
    from agents.harness.core.tracer import HarnessTrace


@dataclass
class EvaluationScore:
    dimension: str
    score: float        # 0.0 - 1.0
    weight: float       # contribution to total score
    details: dict
    passed: bool

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


class Evaluator(ABC):
    dimension: str = "base"
    weight: float = 1.0

    def evaluate(self, trace: "HarnessTrace", task: "Task") -> EvaluationScore:
        return self._do_evaluate(trace, task)

    @abstractmethod
    def _do_evaluate(self, trace: "HarnessTrace", task: "Task") -> EvaluationScore:
        raise NotImplementedError
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_evaluator_base.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/evaluators/base.py tests/test_evaluator_base.py
git commit -m "feat(harness): add Evaluator base class"
```

---

### Task 8: ResultEvaluator（修复 skill 命名空间）

**重要：** 原始实现用 `tc.tool_name` 比较 `expected_skills`，但 tool_name 是 `start_policy` 而 expected_skills 是 `manipulation.grasp`。修复：使用 `trace.skill_calls`（Task 5 中 Tracer 已提取）。

**Files:**
- Create: `agents/harness/core/evaluators/result_eval.py`
- Create: `tests/test_result_eval.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_result_eval.py
import pytest
from datetime import datetime
from agents.harness.core.evaluators.result_eval import ResultEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, ToolCallRecord
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode


def _make_trace(status=TaskStatus.COMPLETED, skill_calls=None, tool_calls=None):
    trace = HarnessTrace(
        task_id="t1", session_id="s1",
        mode=HarnessMode.HARDWARE_MOCK,
        start_time=datetime.now(),
        final_status=status,
        skill_calls=skill_calls or [],
        tool_calls=tool_calls or [],
    )
    return trace


def _make_task(expected_skills=None):
    return Task(task_id="t1", description="test", robot_type="arm",
                expected_skills=expected_skills or [])


def test_completed_task_full_skill_coverage():
    evaluator = ResultEvaluator()
    trace = _make_trace(
        status=TaskStatus.COMPLETED,
        skill_calls=["manipulation.reach", "manipulation.grasp", "manipulation.place"],
    )
    task = _make_task(["manipulation.reach", "manipulation.grasp", "manipulation.place"])
    score = evaluator.evaluate(trace, task)
    assert score.score == pytest.approx(1.0)
    assert score.passed is True


def test_failed_task_scores_zero():
    evaluator = ResultEvaluator()
    trace = _make_trace(status=TaskStatus.FAILED, skill_calls=[])
    task = _make_task(["manipulation.grasp"])
    score = evaluator.evaluate(trace, task)
    assert score.score == 0.0


def test_partial_skill_coverage():
    evaluator = ResultEvaluator()
    trace = _make_trace(
        status=TaskStatus.COMPLETED,
        skill_calls=["manipulation.grasp"],  # missing reach and place
    )
    task = _make_task(["manipulation.reach", "manipulation.grasp", "manipulation.place"])
    score = evaluator.evaluate(trace, task)
    # base=1.0, coverage=1/3 ≈ 0.333
    assert score.score == pytest.approx(1/3, abs=0.01)


def test_no_expected_skills_full_score():
    """Tasks with no expected_skills get full skill coverage."""
    evaluator = ResultEvaluator()
    trace = _make_trace(status=TaskStatus.COMPLETED)
    task = _make_task([])  # regression task might have no expected skills listed
    score = evaluator.evaluate(trace, task)
    assert score.score == pytest.approx(1.0)
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_result_eval.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现（使用 trace.skill_calls）**

```python
# agents/harness/core/evaluators/result_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace, TaskStatus


class ResultEvaluator(Evaluator):
    dimension = "result"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        # 1. Base score from task completion status
        if trace.final_status == TaskStatus.COMPLETED:
            base_score = 1.0
        elif trace.final_status == TaskStatus.FAILED:
            base_score = 0.0
        else:  # TIMEOUT / ABORTED
            base_score = 0.3

        # 2. Skill coverage: use trace.skill_calls (populated from start_policy args)
        #    NOT trace.tool_calls (those are MCP tool names, not skill IDs)
        expected = set(task.expected_skills)
        if not expected:
            skill_coverage = 1.0
        else:
            called = set(trace.skill_calls)
            skill_coverage = len(expected & called) / len(expected)

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
                "called_skills": list(trace.skill_calls),
            },
            passed=passed,
        )
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_result_eval.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/evaluators/result_eval.py tests/test_result_eval.py
git commit -m "feat(harness): add ResultEvaluator, fix skill namespace (use skill_calls not tool_name)"
```

---

### Task 9: EfficiencyEvaluator + RobustnessEvaluator

**Files:**
- Create: `agents/harness/core/evaluators/efficiency_eval.py`
- Create: `agents/harness/core/evaluators/robustness_eval.py`
- Create: `tests/test_efficiency_robustness_eval.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_efficiency_robustness_eval.py
import pytest
from datetime import datetime, timedelta
from agents.harness.core.evaluators.efficiency_eval import EfficiencyEvaluator
from agents.harness.core.evaluators.robustness_eval import RobustnessEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, ToolCallRecord
from agents.harness.core.task_set import Task, SuccessCriteria, EfficiencyCriteria, RobustnessCriteria
from agents.harness.core.mode import HarnessMode


def _make_trace(duration_ms=10000, tool_calls=None, status=TaskStatus.COMPLETED):
    start = datetime.now()
    t = HarnessTrace(
        task_id="t1", session_id="s1",
        mode=HarnessMode.HARDWARE_MOCK,
        start_time=start,
        end_time=start + timedelta(milliseconds=duration_ms),
        duration_ms=duration_ms,
        final_status=status,
        skill_calls=[],
        tool_calls=tool_calls or [],
    )
    return t


def _make_task(max_dur=30, max_retry=2):
    return Task(
        task_id="t1", description="test", robot_type="arm",
        success_criteria=SuccessCriteria(
            efficiency=EfficiencyCriteria(max_duration_seconds=max_dur),
            robustness=RobustnessCriteria(max_retry_count=max_retry),
        )
    )


# --- Efficiency ---
def test_efficiency_fast_task():
    score = EfficiencyEvaluator().evaluate(_make_trace(duration_ms=5000), _make_task(max_dur=30))
    assert score.score > 0.8


def test_efficiency_slow_task():
    score = EfficiencyEvaluator().evaluate(_make_trace(duration_ms=60000), _make_task(max_dur=30))
    assert score.score < 0.5


def test_efficiency_no_duration():
    trace = _make_trace()
    trace.duration_ms = None
    score = EfficiencyEvaluator().evaluate(trace, _make_task())
    assert 0.0 <= score.score <= 1.0


# --- Robustness ---
def test_robustness_no_retries():
    calls = [ToolCallRecord(datetime.now(), "start_policy", {}, "ok")]
    score = RobustnessEvaluator().evaluate(_make_trace(tool_calls=calls), _make_task())
    assert score.score == pytest.approx(1.0)


def test_robustness_within_limit():
    calls = [
        ToolCallRecord(datetime.now(), "start_policy", {}, "failed"),
        ToolCallRecord(datetime.now(), "start_policy", {}, "ok"),
    ]
    score = RobustnessEvaluator().evaluate(_make_trace(tool_calls=calls), _make_task(max_retry=2))
    assert score.score >= 0.5


def test_robustness_exceeded_limit():
    calls = [ToolCallRecord(datetime.now(), "start_policy", {}, "failed")] * 5
    score = RobustnessEvaluator().evaluate(_make_trace(tool_calls=calls), _make_task(max_retry=2))
    assert score.score < 0.5
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_efficiency_robustness_eval.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现两个 Evaluator**

```python
# agents/harness/core/evaluators/efficiency_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace


class EfficiencyEvaluator(Evaluator):
    dimension = "efficiency"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        max_dur = task.success_criteria.efficiency.max_duration_seconds
        duration_ms = trace.duration_ms

        if duration_ms is None:
            score = 0.5
            details = {"note": "duration not available"}
        else:
            duration_s = duration_ms / 1000.0
            if duration_s <= max_dur:
                score = 1.0 - (duration_s / max_dur) * 0.3  # fast tasks get near 1.0
            else:
                score = max(0.0, 1.0 - (duration_s / max_dur - 1.0))
            details = {
                "duration_s": duration_s,
                "max_duration_s": max_dur,
                "ratio": duration_s / max_dur if max_dur > 0 else 0,
            }

        return EvaluationScore(
            dimension=self.dimension, score=score,
            weight=self.weight, details=details, passed=score >= 0.5,
        )
```

```python
# agents/harness/core/evaluators/robustness_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace


class RobustnessEvaluator(Evaluator):
    dimension = "robustness"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        max_retries = task.success_criteria.robustness.max_retry_count
        # Count start_policy calls as proxy for retries (first call is not a retry)
        policy_calls = [tc for tc in trace.tool_calls if tc.tool_name == "start_policy"]
        retries = max(0, len(policy_calls) - 1)

        if retries == 0:
            score = 1.0
        elif retries <= max_retries:
            score = 1.0 - (retries / (max_retries + 1)) * 0.5
        else:
            score = max(0.0, 0.5 - (retries - max_retries) * 0.1)

        return EvaluationScore(
            dimension=self.dimension, score=score,
            weight=self.weight,
            details={"retries": retries, "max_retries": max_retries},
            passed=score >= 0.5,
        )
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_efficiency_robustness_eval.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/evaluators/efficiency_eval.py agents/harness/core/evaluators/robustness_eval.py tests/test_efficiency_robustness_eval.py
git commit -m "feat(harness): add EfficiencyEvaluator and RobustnessEvaluator"
```

---

### Task 10: ExplainabilityEvaluator（修复 mode-aware 权重）

**重要：** Mock 模式下 LLM 不运行，`cot_decisions` 为空，Explainability 得分永远为 0，拉低总分，掩盖真实结果。修复：mock 模式下检测到 `cot_decisions` 为空时，将该维度 weight 设为 0 并返回 N/A 分数，总分由其他三维重新归一化。

**Files:**
- Create: `agents/harness/core/evaluators/explainability_eval.py`
- Create: `tests/test_explainability_eval.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_explainability_eval.py
import pytest
from datetime import datetime
from agents.harness.core.evaluators.explainability_eval import ExplainabilityEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, CoTDecisionRecord
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode


def _make_trace(mode=HarnessMode.REAL, cot_decisions=None):
    return HarnessTrace(
        task_id="t1", session_id="s1",
        mode=mode,
        start_time=datetime.now(),
        final_status=TaskStatus.COMPLETED,
        skill_calls=[],
        cot_decisions=cot_decisions or [],
    )


def _make_task():
    return Task(task_id="t1", description="test", robot_type="arm",
                expected_skills=["manipulation.grasp"])


def test_explainability_mock_mode_no_cot_returns_na():
    """Mock mode with no CoT decisions: weight=0, score=N/A."""
    evaluator = ExplainabilityEvaluator()
    trace = _make_trace(mode=HarnessMode.SKILL_MOCK, cot_decisions=[])
    score = evaluator.evaluate(trace, _make_task())
    assert score.weight == 0.0
    assert score.details.get("mode_aware") is True


def test_explainability_real_mode_with_cot():
    evaluator = ExplainabilityEvaluator()
    decisions = [
        CoTDecisionRecord(datetime.now(), "running", "skill",
                          "start_policy", {"skill_id": "manipulation.grasp"},
                          "grasp object first")
    ]
    trace = _make_trace(mode=HarnessMode.REAL, cot_decisions=decisions)
    score = evaluator.evaluate(trace, _make_task())
    assert score.weight == 0.25
    assert score.score > 0.0


def test_explainability_real_mode_no_cot_penalized():
    """Real mode with no CoT decisions is suspicious — penalize."""
    evaluator = ExplainabilityEvaluator()
    trace = _make_trace(mode=HarnessMode.REAL, cot_decisions=[])
    score = evaluator.evaluate(trace, _make_task())
    assert score.weight == 0.25
    assert score.score == pytest.approx(0.0)
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_explainability_eval.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现（mode-aware 权重）**

```python
# agents/harness/core/evaluators/explainability_eval.py
from agents.harness.core.evaluators.base import Evaluator, EvaluationScore
from agents.harness.core.task_set import Task
from agents.harness.core.tracer import HarnessTrace
from agents.harness.core.mode import HarnessMode

_MOCK_MODES = {HarnessMode.SKILL_MOCK, HarnessMode.HARDWARE_MOCK, HarnessMode.FULL_MOCK}


class ExplainabilityEvaluator(Evaluator):
    dimension = "explainability"
    weight = 0.25

    def _do_evaluate(self, trace: HarnessTrace, task: Task) -> EvaluationScore:
        is_mock = trace.mode in _MOCK_MODES
        n_decisions = len(trace.cot_decisions)

        # Mock mode + no CoT data: skip this dimension (weight=0)
        # so the scorer can redistribute weight among the other 3 dimensions
        if is_mock and n_decisions == 0:
            return EvaluationScore(
                dimension=self.dimension,
                score=0.0,
                weight=0.0,   # ← key fix: excluded from scoring
                details={"mode_aware": True, "reason": "mock mode, no CoT data available"},
                passed=True,  # not a failure, just not applicable
            )

        # Real mode with no CoT: suspicious, penalize
        if n_decisions == 0:
            return EvaluationScore(
                dimension=self.dimension, score=0.0, weight=self.weight,
                details={"cot_count": 0, "note": "no CoT decisions recorded"},
                passed=False,
            )

        # Score based on: decision count, reasoning completeness
        decisions_with_reasoning = sum(
            1 for d in trace.cot_decisions if d.reasoning and len(d.reasoning) > 5
        )
        reasoning_completeness = decisions_with_reasoning / n_decisions

        # Check that decisions align with expected skills
        expected = set(task.expected_skills)
        decision_skills = {
            d.action_args.get("skill_id", "") for d in trace.cot_decisions
            if d.action_type == "skill"
        } - {""}
        skill_alignment = (
            len(expected & decision_skills) / len(expected) if expected else 1.0
        )

        score = 0.5 * reasoning_completeness + 0.5 * skill_alignment
        return EvaluationScore(
            dimension=self.dimension, score=score, weight=self.weight,
            details={
                "cot_count": n_decisions,
                "reasoning_completeness": reasoning_completeness,
                "skill_alignment": skill_alignment,
            },
            passed=score >= 0.5,
        )
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_explainability_eval.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/evaluators/explainability_eval.py tests/test_explainability_eval.py
git commit -m "feat(harness): add ExplainabilityEvaluator with mode-aware weight (mock mode excluded)"
```

---

### Task 11: HarnessScorer（归一化处理 weight=0 的维度）

**Files:**
- Create: `agents/harness/core/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_scorer.py
import pytest
from agents.harness.core.scorer import HarnessScorer, ScoreReport
from agents.harness.core.evaluators.base import EvaluationScore


def test_scorer_basic():
    scores = [
        EvaluationScore("result", 1.0, 0.25, {}, True),
        EvaluationScore("efficiency", 0.8, 0.25, {}, True),
        EvaluationScore("robustness", 0.9, 0.25, {}, True),
        EvaluationScore("explainability", 0.7, 0.25, {}, True),
    ]
    report = HarnessScorer(pass_threshold=0.70).score(scores)
    assert report.total_score == pytest.approx((1.0 + 0.8 + 0.9 + 0.7) / 4, abs=0.01)
    assert report.passed is True


def test_scorer_excludes_zero_weight_dimension():
    """When explainability weight=0 (mock mode), redistribute among other 3."""
    scores = [
        EvaluationScore("result", 1.0, 0.25, {}, True),
        EvaluationScore("efficiency", 0.8, 0.25, {}, True),
        EvaluationScore("robustness", 0.9, 0.25, {}, True),
        EvaluationScore("explainability", 0.0, 0.0, {}, True),  # excluded
    ]
    report = HarnessScorer(pass_threshold=0.70).score(scores)
    # Only 3 dimensions contribute: (1.0 + 0.8 + 0.9) / 3 ≈ 0.9
    assert report.total_score == pytest.approx((1.0 + 0.8 + 0.9) / 3, abs=0.01)
    assert report.passed is True
    assert len(report.active_dimensions) == 3


def test_scorer_fails_below_threshold():
    scores = [
        EvaluationScore("result", 0.2, 0.25, {}, False),
        EvaluationScore("efficiency", 0.3, 0.25, {}, False),
        EvaluationScore("robustness", 0.4, 0.25, {}, False),
        EvaluationScore("explainability", 0.1, 0.25, {}, False),
    ]
    report = HarnessScorer(pass_threshold=0.70).score(scores)
    assert report.passed is False
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_scorer.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 HarnessScorer**

```python
# agents/harness/core/scorer.py
from __future__ import annotations
from dataclasses import dataclass
from agents.harness.core.evaluators.base import EvaluationScore


@dataclass
class ScoreReport:
    task_id: str
    scores: list[EvaluationScore]
    active_dimensions: list[str]   # dimensions with weight > 0
    total_score: float
    passed: bool
    pass_threshold: float

    def summary(self) -> str:
        lines = [f"Task: {self.task_id}",
                 f"Total: {self.total_score:.3f} ({'PASS' if self.passed else 'FAIL'})"]
        for s in self.scores:
            flag = "" if s.weight > 0 else " [excluded]"
            lines.append(f"  {s.dimension}: {s.score:.3f} (w={s.weight:.2f}){flag}")
        return "\n".join(lines)


class HarnessScorer:
    def __init__(self, pass_threshold: float = 0.70):
        self.pass_threshold = pass_threshold

    def score(self, evaluation_scores: list[EvaluationScore],
              task_id: str = "") -> ScoreReport:
        active = [s for s in evaluation_scores if s.weight > 0]
        if not active:
            total = 0.0
        else:
            # Equal-weight average over active dimensions
            total = sum(s.score for s in active) / len(active)

        return ScoreReport(
            task_id=task_id,
            scores=evaluation_scores,
            active_dimensions=[s.dimension for s in active],
            total_score=total,
            passed=total >= self.pass_threshold,
            pass_threshold=self.pass_threshold,
        )
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_scorer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/core/scorer.py tests/test_scorer.py
git commit -m "feat(harness): add HarnessScorer with zero-weight dimension exclusion"
```

---

## Phase 5: Mocks

### Task 12: SkillMocks + HardwareMocks + VLAMocks

**Files:**
- Create: `agents/harness/mocks/skill_mocks.py`
- Create: `agents/harness/mocks/hardware_mocks.py`
- Create: `agents/harness/mocks/vla_mocks.py`
- Create: `agents/harness/core/harness_env.py`
- Create: `tests/test_mocks.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_mocks.py
import pytest
import asyncio
from agents.harness.mocks.skill_mocks import MockSkillRegistry
from agents.harness.mocks.hardware_mocks import MockArmAdapter
from agents.harness.mocks.vla_mocks import MockVLAAdapter
from agents.hardware.arm_adapter import Pose6D


def test_mock_skill_registry_returns_result():
    reg = MockSkillRegistry(default_success_rate=1.0)
    result = reg.call_skill("manipulation.grasp", {})
    assert result.success is True
    assert "manipulation.grasp" in result.content


def test_mock_skill_registry_zero_rate_fails():
    reg = MockSkillRegistry(default_success_rate=0.0)
    result = reg.call_skill("manipulation.grasp", {})
    assert result.success is False


def test_mock_arm_adapter_move():
    arm = MockArmAdapter()
    pose = Pose6D(x=0.3, y=0.0, z=0.2, roll=0, pitch=0, yaw=0)
    result = asyncio.run(arm.move_to_pose(pose))
    assert isinstance(result, bool)


def test_mock_arm_adapter_get_state():
    from agents.hardware.arm_adapter import RobotState
    arm = MockArmAdapter(joint_error_rate=0.0)
    state = asyncio.run(arm.get_state())
    assert isinstance(state, RobotState)
    assert 0.0 <= state.gripper_opening <= 1.0


def test_mock_vla_returns_action():
    vla = MockVLAAdapter(success_rate=1.0, action_noise=False)
    action = asyncio.run(vla.act({"image": "test"}, "grasp"))
    assert len(action) == 7
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_mocks.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 Mocks**

```python
# agents/harness/mocks/skill_mocks.py
from __future__ import annotations
import random
from dataclasses import dataclass, field


@dataclass
class SkillResult:
    success: bool
    content: str
    data: dict = field(default_factory=dict)


class MockSkillRegistry:
    def __init__(self, default_success_rate: float = 0.85,
                 per_skill_rate: dict | None = None):
        self.default_success_rate = default_success_rate
        self.per_skill_rate = per_skill_rate or {}

    def call_skill(self, skill_id: str, args: dict) -> SkillResult:
        rate = self.per_skill_rate.get(skill_id, self.default_success_rate)
        success = random.random() < rate
        return SkillResult(
            success=success,
            content=f"[mock] {skill_id} {'succeeded' if success else 'failed'}",
            data={"skill_id": skill_id},
        )
```

```python
# agents/harness/mocks/hardware_mocks.py
from __future__ import annotations
import asyncio
import random
from agents.hardware.arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities


class MockArmAdapter(ArmAdapter):
    def __init__(
        self,
        joint_error_rate: float = 0.05,
        gripper_slope_rate: float = 0.1,
        position_noise: float = 0.005,
        latency_ms: int = 50,
    ):
        self._joint_error_rate = joint_error_rate
        self._gripper_slope_rate = gripper_slope_rate
        self._position_noise = position_noise
        self._latency_ms = latency_ms
        self._gripper_open = 0.0
        self._joints = [0.0] * 7

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = [0.1] * 7
        return True

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = angles[:]
        return True

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        await asyncio.sleep(self._latency_ms / 2000.0)
        if random.random() < self._gripper_slope_rate:
            return False
        self._gripper_open = max(0.0, min(1.0, opening))
        return True

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=self._joints[:],
            end_effector_pose=Pose6D(x=0.3, y=0.0, z=0.2, roll=0, pitch=0, yaw=0),
            gripper_opening=self._gripper_open,
            is_moving=False,
            error_code=0,
        )

    async def is_ready(self) -> bool:
        return True

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=["manipulation.grasp", "manipulation.place", "manipulation.reach"],
        )
```

```python
# agents/harness/mocks/vla_mocks.py
from __future__ import annotations
import random


class MockVLAAdapter:
    def __init__(self, success_rate: float = 0.75, action_noise: bool = True):
        self.success_rate = success_rate
        self.action_noise = action_noise

    def reset(self) -> None:
        pass

    async def act(self, observation: dict, instruction: str) -> list[float]:
        base = [0.1, 0.0, 0.2, 0.0, 0.0, 0.0, 0.5]
        if self.action_noise:
            base = [a + random.gauss(0, 0.01) for a in base]
        return base

    async def execute(self, action: list[float]) -> dict:
        return {"success": random.random() < self.success_rate, "action": action}
```

```python
# agents/harness/core/harness_env.py
from __future__ import annotations
from agents.harness.core.mode import HarnessMode
from agents.harness.core.config import HarnessConfig
from agents.harness.mocks.skill_mocks import MockSkillRegistry
from agents.harness.mocks.hardware_mocks import MockArmAdapter
from agents.harness.mocks.vla_mocks import MockVLAAdapter


class HarnessEnvironment:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.mode = config.mode
        self.skill_registry: MockSkillRegistry | None = None
        self.arm_adapter: MockArmAdapter | None = None
        self.vla_adapter: MockVLAAdapter | None = None
        self._setup()

    def _setup(self) -> None:
        if self.mode in (HarnessMode.SKILL_MOCK, HarnessMode.FULL_MOCK):
            cfg = self.config.skill_mock
            self.skill_registry = MockSkillRegistry(
                default_success_rate=cfg.default_success_rate,
                per_skill_rate=cfg.per_skill_rate,
            )
        if self.mode in (HarnessMode.HARDWARE_MOCK, HarnessMode.FULL_MOCK):
            cfg = self.config.hardware_mock
            self.arm_adapter = MockArmAdapter(
                joint_error_rate=cfg.joint_error_rate,
                gripper_slope_rate=cfg.gripper_slope_rate,
                position_noise=cfg.position_noise,
                latency_ms=cfg.latency_ms,
            )
        if self.mode == HarnessMode.FULL_MOCK:
            cfg = self.config.full_mock
            self.vla_adapter = MockVLAAdapter(
                success_rate=cfg.vla_success_rate,
                action_noise=cfg.vla_action_noise,
            )

    @classmethod
    def create(cls, config: HarnessConfig) -> "HarnessEnvironment":
        return cls(config)
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_mocks.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/mocks/ agents/harness/core/harness_env.py tests/test_mocks.py
git commit -m "feat(harness): add SkillMocks, HardwareMocks, VLAMocks, HarnessEnvironment"
```

---

## Phase 6: attach_harness 拦截器（补全 P1 缺口）

### Task 13: integration.py — attach_harness

**重要：** 这是原始实现计划最大的遗漏。`attach_harness` 需要将 `HarnessTracer` 挂接到 `RobotAgentLoop`，在不修改 `RobotAgentLoop` 源码的前提下拦截工具调用和 CoT 决策。

实现方案：用子类包装 `ToolRegistry` 和 `CoTTaskPlanner`，在调用前后插入追踪代码。

**Files:**
- Create: `agents/harness/integration.py`
- Create: `tests/test_harness_integration.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_harness_integration.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.harness.integration import attach_harness, TracingToolRegistry
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode
from agents.harness.core.tracer import HarnessTracer, TaskStatus
from agents.channels.robot_tools import RobotToolRegistry, ToolResult


def _make_real_registry():
    reg = RobotToolRegistry()
    async def _dummy(**kwargs):
        return ToolResult("test_tool", True, "ok")
    reg.register("test_tool", _dummy)
    return reg


def test_tracing_registry_records_calls():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    tracer = HarnessTracer(config)
    tracer.start_trace("t1", "s1")

    real_reg = _make_real_registry()
    tracing_reg = TracingToolRegistry(real_reg, tracer)

    asyncio.run(tracing_reg.call("test_tool", {}))
    trace = tracer.get_trace()
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "test_tool"


def test_tracing_registry_extracts_skill_id():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    tracer = HarnessTracer(config)
    tracer.start_trace("t1", "s1")

    real_reg = _make_real_registry()
    async def _start_policy(skill_id="", **kwargs):
        return ToolResult("start_policy", True, f"started {skill_id}")
    real_reg.register("start_policy", _start_policy)

    tracing_reg = TracingToolRegistry(real_reg, tracer)
    asyncio.run(tracing_reg.call("start_policy", {"skill_id": "manipulation.grasp"}))

    trace = tracer.get_trace()
    assert "manipulation.grasp" in trace.skill_calls


def test_attach_harness_returns_patched_loop():
    from agents.channels.agent_loop import RobotAgentLoop
    from agents.channels.bus import MessageBus
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)

    mock_provider = MagicMock()
    bus = MessageBus()
    loop = RobotAgentLoop(bus=bus, provider=mock_provider, robot_type="arm")

    patched_loop, tracer = attach_harness(loop, config)
    assert tracer is not None
    assert isinstance(patched_loop.tool_registry, TracingToolRegistry)
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_harness_integration.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 integration.py**

```python
# agents/harness/integration.py
"""attach_harness — zero-invasive interceptor for RobotAgentLoop.

Wraps the loop's ToolRegistry with a TracingToolRegistry that records
all tool calls to HarnessTracer without modifying RobotAgentLoop source code.
"""
from __future__ import annotations
import time
from typing import Any, TYPE_CHECKING

from agents.channels.robot_tools import RobotToolRegistry, ToolResult
from agents.harness.core.config import HarnessConfig
from agents.harness.core.tracer import HarnessTracer

if TYPE_CHECKING:
    from agents.channels.agent_loop import RobotAgentLoop


class TracingToolRegistry(RobotToolRegistry):
    """Wraps a real ToolRegistry and records all calls to HarnessTracer."""

    def __init__(self, wrapped: RobotToolRegistry, tracer: HarnessTracer):
        super().__init__()
        self._wrapped = wrapped
        self._tracer = tracer
        # Mirror the wrapped registry's tools
        self._tools = wrapped._tools  # type: ignore[attr-defined]

    async def call(self, name: str, args: dict[str, Any]) -> ToolResult:
        start = time.monotonic()
        result = await self._wrapped.call(name, args)
        duration_ms = int((time.monotonic() - start) * 1000)
        self._tracer.record_tool_call(
            name=name,
            args=args,
            result=result.content if result else "no result",
            duration_ms=duration_ms,
        )
        return result

    def has_tool(self, name: str) -> bool:
        return self._wrapped.has_tool(name)

    def list_tools(self) -> list[str]:
        return self._wrapped.list_tools()

    def register(self, name: str, fn: Any) -> None:
        self._wrapped.register(name, fn)


def attach_harness(
    loop: "RobotAgentLoop",
    config: HarnessConfig,
) -> tuple["RobotAgentLoop", HarnessTracer]:
    """Attach a HarnessTracer to a RobotAgentLoop without modifying its source.

    Replaces loop.tool_registry with a TracingToolRegistry that records
    all tool calls. Returns the patched loop and the tracer.

    Usage:
        loop, tracer = attach_harness(existing_loop, config)
        tracer.start_trace("task_001", "sess_001")
        # ... run loop ...
        trace = tracer.stop_trace()
    """
    tracer = HarnessTracer(config)
    loop.tool_registry = TracingToolRegistry(loop.tool_registry, tracer)
    return loop, tracer
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_harness_integration.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/integration.py tests/test_harness_integration.py
git commit -m "feat(harness): implement attach_harness interceptor via TracingToolRegistry"
```

---

## Phase 7: 端到端入口（补全 P3 缺口）

### Task 14: runner.py — HarnessRunner

**重要：** 原始计划没有把各组件串联起来的完整运行入口。`HarnessRunner` 实现：加载 TaskSet → 创建 HarnessEnv → 启动 Tracer → 运行模拟任务 → 评估 → 生成报告。

**Files:**
- Create: `agents/harness/runner.py`
- Create: `tests/test_harness_runner.py`

- [ ] **Step 1: 写 failing test**

```python
# tests/test_harness_runner.py
import pytest
from agents.harness.runner import HarnessRunner
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode
from agents.harness.core.task_set import Task, TaskSet


def _make_simple_task_set():
    ts = TaskSet()
    ts.declarative.append(Task(
        task_id="run_test_001",
        description="test run",
        robot_type="arm",
        expected_skills=["manipulation.grasp"],
    ))
    return ts


def test_runner_creates_with_config():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    assert runner.config.mode == HarnessMode.SKILL_MOCK


def test_runner_evaluate_returns_reports():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    ts = _make_simple_task_set()
    reports = runner.evaluate(ts)
    assert len(reports) == 1
    assert reports[0].task_id == "run_test_001"
    assert 0.0 <= reports[0].total_score <= 1.0


def test_runner_summary_str():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    ts = _make_simple_task_set()
    reports = runner.evaluate(ts)
    summary = runner.summary(reports)
    assert "run_test_001" in summary
    assert "PASS" in summary or "FAIL" in summary
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_harness_runner.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现 HarnessRunner**

```python
# agents/harness/runner.py
"""HarnessRunner — end-to-end evaluation pipeline.

Loads TaskSet → creates HarnessEnvironment → starts Tracer → simulates
task execution → evaluates with 4 dimensions → generates ScoreReport.
"""
from __future__ import annotations
import uuid
from agents.harness.core.config import HarnessConfig
from agents.harness.core.task_set import Task, TaskSet
from agents.harness.core.tracer import HarnessTracer, TaskStatus
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.core.scorer import HarnessScorer, ScoreReport
from agents.harness.core.evaluators.result_eval import ResultEvaluator
from agents.harness.core.evaluators.efficiency_eval import EfficiencyEvaluator
from agents.harness.core.evaluators.robustness_eval import RobustnessEvaluator
from agents.harness.core.evaluators.explainability_eval import ExplainabilityEvaluator


class HarnessRunner:
    """Orchestrates the full harness evaluation pipeline."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self._env = HarnessEnvironment.create(config)
        self._scorer = HarnessScorer(pass_threshold=config.pass_threshold)
        self._evaluators = [
            ResultEvaluator(),
            EfficiencyEvaluator(),
            RobustnessEvaluator(),
            ExplainabilityEvaluator(),
        ]

    def evaluate(self, task_set: TaskSet) -> list[ScoreReport]:
        """Run all tasks in the TaskSet and return a ScoreReport per task."""
        reports = []
        for task in task_set.all_tasks():
            report = self._run_task(task)
            reports.append(report)
        return reports

    def _run_task(self, task: Task) -> ScoreReport:
        tracer = HarnessTracer(self.config)
        session_id = str(uuid.uuid4())[:8]
        tracer.start_trace(task.task_id, session_id)

        # Simulate skill execution using MockSkillRegistry
        all_passed = True
        for skill_id in task.expected_skills:
            if self._env.skill_registry:
                result = self._env.skill_registry.call_skill(skill_id, {})
                # Record as if start_policy was called
                tracer.record_tool_call(
                    "start_policy", {"skill_id": skill_id},
                    result.content,
                )
                if not result.success:
                    all_passed = False
            else:
                # REAL mode: skills not simulated, just mark as called
                tracer.record_tool_call(
                    "start_policy", {"skill_id": skill_id}, "real mode"
                )

        status = TaskStatus.COMPLETED if all_passed else TaskStatus.FAILED
        trace = tracer.stop_trace(status=status)

        eval_scores = [ev.evaluate(trace, task) for ev in self._evaluators]
        return self._scorer.score(eval_scores, task_id=task.task_id)

    def summary(self, reports: list[ScoreReport]) -> str:
        lines = ["=" * 50, "Harness Evaluation Summary", "=" * 50]
        for r in reports:
            lines.append(r.summary())
            lines.append("-" * 30)
        passed = sum(1 for r in reports if r.passed)
        lines.append(f"Total: {passed}/{len(reports)} passed")
        return "\n".join(lines)
```

- [ ] **Step 4: 运行确认 PASS**

Run: `pytest tests/test_harness_runner.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/harness/runner.py tests/test_harness_runner.py
git commit -m "feat(harness): add HarnessRunner end-to-end evaluation pipeline"
```

---

## Phase 8: 公开 API + 综合验证

### Task 15: __init__.py + 全量测试

**Files:**
- Modify: `agents/harness/__init__.py`
- Create: `tests/test_harness_full.py`

- [ ] **Step 1: 写综合测试**

```python
# tests/test_harness_full.py
"""Full integration test: TaskLoader → HarnessRunner → ScoreReport."""
import pytest
from pathlib import Path
from agents.harness import HarnessRunner, HarnessConfig, TaskSet, Task
from agents.harness.core.mode import HarnessMode


def test_full_pipeline_skill_mock():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK,
                           skill_mock_config=None)  # use defaults
    config.skill_mock.default_success_rate = 1.0   # ensure all skills succeed

    ts = TaskSet()
    ts.declarative.append(Task(
        task_id="full_test_001",
        description="full pipeline test",
        robot_type="arm",
        expected_skills=["manipulation.reach", "manipulation.grasp"],
    ))

    runner = HarnessRunner(config)
    reports = runner.evaluate(ts)
    assert len(reports) == 1
    r = reports[0]
    assert r.task_id == "full_test_001"
    assert r.total_score > 0.0
    print("\n" + runner.summary(reports))


def test_full_pipeline_loads_yaml_tasks():
    from agents.harness.core.task_loader import TaskLoader
    tasks_dir = Path("agents/harness/tasks")
    if not tasks_dir.exists():
        pytest.skip("tasks dir not found")
    loader = TaskLoader()
    ts = loader.load_from_dir(tasks_dir)
    assert len(ts.declarative) >= 1

    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    config.skill_mock.default_success_rate = 0.9
    runner = HarnessRunner(config)
    reports = runner.evaluate(ts)
    assert len(reports) == len(ts.declarative)
    for r in reports:
        assert 0.0 <= r.total_score <= 1.0
```

- [ ] **Step 2: 运行确认 FAIL**

Run: `pytest tests/test_harness_full.py -v`
Expected: FAIL — ImportError (\_\_init\_\_.py not yet populated)

- [ ] **Step 3: 实现 \_\_init\_\_.py**

```python
# agents/harness/__init__.py
"""Agent Harness — Testing, Simulation, and Monitoring Framework.

Quick start:
    from agents.harness import HarnessRunner, HarnessConfig, TaskSet
    from agents.harness.core.mode import HarnessMode

    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    reports = runner.evaluate(task_set)
"""
from agents.harness.core.mode import HarnessMode
from agents.harness.core.config import HarnessConfig
from agents.harness.core.task_set import Task, TaskSet
from agents.harness.core.task_loader import TaskLoader
from agents.harness.core.tracer import HarnessTracer
from agents.harness.core.scorer import HarnessScorer, ScoreReport
from agents.harness.core.harness_env import HarnessEnvironment
from agents.harness.integration import attach_harness, TracingToolRegistry
from agents.harness.runner import HarnessRunner

__all__ = [
    "HarnessMode",
    "HarnessConfig",
    "Task",
    "TaskSet",
    "TaskLoader",
    "HarnessTracer",
    "HarnessScorer",
    "ScoreReport",
    "HarnessEnvironment",
    "attach_harness",
    "TracingToolRegistry",
    "HarnessRunner",
]
```

- [ ] **Step 4: 运行全量测试**

Run: `pytest tests/test_harness_full.py tests/test_harness_mode.py tests/test_harness_config.py tests/test_task_set.py tests/test_task_loader.py tests/test_tracer.py tests/test_scorer.py tests/test_mocks.py tests/test_harness_integration.py tests/test_harness_runner.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 确认不影响已有测试**

Run: `pytest tests/ -v --ignore=tests/test_harness_full.py -x -q 2>&1 | tail -20`
Expected: 已有测试无新增失败

- [ ] **Step 6: Final commit**

```bash
git add agents/harness/__init__.py tests/test_harness_full.py
git commit -m "feat(harness): complete harness framework with public API and full integration test"
```

---

## 自检清单

| 漏洞 | 修复位置 | 状态 |
|------|----------|------|
| P0: TaskSet 缺 @dataclass | Task 3 task_set.py | ✓ |
| P0: ArmAdapter 接口验证 | 预检证实接口存在，Task 12 直接继承 | ✓ |
| P1: attach_harness 无实现 | Task 13 integration.py | ✓ |
| P1: tool_name vs skill_id 命名空间 | Task 5 tracer.py + Task 8 result_eval.py | ✓ |
| P2: Mock 模式 Explainability 失效 | Task 10 explainability_eval.py | ✓ |
| P2: 回归任务 expected_skills=[] | Task 4 task_loader.py | ✓ |
| P3: 缺少端到端运行入口 | Task 14 runner.py | ✓ |
