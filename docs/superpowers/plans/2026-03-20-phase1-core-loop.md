:orphan:

# Phase 1: Universal Agent Core Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 core execution loop: voice-template input → gap-aware dual-format plan → failure data capture → training trigger, using existing AGX/LeRobot hardware clients.

**Architecture:** A new `agents/hardware/` package introduces `ArmAdapter` ABC and static `RobotCapabilityRegistry`; a `PlanGenerator` wraps `TaskPlanner` to emit dot-notation YAML execution plans; a `VoiceTemplateAgent` fills `SceneSpec` via Q&A; and `FailureDataRecorder` + `TrainingScriptGenerator` close the data-collection loop. All layers are decoupled by dataclass interfaces — no layer imports from a layer above it.

**Tech Stack:** Python 3.10+, dataclasses, PyYAML, pytest + pytest-asyncio, existing ollama/mock backend, existing AGX/LeRobot client stubs.

**Spec:** `docs/superpowers/specs/2026-03-20-universal-embodied-agent-design.md`

---

## File Map

| Status | Path | Responsibility |
|--------|------|---------------|
| Create | `agents/hardware/__init__.py` | Package init, re-exports |
| Create | `agents/hardware/arm_adapter.py` | `ArmAdapter` ABC + `Pose6D`, `RobotState`, `RobotCapabilities` dataclasses |
| Create | `agents/hardware/agx_arm_adapter.py` | AGX Arm wrapper implementing `ArmAdapter` |
| Create | `agents/hardware/lerobot_arm_adapter.py` | LeRobot wrapper implementing `ArmAdapter` |
| Create | `agents/hardware/capability_registry.py` | `GapType` enum, `CapabilityResult` dataclass, `RobotCapabilityRegistry` |
| Create | `agents/hardware/gap_detector.py` | `GapDetectionEngine` — classifies hard gaps |
| Create | `agents/hardware/skills_registry.yaml` | Default skill-registry YAML (shipped with code) |
| Create | `agents/components/scene_spec.py` | `SceneSpec` dataclass + YAML round-trip |
| Create | `agents/components/plan_generator.py` | `PlanGenerator` — wraps `TaskPlanner`, emits Markdown + YAML plan |
| Create | `agents/components/voice_template_agent.py` | `VoiceTemplateAgent` guided Q&A → `SceneSpec` |
| Modify | `agents/components/task_planner.py` | Add `_SKILL_NAMESPACE_MAP` for dot-notation, no other changes |
| Create | `agents/data/__init__.py` | Package init |
| Create | `agents/data/failure_recorder.py` | `FailureRecord` dataclass + `FailureDataRecorder` |
| Create | `agents/training/__init__.py` | Package init |
| Create | `agents/training/script_generator.py` | `TrainingConfig` dataclass + `TrainingScriptGenerator` |
| Create | `tests/test_arm_adapter.py` | Unit tests for ArmAdapter ABC + concrete stubs |
| Create | `tests/test_capability_registry.py` | Unit tests for registry load, query, list_gaps |
| Create | `tests/test_gap_detector.py` | Unit tests for hard-gap classification |
| Create | `tests/test_scene_spec.py` | YAML round-trip + validation tests |
| Create | `tests/test_plan_generator.py` | Dual-format output, gap annotation, SemanticMap integration |
| Create | `tests/test_voice_template_agent.py` | Sync Q&A fill, missing-field validation |
| Create | `tests/test_failure_recorder.py` | Record save, size enforcement, cleanup |
| Create | `tests/test_training_script_generator.py` | Config generation, bash script render |

---

## Task 1: ArmAdapter ABC + Data Structures

**Files:**
- Create: `agents/hardware/__init__.py`
- Create: `agents/hardware/arm_adapter.py`
- Create: `tests/test_arm_adapter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_arm_adapter.py
import pytest
from agents.hardware.arm_adapter import (
    Pose6D, RobotState, RobotCapabilities, ArmAdapter
)


class _DummyAdapter(ArmAdapter):
    async def move_to_pose(self, pose, speed=0.1):
        return True
    async def move_joints(self, angles, speed=0.1):
        return True
    async def set_gripper(self, opening, force=10.0):
        return True
    async def get_state(self):
        return RobotState(
            joint_angles=[0.0] * 6,
            end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
            gripper_opening=0.5,
            is_moving=False,
        )
    async def is_ready(self):
        return True
    async def emergency_stop(self):
        pass
    def get_capabilities(self):
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=["manipulation.grasp", "manipulation.place"],
        )


def test_pose6d_fields():
    p = Pose6D(1.0, 2.0, 3.0, 0.1, 0.2, 0.3)
    assert p.x == 1.0 and p.yaw == 0.3


def test_robot_state_fields():
    s = RobotState(
        joint_angles=[0.0] * 6,
        end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
        gripper_opening=0.5,
        is_moving=False,
    )
    assert s.error_code == 0


def test_capabilities_fields():
    cap = RobotCapabilities(robot_type="arm", supported_skills=["manipulation.grasp"])
    assert cap.max_payload_kg == 0.0


@pytest.mark.asyncio
async def test_dummy_adapter_is_ready():
    adapter = _DummyAdapter()
    assert await adapter.is_ready()


@pytest.mark.asyncio
async def test_dummy_adapter_get_capabilities():
    adapter = _DummyAdapter()
    cap = adapter.get_capabilities()
    assert "manipulation.grasp" in cap.supported_skills


def test_abstract_methods_enforced():
    """ArmAdapter cannot be instantiated without all abstract methods."""
    with pytest.raises(TypeError):
        ArmAdapter()  # type: ignore
```

- [ ] **Step 2: Run — expect ImportError (module not yet written)**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python -m pytest tests/test_arm_adapter.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'agents.hardware'`

- [ ] **Step 3: Create package + arm_adapter.py**

```python
# agents/hardware/__init__.py
from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities

__all__ = ["ArmAdapter", "Pose6D", "RobotState", "RobotCapabilities"]
```

```python
# agents/hardware/arm_adapter.py
"""ArmAdapter — 机械臂硬件抽象接口 (Phase 1)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class Pose6D:
    """6-DOF end-effector pose in Cartesian space (metres, radians)."""
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


@dataclass
class RobotState:
    """Snapshot of robot state at a single instant."""
    joint_angles: List[float]
    end_effector_pose: Pose6D
    gripper_opening: float   # 0.0 = closed, 1.0 = fully open
    is_moving: bool
    error_code: int = 0


@dataclass
class RobotCapabilities:
    """Static capabilities metadata reported by the adapter."""
    robot_type: str                          # "arm" | "mobile" | "mobile_arm"
    supported_skills: List[str]              # dot-notation skill IDs
    max_payload_kg: float = 0.0
    reach_m: float = 0.0


class ArmAdapter(ABC):
    """Abstract base class for all robotic arm hardware adapters."""

    @abstractmethod
    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        """Move end-effector to Pose6D. Returns True on success."""

    @abstractmethod
    async def move_joints(self, angles: List[float], speed: float = 0.1) -> bool:
        """Command joint angles (radians). Returns True on success."""

    @abstractmethod
    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        """Set gripper opening [0,1] with force limit (N). Returns True on success."""

    @abstractmethod
    async def get_state(self) -> RobotState:
        """Return current robot state snapshot."""

    @abstractmethod
    async def is_ready(self) -> bool:
        """Return True if the arm is powered, homed, and ready for commands."""

    @abstractmethod
    async def emergency_stop(self) -> None:
        """Immediately halt all motion."""

    @abstractmethod
    def get_capabilities(self) -> RobotCapabilities:
        """Return static capabilities metadata."""
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_arm_adapter.py -v
```
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add agents/hardware/__init__.py agents/hardware/arm_adapter.py tests/test_arm_adapter.py
git commit -m "feat(hardware): add ArmAdapter ABC with Pose6D, RobotState, RobotCapabilities"
```

---

## Task 2: AGX and LeRobot ArmAdapter Wrappers

**Files:**
- Create: `agents/hardware/agx_arm_adapter.py`
- Create: `agents/hardware/lerobot_arm_adapter.py`
- Modify: `agents/hardware/__init__.py`
- Modify: `tests/test_arm_adapter.py` (add wrapper tests)

- [ ] **Step 1: Add wrapper tests**

Append to `tests/test_arm_adapter.py`:

```python
# --- AGX Arm wrapper ---
from agents.hardware.agx_arm_adapter import AGXArmAdapter

def test_agx_adapter_capabilities():
    adapter = AGXArmAdapter(config={})
    cap = adapter.get_capabilities()
    assert cap.robot_type == "arm"
    assert "manipulation.grasp" in cap.supported_skills


@pytest.mark.asyncio
async def test_agx_adapter_is_ready_no_hardware():
    """Without real hardware, is_ready returns False (not raises)."""
    adapter = AGXArmAdapter(config={"mock": True})
    result = await adapter.is_ready()
    assert isinstance(result, bool)


# --- LeRobot wrapper ---
from agents.hardware.lerobot_arm_adapter import LeRobotArmAdapter

def test_lerobot_adapter_capabilities():
    adapter = LeRobotArmAdapter(config={})
    cap = adapter.get_capabilities()
    assert cap.robot_type == "arm"
    assert "manipulation.reach" in cap.supported_skills


@pytest.mark.asyncio
async def test_lerobot_adapter_is_ready_no_hardware():
    adapter = LeRobotArmAdapter(config={"mock": True})
    result = await adapter.is_ready()
    assert isinstance(result, bool)
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_arm_adapter.py::test_agx_adapter_capabilities -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write AGX wrapper**

```python
# agents/hardware/agx_arm_adapter.py
"""AGX Arm ArmAdapter wrapper — delegates to existing AGX client if available."""
import asyncio
import logging
from typing import Any, Dict, List

from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities

_LOG = logging.getLogger(__name__)

_AGX_SKILLS = [
    "manipulation.grasp",
    "manipulation.place",
    "manipulation.reach",
    "manipulation.inspect",
]


class AGXArmAdapter(ArmAdapter):
    """Wraps existing AGX arm skill clients under the ArmAdapter ABC.

    In mock mode (config['mock']=True or no hardware detected), all motion
    methods return True and get_state returns a zeroed RobotState.
    """

    def __init__(self, config: Dict[str, Any]):
        self._mock = config.get("mock", False)
        self._client = None
        if not self._mock:
            self._try_connect(config)

    def _try_connect(self, config: Dict[str, Any]) -> None:
        try:
            from agents.skills.manipulation.grasp import GraspSkill  # noqa: F401
            # Real client integration deferred to Phase 2
        except ImportError:
            _LOG.warning("AGX skills not available — falling back to mock mode")
            self._mock = True

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("AGX move_to_pose requires Phase 2 hardware bridge")

    async def move_joints(self, angles: List[float], speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("AGX move_joints requires Phase 2 hardware bridge")

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("AGX set_gripper requires Phase 2 hardware bridge")

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=[0.0] * 6,
            end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
            gripper_opening=0.5,
            is_moving=False,
        )

    async def is_ready(self) -> bool:
        return self._mock  # mock is always "ready"; real needs hardware

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=list(_AGX_SKILLS),
            max_payload_kg=2.0,
            reach_m=0.85,
        )
```

```python
# agents/hardware/lerobot_arm_adapter.py
"""LeRobot ArmAdapter wrapper — delegates to LeRobot client if available."""
import logging
from typing import Any, Dict, List

from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities

_LOG = logging.getLogger(__name__)

_LEROBOT_SKILLS = [
    "manipulation.grasp",
    "manipulation.place",
    "manipulation.reach",
]


class LeRobotArmAdapter(ArmAdapter):
    """Wraps LeRobot transport client under the ArmAdapter ABC.

    mock=True when no real LeRobot endpoint is configured.
    """

    def __init__(self, config: Dict[str, Any]):
        self._mock = config.get("mock", False)
        self._endpoint = config.get("endpoint", "")
        self._client = None
        if not self._mock and self._endpoint:
            self._try_connect()

    def _try_connect(self) -> None:
        try:
            from agents.clients.lerobot import LeRobotClient  # noqa: F401
        except ImportError:
            _LOG.warning("LeRobot client not available — mock mode")
            self._mock = True

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("LeRobot move_to_pose requires Phase 2 bridge")

    async def move_joints(self, angles: List[float], speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("LeRobot move_joints requires Phase 2 bridge")

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("LeRobot set_gripper requires Phase 2 bridge")

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=[0.0] * 6,
            end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
            gripper_opening=0.5,
            is_moving=False,
        )

    async def is_ready(self) -> bool:
        return self._mock

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=list(_LEROBOT_SKILLS),
            max_payload_kg=1.0,
            reach_m=0.65,
        )
```

- [ ] **Step 4: Update `agents/hardware/__init__.py`**

```python
# agents/hardware/__init__.py
from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities
from .agx_arm_adapter import AGXArmAdapter
from .lerobot_arm_adapter import LeRobotArmAdapter

__all__ = [
    "ArmAdapter", "Pose6D", "RobotState", "RobotCapabilities",
    "AGXArmAdapter", "LeRobotArmAdapter",
]
```

- [ ] **Step 5: Run all arm adapter tests — expect PASS**

```bash
python -m pytest tests/test_arm_adapter.py -v
```
Expected: `10 passed`

- [ ] **Step 6: Commit**

```bash
git add agents/hardware/agx_arm_adapter.py agents/hardware/lerobot_arm_adapter.py agents/hardware/__init__.py tests/test_arm_adapter.py
git commit -m "feat(hardware): add AGXArmAdapter and LeRobotArmAdapter mock wrappers"
```

---

## Task 3: RobotCapabilityRegistry

**Files:**
- Create: `agents/hardware/capability_registry.py`
- Create: `agents/hardware/skills_registry.yaml`
- Modify: `agents/hardware/__init__.py`
- Create: `tests/test_capability_registry.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_capability_registry.py
import pytest
import yaml
from pathlib import Path
from agents.hardware.capability_registry import (
    GapType, CapabilityResult, RobotCapabilityRegistry
)

REGISTRY_YAML = """
skills:
  - id: manipulation.grasp
    robot_types: [arm, mobile_arm]
    description: "Pick up an object"
  - id: manipulation.place
    robot_types: [arm, mobile_arm]
    description: "Place an object"
  - id: navigation.goto
    robot_types: [mobile, mobile_arm]
    description: "Navigate to a waypoint"
  - id: vision.detect
    robot_types: [arm, mobile, mobile_arm]
    description: "Detect objects in scene"
"""


@pytest.fixture
def registry_file(tmp_path):
    p = tmp_path / "skills.yaml"
    p.write_text(REGISTRY_YAML)
    return str(p)


@pytest.fixture
def registry(registry_file):
    return RobotCapabilityRegistry(registry_file)


def test_query_supported_skill(registry):
    result = registry.query("manipulation.grasp", "arm")
    assert result.gap_type == GapType.NONE


def test_query_wrong_robot_type(registry):
    # Phase 1 simplification: skills unsupported for a robot_type are classified
    # as HARD gaps (not ADAPTER), since Phase 1 does not distinguish "registered
    # but incompatible adapter" from "skill entirely missing". Phase 2 will add
    # ADAPTER classification once hardware adapters report per-skill support.
    result = registry.query("navigation.goto", "arm")
    assert result.gap_type == GapType.HARD
    assert "arm" in result.reason.lower() or "navigation" in result.reason.lower()


def test_query_unknown_skill(registry):
    result = registry.query("unknown.skill", "arm")
    assert result.gap_type == GapType.HARD


def test_list_gaps_with_gaps(registry):
    steps = [
        {"skill": "manipulation.grasp", "step_id": "1"},
        {"skill": "navigation.goto", "step_id": "2"},  # gap for "arm"
    ]
    gaps = registry.list_gaps(steps, "arm")
    assert len(gaps) == 1
    assert gaps[0].skill_id == "navigation.goto"
    assert gaps[0].gap_type == GapType.HARD


def test_list_gaps_no_gaps(registry):
    steps = [
        {"skill": "manipulation.grasp", "step_id": "1"},
        {"skill": "vision.detect", "step_id": "2"},
    ]
    gaps = registry.list_gaps(steps, "arm")
    assert gaps == []


def test_register_new_skill(registry):
    registry.register({
        "id": "force.push",
        "robot_types": ["arm"],
        "description": "Apply controlled force",
    })
    result = registry.query("force.push", "arm")
    assert result.gap_type == GapType.NONE


def test_gap_type_enum_values():
    assert GapType.HARD.value == "hard"
    assert GapType.NONE.value == "none"
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_capability_registry.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write registry YAML + Python**

```yaml
# agents/hardware/skills_registry.yaml
# Phase 1 static skill registry — extend in Phase 2 with performance metrics
skills:
  - id: manipulation.grasp
    robot_types: [arm, mobile_arm]
    description: "Pick up an object using the end-effector"
  - id: manipulation.place
    robot_types: [arm, mobile_arm]
    description: "Place a held object at a target location"
  - id: manipulation.reach
    robot_types: [arm, mobile_arm]
    description: "Move end-effector to a target pose without grasping"
  - id: manipulation.inspect
    robot_types: [arm, mobile, mobile_arm]
    description: "Visually inspect a target object or location"
  - id: navigation.goto
    robot_types: [mobile, mobile_arm]
    description: "Navigate mobile base to a waypoint"
  - id: navigation.dock
    robot_types: [mobile, mobile_arm]
    description: "Precisely dock at a station"
  - id: vision.detect
    robot_types: [arm, mobile, mobile_arm]
    description: "Detect and localize objects in the scene"
  - id: vision.segment
    robot_types: [arm, mobile, mobile_arm]
    description: "Segment objects using vision models"
  - id: force.push
    robot_types: [arm, mobile_arm]
    description: "Apply controlled force for assembly or insertion"
```

```python
# agents/hardware/capability_registry.py
"""RobotCapabilityRegistry — static YAML-backed skill registry (Phase 1)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import yaml


class GapType(Enum):
    NONE = "none"              # skill fully supported
    HARD = "hard"              # skill not registered for robot_type
    ADAPTER = "adapter"        # registered but no adapter implementation
    PERFORMANCE = "performance"  # adapter exists but below threshold


@dataclass
class CapabilityResult:
    skill_id: str
    robot_type: str
    gap_type: GapType
    reason: str = ""
    suggested_fallback: Optional[str] = None


class RobotCapabilityRegistry:
    """Loads a YAML skill registry and answers capability queries.

    YAML format::

        skills:
          - id: manipulation.grasp
            robot_types: [arm, mobile_arm]
            description: "..."
    """

    def __init__(self, registry_yaml_path: str):
        self._skills: Dict[str, List[str]] = {}  # skill_id → [robot_types]
        self._meta: Dict[str, dict] = {}
        self._load(registry_yaml_path)

    def _load(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for entry in data.get("skills", []):
            sid = entry["id"]
            self._skills[sid] = entry.get("robot_types", [])
            self._meta[sid] = entry

    def register(self, skill_meta: dict) -> None:
        """Dynamically register a new skill (or overwrite existing)."""
        sid = skill_meta["id"]
        self._skills[sid] = skill_meta.get("robot_types", [])
        self._meta[sid] = skill_meta

    def query(self, skill_id: str, robot_type: str) -> CapabilityResult:
        """Return CapabilityResult for (skill_id, robot_type) pair."""
        if skill_id not in self._skills:
            return CapabilityResult(
                skill_id=skill_id,
                robot_type=robot_type,
                gap_type=GapType.HARD,
                reason=f"Skill '{skill_id}' not found in registry",
            )
        supported_types = self._skills[skill_id]
        if robot_type not in supported_types:
            return CapabilityResult(
                skill_id=skill_id,
                robot_type=robot_type,
                gap_type=GapType.HARD,
                reason=(
                    f"Skill '{skill_id}' does not support robot_type='{robot_type}'. "
                    f"Supported: {supported_types}"
                ),
            )
        return CapabilityResult(
            skill_id=skill_id,
            robot_type=robot_type,
            gap_type=GapType.NONE,
        )

    def update_performance(self, skill_id: str, metrics: dict) -> None:
        """Placeholder for Phase 2 performance tracking — no-op in Phase 1."""
        if skill_id in self._meta:
            self._meta[skill_id].setdefault("performance", {}).update(metrics)

    def list_gaps(
        self, plan_steps: List[dict], robot_type: str
    ) -> List[CapabilityResult]:
        """Return CapabilityResults with gap_type != NONE for each plan step."""
        gaps = []
        for step in plan_steps:
            skill_id = step.get("skill", "")
            if not skill_id:
                continue
            result = self.query(skill_id, robot_type)
            if result.gap_type != GapType.NONE:
                gaps.append(result)
        return gaps
```

- [ ] **Step 4: Update `agents/hardware/__init__.py`**

```python
# agents/hardware/__init__.py
from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities
from .agx_arm_adapter import AGXArmAdapter
from .lerobot_arm_adapter import LeRobotArmAdapter
from .capability_registry import GapType, CapabilityResult, RobotCapabilityRegistry

__all__ = [
    "ArmAdapter", "Pose6D", "RobotState", "RobotCapabilities",
    "AGXArmAdapter", "LeRobotArmAdapter",
    "GapType", "CapabilityResult", "RobotCapabilityRegistry",
]
```

- [ ] **Step 5: Run registry tests — expect PASS**

```bash
python -m pytest tests/test_capability_registry.py -v
```
Expected: `8 passed`

- [ ] **Step 6: Commit**

```bash
git add agents/hardware/capability_registry.py agents/hardware/skills_registry.yaml agents/hardware/__init__.py tests/test_capability_registry.py
git commit -m "feat(hardware): add RobotCapabilityRegistry with YAML-backed skill registration"
```

---

## Task 4: Gap Detection Engine

**Files:**
- Create: `agents/hardware/gap_detector.py`
- Modify: `agents/hardware/__init__.py`
- Create: `tests/test_gap_detector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_gap_detector.py
import pytest
from agents.hardware.capability_registry import GapType, CapabilityResult
from agents.hardware.gap_detector import GapDetectionEngine, GapReport

STEPS_WITH_GAP = [
    {"step_id": "1", "skill": "manipulation.grasp", "params": {"target": "box"}},
    {"step_id": "2", "skill": "navigation.goto", "params": {"target": "shelf_A"}},
]

STEPS_NO_GAP = [
    {"step_id": "1", "skill": "manipulation.grasp", "params": {}},
    {"step_id": "2", "skill": "manipulation.place", "params": {}},
]


@pytest.fixture
def engine(tmp_path):
    registry_yaml = tmp_path / "skills.yaml"
    registry_yaml.write_text("""
skills:
  - id: manipulation.grasp
    robot_types: [arm]
  - id: manipulation.place
    robot_types: [arm]
  - id: navigation.goto
    robot_types: [mobile]
""")
    from agents.hardware.capability_registry import RobotCapabilityRegistry
    registry = RobotCapabilityRegistry(str(registry_yaml))
    return GapDetectionEngine(registry)


def test_detect_returns_gap_report(engine):
    report = engine.detect(STEPS_WITH_GAP, robot_type="arm")
    assert isinstance(report, GapReport)


def test_detect_finds_hard_gap(engine):
    report = engine.detect(STEPS_WITH_GAP, robot_type="arm")
    assert report.has_gaps
    assert len(report.hard_gaps) == 1
    assert report.hard_gaps[0].skill_id == "navigation.goto"


def test_detect_no_gap(engine):
    report = engine.detect(STEPS_NO_GAP, robot_type="arm")
    assert not report.has_gaps
    assert report.hard_gaps == []


def test_annotate_steps(engine):
    annotated = engine.annotate_steps(STEPS_WITH_GAP, robot_type="arm")
    step_map = {s["step_id"]: s for s in annotated}
    assert step_map["1"]["status"] == "pending"
    assert step_map["2"]["status"] == "gap"


def test_gap_report_summary(engine):
    report = engine.detect(STEPS_WITH_GAP, robot_type="arm")
    summary = report.summary()
    assert "navigation.goto" in summary
    assert "hard" in summary.lower()
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_gap_detector.py -v 2>&1 | head -10
```

- [ ] **Step 3: Write gap_detector.py**

```python
# agents/hardware/gap_detector.py
"""GapDetectionEngine — Phase 1 hard-gap-only classifier."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .capability_registry import GapType, CapabilityResult, RobotCapabilityRegistry


@dataclass
class GapReport:
    """Result of a gap detection pass over a plan's steps."""
    hard_gaps: List[CapabilityResult] = field(default_factory=list)
    adapter_gaps: List[CapabilityResult] = field(default_factory=list)
    performance_gaps: List[CapabilityResult] = field(default_factory=list)

    @property
    def has_gaps(self) -> bool:
        return bool(self.hard_gaps or self.adapter_gaps or self.performance_gaps)

    def summary(self) -> str:
        lines = []
        for gap in self.hard_gaps:
            lines.append(f"[hard] {gap.skill_id}: {gap.reason}")
        for gap in self.adapter_gaps:
            lines.append(f"[adapter] {gap.skill_id}: {gap.reason}")
        for gap in self.performance_gaps:
            lines.append(f"[performance] {gap.skill_id}: {gap.reason}")
        return "\n".join(lines) if lines else "No gaps detected."


class GapDetectionEngine:
    """Classifies plan steps as supported or gap, annotates with status field."""

    def __init__(self, registry: RobotCapabilityRegistry):
        self._registry = registry

    def detect(self, plan_steps: List[dict], robot_type: str) -> GapReport:
        """Run gap detection over all plan steps.

        Returns a GapReport bucketing gaps by type.
        """
        report = GapReport()
        for step in plan_steps:
            skill_id = step.get("skill", "")
            if not skill_id:
                continue
            result = self._registry.query(skill_id, robot_type)
            if result.gap_type == GapType.HARD:
                report.hard_gaps.append(result)
            elif result.gap_type == GapType.ADAPTER:
                report.adapter_gaps.append(result)
            elif result.gap_type == GapType.PERFORMANCE:
                report.performance_gaps.append(result)
        return report

    def annotate_steps(self, plan_steps: List[dict], robot_type: str) -> List[dict]:
        """Return a copy of plan_steps with 'status' set to 'gap' or 'pending'."""
        gap_skills = {
            r.skill_id
            for r in self._registry.list_gaps(plan_steps, robot_type)
        }
        annotated = []
        for step in plan_steps:
            s = dict(step)
            s["status"] = "gap" if s.get("skill", "") in gap_skills else "pending"
            annotated.append(s)
        return annotated
```

- [ ] **Step 4: Update `agents/hardware/__init__.py`**

Add to imports:
```python
from .gap_detector import GapDetectionEngine, GapReport
```
And add `"GapDetectionEngine", "GapReport"` to `__all__`.

- [ ] **Step 5: Run gap detector tests — expect PASS**

```bash
python -m pytest tests/test_gap_detector.py -v
```
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add agents/hardware/gap_detector.py agents/hardware/__init__.py tests/test_gap_detector.py
git commit -m "feat(hardware): add GapDetectionEngine for hard-gap classification and step annotation"
```

---

## Task 5: SceneSpec Dataclass

**Files:**
- Create: `agents/components/scene_spec.py`
- Create: `tests/test_scene_spec.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scene_spec.py
import pytest
from agents.components.scene_spec import SceneSpec

MINIMAL_DICT = {
    "scene_type": "warehouse_pick",
    "environment": "Large warehouse with shelving units",
    "robot_type": "arm",
    "task_description": "Pick red box from shelf A and place on conveyor",
}

FULL_DICT = {
    **MINIMAL_DICT,
    "objects": ["red_box", "shelf_A", "conveyor"],
    "constraints": ["avoid_fragile_area"],
    "success_criteria": ["box_on_conveyor"],
    "metadata": {"operator": "test"},
}


def test_from_dict_minimal():
    spec = SceneSpec.from_dict(MINIMAL_DICT)
    assert spec.scene_type == "warehouse_pick"
    assert spec.objects == []
    assert spec.constraints == []


def test_from_dict_full():
    spec = SceneSpec.from_dict(FULL_DICT)
    assert "red_box" in spec.objects
    assert spec.metadata["operator"] == "test"


def test_to_yaml_round_trip():
    spec = SceneSpec.from_dict(FULL_DICT)
    yaml_str = spec.to_yaml()
    spec2 = SceneSpec.from_yaml(yaml_str)
    assert spec2.scene_type == spec.scene_type
    assert spec2.objects == spec.objects
    assert spec2.constraints == spec.constraints


def test_missing_required_field_raises():
    bad = {k: v for k, v in MINIMAL_DICT.items() if k != "task_description"}
    with pytest.raises((KeyError, TypeError, ValueError)):
        SceneSpec.from_dict(bad)


def test_yaml_contains_scene_type():
    spec = SceneSpec.from_dict(MINIMAL_DICT)
    assert "warehouse_pick" in spec.to_yaml()


def test_robot_type_preserved():
    spec = SceneSpec.from_dict(MINIMAL_DICT)
    assert spec.robot_type == "arm"
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_scene_spec.py -v 2>&1 | head -10
```

- [ ] **Step 3: Write scene_spec.py**

```python
# agents/components/scene_spec.py
"""SceneSpec — structured task description filled via voice template or YAML."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml

_REQUIRED_FIELDS = ("scene_type", "environment", "robot_type", "task_description")


@dataclass
class SceneSpec:
    """Structured description of a scene and task, produced by VoiceTemplateAgent."""
    scene_type: str           # e.g. "warehouse_pick", "assembly", "inspection"
    environment: str          # free-text environment description
    robot_type: str           # "arm" | "mobile" | "mobile_arm"
    task_description: str     # natural language task goal
    objects: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        d = {
            "scene_type": self.scene_type,
            "environment": self.environment,
            "robot_type": self.robot_type,
            "task_description": self.task_description,
            "objects": self.objects,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "metadata": self.metadata,
        }
        return yaml.dump(d, allow_unicode=True, default_flow_style=False)

    @classmethod
    def from_yaml(cls, text: str) -> "SceneSpec":
        """Deserialize from YAML string."""
        d = yaml.safe_load(text)
        return cls.from_dict(d)

    @classmethod
    def from_dict(cls, d: dict) -> "SceneSpec":
        """Construct from a plain dict; raises KeyError on missing required fields."""
        for key in _REQUIRED_FIELDS:
            if key not in d:
                raise KeyError(f"SceneSpec missing required field: '{key}'")
        return cls(
            scene_type=d["scene_type"],
            environment=d["environment"],
            robot_type=d["robot_type"],
            task_description=d["task_description"],
            objects=list(d.get("objects") or []),
            constraints=list(d.get("constraints") or []),
            success_criteria=list(d.get("success_criteria") or []),
            metadata=dict(d.get("metadata") or {}),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_scene_spec.py -v
```
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add agents/components/scene_spec.py tests/test_scene_spec.py
git commit -m "feat(components): add SceneSpec dataclass with YAML round-trip"
```

---

## Task 6: PlanGenerator (dual-format output + gap annotation)

**Files:**
- Create: `agents/components/plan_generator.py`
- Modify: `agents/components/task_planner.py` (add `_SKILL_NAMESPACE_MAP` constant)
- Create: `tests/test_plan_generator.py`

**Context:** `TaskPlanner` uses flat vocab (`go_to`, `pick`, `place`, `inspect`). `PlanGenerator` wraps it and maps to dot-notation skills, then emits both Markdown report and YAML execution plan.

- [ ] **Step 1: Add namespace map to task_planner.py**

In `agents/components/task_planner.py`, add after the `_SYSTEM_PROMPT` string:

```python
# Canonical skill namespace mapping — flat action → dot-notation skill ID
_SKILL_NAMESPACE_MAP: dict = {
    "pick":    "manipulation.grasp",
    "place":   "manipulation.place",
    "go_to":   "navigation.goto",
    "inspect": "manipulation.inspect",
}
```

- [ ] **Step 2: Verify task_planner.py still passes its existing tests**

```bash
python -m pytest tests/test_task_planner.py -v
```
Expected: All existing tests pass.

- [ ] **Step 3: Write failing PlanGenerator tests**

```python
# tests/test_plan_generator.py
import pytest
import yaml
from agents.components.scene_spec import SceneSpec
from agents.components.plan_generator import PlanGenerator, ExecutionPlan

SCENE = SceneSpec(
    scene_type="warehouse_pick",
    environment="Warehouse with shelves",
    robot_type="arm",
    task_description="Pick red box from shelf A",
    objects=["red_box", "shelf_A"],
)


@pytest.fixture
def generator(tmp_path):
    registry_yaml = tmp_path / "skills.yaml"
    registry_yaml.write_text("""
skills:
  - id: manipulation.grasp
    robot_types: [arm]
  - id: manipulation.place
    robot_types: [arm]
  - id: manipulation.inspect
    robot_types: [arm]
  - id: navigation.goto
    robot_types: [mobile]
""")
    return PlanGenerator(registry_yaml_path=str(registry_yaml), backend="mock")


@pytest.mark.asyncio
async def test_generate_returns_execution_plan(generator):
    plan = await generator.generate(SCENE)
    assert isinstance(plan, ExecutionPlan)


@pytest.mark.asyncio
async def test_plan_has_steps(generator):
    plan = await generator.generate(SCENE)
    assert len(plan.steps) > 0


@pytest.mark.asyncio
async def test_steps_use_dot_notation(generator):
    plan = await generator.generate(SCENE)
    for step in plan.steps:
        assert "." in step["skill"], f"Expected dot-notation skill, got: {step['skill']}"


@pytest.mark.asyncio
async def test_yaml_output_valid(generator):
    plan = await generator.generate(SCENE)
    yaml_str = plan.to_yaml()
    parsed = yaml.safe_load(yaml_str)
    assert "plan_id" in parsed
    assert "steps" in parsed
    assert "status" in parsed


@pytest.mark.asyncio
async def test_markdown_output_contains_scene_type(generator):
    plan = await generator.generate(SCENE)
    md = plan.to_markdown()
    assert "warehouse_pick" in md


@pytest.mark.asyncio
async def test_gap_steps_annotated(generator):
    """navigation.goto is a gap for arm — steps injected manually to bypass mock planner."""
    from agents.hardware.capability_registry import RobotCapabilityRegistry
    from agents.hardware.gap_detector import GapDetectionEngine
    import os, tempfile, yaml

    registry_yaml = """
skills:
  - id: manipulation.grasp
    robot_types: [arm]
  - id: navigation.goto
    robot_types: [mobile]
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(registry_yaml)
        reg_path = f.name

    try:
        registry = RobotCapabilityRegistry(reg_path)
        engine = GapDetectionEngine(registry)
        steps = [
            {"step_id": "1", "skill": "manipulation.grasp", "params": {}},
            {"step_id": "2", "skill": "navigation.goto", "params": {}},
        ]
        annotated = engine.annotate_steps(steps, robot_type="arm")
        gap_skills = {s["skill"] for s in annotated if s.get("status") == "gap"}
        assert "navigation.goto" in gap_skills
        assert annotated[0]["status"] == "pending"
    finally:
        os.unlink(reg_path)


@pytest.mark.asyncio
async def test_capability_gaps_field_informational(generator):
    plan = await generator.generate(SCENE)
    yaml_str = plan.to_yaml()
    parsed = yaml.safe_load(yaml_str)
    assert "capability_gaps" in parsed
```

- [ ] **Step 4: Run — expect ImportError**

```bash
python -m pytest tests/test_plan_generator.py -v 2>&1 | head -10
```

- [ ] **Step 5: Write plan_generator.py**

```python
# agents/components/plan_generator.py
"""PlanGenerator — wraps TaskPlanner to emit dot-notation YAML + Markdown plans."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import yaml

from .scene_spec import SceneSpec
from .task_planner import TaskPlanner, _SKILL_NAMESPACE_MAP
from ..hardware.capability_registry import RobotCapabilityRegistry
from ..hardware.gap_detector import GapDetectionEngine


@dataclass
class ExecutionPlan:
    """Dual-format execution plan: YAML machine-readable + Markdown human-readable."""
    plan_id: str
    scene_spec: SceneSpec
    steps: List[dict]                        # annotated with status, skill (dot-notation)
    capability_gaps: List[str] = field(default_factory=list)  # informational
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_yaml(self) -> str:
        """Serialize to YAML execution plan string."""
        d = {
            "plan_id": self.plan_id,
            "scene_spec_ref": self.scene_spec.scene_type,
            "created_at": self.created_at,
            "status": self.status,
            "capability_gaps": self.capability_gaps,
            "steps": self.steps,
        }
        return yaml.dump(d, allow_unicode=True, default_flow_style=False)

    def to_markdown(self) -> str:
        """Render human-readable Markdown technical report."""
        lines = [
            f"# 技术方案报告",
            f"",
            f"**Plan ID:** `{self.plan_id}`  ",
            f"**创建时间:** {self.created_at}  ",
            f"**场景类型:** {self.scene_spec.scene_type}  ",
            f"**机器人类型:** {self.scene_spec.robot_type}  ",
            f"**任务描述:** {self.scene_spec.task_description}",
            f"",
            f"## 执行步骤",
            f"",
        ]
        for i, step in enumerate(self.steps, 1):
            status_badge = "⚠️ GAP" if step.get("status") == "gap" else "✅"
            params_str = ", ".join(
                f"{k}={v}" for k, v in (step.get("params") or {}).items()
            )
            lines.append(
                f"{i}. {status_badge} **{step['skill']}**"
                + (f" ({params_str})" if params_str else "")
            )
        if self.capability_gaps:
            lines += ["", "## 能力缺口 (Capability Gaps)", ""]
            for gap in self.capability_gaps:
                lines.append(f"- ⚠️ {gap}")
        return "\n".join(lines)


class PlanGenerator:
    """Generates dual-format execution plans from a SceneSpec.

    Internally uses TaskPlanner (mock or ollama) and maps flat actions
    to dot-notation skill IDs via _SKILL_NAMESPACE_MAP.
    """

    def __init__(
        self,
        registry_yaml_path: str,
        ollama_model: str = "qwen2.5:3b",
        backend: str = "ollama",
    ):
        self._planner = TaskPlanner(ollama_model=ollama_model, backend=backend)
        self._registry = RobotCapabilityRegistry(registry_yaml_path)
        self._gap_engine = GapDetectionEngine(self._registry)

    async def generate(self, scene: SceneSpec) -> ExecutionPlan:
        """Generate an ExecutionPlan for the given SceneSpec."""
        task_plan = await self._planner.plan(scene.task_description)

        # Convert flat actions → dot-notation steps
        raw_steps = []
        for action in task_plan.actions:
            skill_id = _SKILL_NAMESPACE_MAP.get(action.action, action.action)
            raw_steps.append({
                "step_id": str(len(raw_steps) + 1),
                "skill": skill_id,
                "params": {
                    "target": action.target,
                    **({"location": action.location} if action.location else {}),
                },
            })

        # Annotate steps with gap status
        annotated = self._gap_engine.annotate_steps(raw_steps, scene.robot_type)

        # Build capability_gaps list (informational)
        gap_report = self._gap_engine.detect(raw_steps, scene.robot_type)
        cap_gaps = [
            f"{g.skill_id}: {g.reason}" for g in gap_report.hard_gaps
        ]

        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            scene_spec=scene,
            steps=annotated,
            capability_gaps=cap_gaps,
        )
```

- [ ] **Step 6: Run PlanGenerator tests — expect PASS**

```bash
python -m pytest tests/test_plan_generator.py -v
```
Expected: `7 passed`

- [ ] **Step 7: Commit**

```bash
git add agents/components/plan_generator.py agents/components/task_planner.py tests/test_plan_generator.py
git commit -m "feat(components): add PlanGenerator with dual-format YAML+Markdown output and gap annotation"
```

---

## Task 7: VoiceTemplateAgent

**Files:**
- Create: `agents/components/voice_template_agent.py`
- Create: `tests/test_voice_template_agent.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_voice_template_agent.py
import pytest
from agents.components.voice_template_agent import VoiceTemplateAgent
from agents.components.scene_spec import SceneSpec

ANSWERS = {
    "scene_type": "warehouse_pick",
    "environment": "Large warehouse with metal shelves",
    "robot_type": "arm",
    "task_description": "Pick red box from shelf A and place on conveyor",
    "objects": "red_box, shelf_A, conveyor",
    "constraints": "avoid_fragile_zone",
    "success_criteria": "box_on_conveyor",
}


@pytest.fixture
def agent():
    return VoiceTemplateAgent()


@pytest.mark.asyncio
async def test_fill_from_answers_returns_scene_spec(agent):
    spec = await agent.fill_from_answers(ANSWERS)
    assert isinstance(spec, SceneSpec)


@pytest.mark.asyncio
async def test_scene_type_preserved(agent):
    spec = await agent.fill_from_answers(ANSWERS)
    assert spec.scene_type == "warehouse_pick"


@pytest.mark.asyncio
async def test_objects_parsed_from_comma_string(agent):
    spec = await agent.fill_from_answers(ANSWERS)
    assert "red_box" in spec.objects
    assert "conveyor" in spec.objects


@pytest.mark.asyncio
async def test_missing_required_answer_raises(agent):
    bad = {k: v for k, v in ANSWERS.items() if k != "task_description"}
    with pytest.raises((KeyError, ValueError)):
        await agent.fill_from_answers(bad)


def test_questions_list_complete(agent):
    """All required SceneSpec fields have a corresponding question."""
    required = {"scene_type", "environment", "robot_type", "task_description"}
    question_keys = {q[0] for q in agent.QUESTIONS}
    assert required.issubset(question_keys)


@pytest.mark.asyncio
async def test_interactive_fill_uses_input_fn(agent):
    """interactive_fill calls input_fn for each question and returns a SceneSpec."""
    answer_map = dict(ANSWERS)
    call_count = [0]

    async def mock_input(prompt: str) -> str:
        call_count[0] += 1
        for key, val in answer_map.items():
            if key in prompt.lower():
                return val
        return "default"

    outputs = []
    async def mock_output(text: str) -> None:
        outputs.append(text)

    spec = await agent.interactive_fill(mock_input, mock_output)
    assert isinstance(spec, SceneSpec)
    assert call_count[0] >= 4
    assert len(outputs) >= 4  # output_fn called at least once per required question
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_voice_template_agent.py -v 2>&1 | head -10
```

- [ ] **Step 3: Write voice_template_agent.py**

```python
# agents/components/voice_template_agent.py
"""VoiceTemplateAgent — guides user through Q&A to fill a SceneSpec."""
from __future__ import annotations

from typing import Any, Callable, Coroutine, Dict, List, Tuple

from .scene_spec import SceneSpec

# Each tuple: (field_name, question_text, is_list_field)
_QUESTIONS: List[Tuple[str, str, bool]] = [
    ("scene_type",       "场景类型？(warehouse_pick / assembly / inspection / other)", False),
    ("environment",      "描述当前环境（货架、机器人位置、空间大小等）：", False),
    ("robot_type",       "机器人类型？(arm / mobile / mobile_arm)", False),
    ("task_description", "用一句话描述任务目标：", False),
    ("objects",          "涉及的对象有哪些？（逗号分隔，如: red_box, shelf_A）", True),
    ("constraints",      "有哪些约束条件？（逗号分隔，或直接回车跳过）", True),
    ("success_criteria", "成功标准是什么？（逗号分隔，或直接回车跳过）", True),
]

_REQUIRED = {"scene_type", "environment", "robot_type", "task_description"}


def _parse_list(text: str) -> List[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


class VoiceTemplateAgent:
    """Fills a SceneSpec via guided Q&A, either programmatically or interactively."""

    QUESTIONS = _QUESTIONS

    async def fill_from_answers(self, answers: Dict[str, Any]) -> SceneSpec:
        """Build SceneSpec from a pre-filled answer dict.

        For list fields, values may be comma-separated strings or lists.
        Raises KeyError if any required field is missing.
        """
        for field in _REQUIRED:
            if field not in answers or not answers[field]:
                raise KeyError(f"Required field missing: '{field}'")

        def _to_list(val: Any) -> List[str]:
            if isinstance(val, list):
                return val
            return _parse_list(str(val)) if val else []

        return SceneSpec(
            scene_type=str(answers["scene_type"]).strip(),
            environment=str(answers["environment"]).strip(),
            robot_type=str(answers["robot_type"]).strip(),
            task_description=str(answers["task_description"]).strip(),
            objects=_to_list(answers.get("objects", [])),
            constraints=_to_list(answers.get("constraints", [])),
            success_criteria=_to_list(answers.get("success_criteria", [])),
        )

    async def interactive_fill(
        self,
        input_fn: Callable[[str], Coroutine[Any, Any, str]],
        output_fn: Callable[[str], Coroutine[Any, Any, None]],
    ) -> SceneSpec:
        """Interactively fill SceneSpec by calling input_fn for each question.

        Args:
            input_fn: async callable(prompt) → str
            output_fn: async callable(text) → None (for displaying prompts)
        """
        answers: Dict[str, Any] = {}
        for field_name, question, is_list in _QUESTIONS:
            await output_fn(f"\n❓ {question}")
            response = await input_fn(question)
            answers[field_name] = response
        return await self.fill_from_answers(answers)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_voice_template_agent.py -v
```
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add agents/components/voice_template_agent.py tests/test_voice_template_agent.py
git commit -m "feat(components): add VoiceTemplateAgent for guided SceneSpec Q&A filling"
```

---

## Task 8: FailureDataRecorder

**Files:**
- Create: `agents/data/__init__.py`
- Create: `agents/data/failure_recorder.py`
- Create: `tests/test_failure_recorder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_failure_recorder.py
import pytest
import json
from pathlib import Path
from agents.data.failure_recorder import FailureDataRecorder, FailureRecord
from agents.components.scene_spec import SceneSpec

SCENE = SceneSpec(
    scene_type="warehouse_pick",
    environment="Warehouse",
    robot_type="arm",
    task_description="Pick red box",
)

PLAN_YAML = "plan_id: test-123\nstatus: failed\nsteps: []"


@pytest.fixture
def recorder(tmp_path):
    return FailureDataRecorder(base_dir=str(tmp_path / "failures"), max_size_gb=1.0)


@pytest.mark.asyncio
async def test_record_creates_directory(recorder, tmp_path):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="2",
        error_type="hard_gap",
    )
    path = await recorder.record(record)
    assert Path(path).exists()


@pytest.mark.asyncio
async def test_record_saves_metadata_json(recorder, tmp_path):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="2",
        error_type="hard_gap",
        notes="Test failure",
    )
    path = await recorder.record(record)
    meta_file = Path(path) / "metadata.json"
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text())
    assert meta["error_type"] == "hard_gap"
    assert meta["failed_step_id"] == "2"


@pytest.mark.asyncio
async def test_record_saves_plan_yaml(recorder):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="1",
        error_type="execution_error",
    )
    path = await recorder.record(record)
    plan_file = Path(path) / "plan.yaml"
    assert plan_file.exists()
    assert "test-123" in plan_file.read_text()


@pytest.mark.asyncio
async def test_record_saves_scene_spec_yaml(recorder):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="1",
        error_type="execution_error",
    )
    path = await recorder.record(record)
    spec_file = Path(path) / "scene_spec.yaml"
    assert spec_file.exists()
    assert "warehouse_pick" in spec_file.read_text()


def test_list_records_empty(recorder):
    records = recorder.list_records()
    assert records == []


@pytest.mark.asyncio
async def test_list_records_after_record(recorder):
    record = FailureRecord(
        scene_spec=SCENE,
        plan_yaml=PLAN_YAML,
        failed_step_id="1",
        error_type="hard_gap",
    )
    await recorder.record(record)
    records = recorder.list_records()
    assert len(records) == 1
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_failure_recorder.py -v 2>&1 | head -10
```

- [ ] **Step 3: Write failure_recorder.py**

```python
# agents/data/__init__.py
from .failure_recorder import FailureDataRecorder, FailureRecord

__all__ = ["FailureDataRecorder", "FailureRecord"]
```

```python
# agents/data/failure_recorder.py
"""FailureDataRecorder — saves execution failure data for training pipeline."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import uuid

from ..components.scene_spec import SceneSpec


@dataclass
class FailureRecord:
    """All data captured at the moment of a skill execution failure."""
    scene_spec: SceneSpec
    plan_yaml: str
    failed_step_id: str
    error_type: str           # "hard_gap" | "execution_error" | "timeout"
    notes: str = ""
    failure_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # Optional raw data — not required in Phase 1
    rgb_frame_paths: List[str] = field(default_factory=list)
    state_log: List[dict] = field(default_factory=list)


class FailureDataRecorder:
    """Persists FailureRecord objects to disk under base_dir/<failure_id>/.

    Phase 1 saves: metadata.json, scene_spec.yaml, plan.yaml
    Phase 2 will add: rgb_frames/, state_log.jsonl
    """

    def __init__(self, base_dir: str, max_size_gb: float = 50.0):
        self._base = Path(base_dir)
        self._max_bytes = int(max_size_gb * 1024 ** 3)
        self._base.mkdir(parents=True, exist_ok=True)

    async def record(self, record: FailureRecord) -> str:
        """Save failure record to disk. Returns the directory path."""
        record_dir = self._base / record.failure_id
        record_dir.mkdir(parents=True, exist_ok=True)

        # metadata.json
        meta = {
            "failure_id": record.failure_id,
            "timestamp": record.timestamp,
            "failed_step_id": record.failed_step_id,
            "error_type": record.error_type,
            "notes": record.notes,
        }
        (record_dir / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)
        )

        # scene_spec.yaml
        (record_dir / "scene_spec.yaml").write_text(record.scene_spec.to_yaml())

        # plan.yaml
        (record_dir / "plan.yaml").write_text(record.plan_yaml)

        return str(record_dir)

    def list_records(self) -> List[str]:
        """Return sorted list of all recorded failure directory paths."""
        if not self._base.exists():
            return []
        return sorted(
            str(p) for p in self._base.iterdir() if p.is_dir()
        )

    def cleanup_old(self, keep_count: int = 1000) -> int:
        """Remove oldest records when count exceeds keep_count. Returns number deleted."""
        records = self.list_records()
        to_delete = records[:-keep_count] if len(records) > keep_count else []
        for path in to_delete:
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        return len(to_delete)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_failure_recorder.py -v
```
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add agents/data/__init__.py agents/data/failure_recorder.py tests/test_failure_recorder.py
git commit -m "feat(data): add FailureDataRecorder saving metadata, scene_spec, plan on failure"
```

---

## Task 9: TrainingScriptGenerator

**Files:**
- Create: `agents/training/__init__.py`
- Create: `agents/training/script_generator.py`
- Create: `tests/test_training_script_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_training_script_generator.py
import pytest
from agents.hardware.capability_registry import GapType, CapabilityResult
from agents.training.script_generator import TrainingScriptGenerator, TrainingConfig

GAP = CapabilityResult(
    skill_id="manipulation.grasp",
    robot_type="arm",
    gap_type=GapType.HARD,
    reason="Skill not found in registry",
)


@pytest.fixture
def generator():
    return TrainingScriptGenerator()


def test_generate_training_config(generator):
    config = generator.generate_training_config(GAP, dataset_path="/data/grasp")
    assert isinstance(config, TrainingConfig)
    assert config.skill_id == "manipulation.grasp"
    assert config.dataset_path == "/data/grasp"


def test_training_config_defaults(generator):
    config = generator.generate_training_config(GAP, dataset_path="/data/grasp")
    assert config.epochs > 0
    assert config.batch_size > 0
    assert config.model_type in ("act", "gr00t", "lerobot")


def test_render_bash_script_contains_skill(generator):
    config = generator.generate_training_config(GAP, dataset_path="/data/grasp")
    script = generator.render_bash_script(config)
    assert "manipulation.grasp" in script
    assert "#!/bin/bash" in script


def test_render_bash_script_contains_dataset_path(generator):
    config = generator.generate_training_config(GAP, dataset_path="/data/grasp_001")
    script = generator.render_bash_script(config)
    assert "/data/grasp_001" in script


def test_generate_dataset_requirements(generator):
    reqs = generator.generate_dataset_requirements([GAP])
    assert "manipulation.grasp" in reqs
    assert "min_episodes" in reqs["manipulation.grasp"]


def test_render_markdown_report(generator):
    report = generator.render_markdown_report([GAP])
    assert "manipulation.grasp" in report
    assert "#" in report  # has headings
```

- [ ] **Step 2: Run — expect ImportError**

```bash
python -m pytest tests/test_training_script_generator.py -v 2>&1 | head -10
```

- [ ] **Step 3: Write script_generator.py**

```python
# agents/training/__init__.py
from .script_generator import TrainingScriptGenerator, TrainingConfig

__all__ = ["TrainingScriptGenerator", "TrainingConfig"]
```

```python
# agents/training/script_generator.py
"""TrainingScriptGenerator — generates dataset requirements and training configs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..hardware.capability_registry import CapabilityResult

# Default training parameters by skill domain
_SKILL_CONFIGS: Dict[str, dict] = {
    "manipulation": {"model_type": "act",   "epochs": 100, "batch_size": 16},
    "navigation":   {"model_type": "lerobot", "epochs": 50,  "batch_size": 32},
    "vision":       {"model_type": "gr00t",  "epochs": 30,  "batch_size": 8},
    "force":        {"model_type": "act",   "epochs": 80,  "batch_size": 16},
    "default":      {"model_type": "act",   "epochs": 100, "batch_size": 16},
}

_MIN_EPISODES: Dict[str, int] = {
    "manipulation": 200,
    "navigation":   100,
    "vision":       150,
    "force":        300,
    "default":      200,
}


@dataclass
class TrainingConfig:
    """Training job configuration for a single skill gap."""
    skill_id: str
    dataset_path: str
    model_type: str         # "act" | "gr00t" | "lerobot"
    epochs: int
    batch_size: int
    output_dir: str = ""


class TrainingScriptGenerator:
    """Generates training configs, bash scripts, and gap reports for engineers."""

    def generate_training_config(
        self, gap: CapabilityResult, dataset_path: str
    ) -> TrainingConfig:
        """Return a TrainingConfig for the given gap and dataset path."""
        domain = gap.skill_id.split(".")[0] if "." in gap.skill_id else "default"
        cfg = _SKILL_CONFIGS.get(domain, _SKILL_CONFIGS["default"])
        return TrainingConfig(
            skill_id=gap.skill_id,
            dataset_path=dataset_path,
            model_type=cfg["model_type"],
            epochs=cfg["epochs"],
            batch_size=cfg["batch_size"],
            output_dir=f"models/{gap.skill_id.replace('.', '_')}",
        )

    def generate_dataset_requirements(
        self, gaps: List[CapabilityResult]
    ) -> Dict[str, dict]:
        """Return per-gap dataset collection requirements dict.

        Format::

            { "manipulation.grasp": { "min_episodes": 200, "data_types": [...] } }
        """
        requirements: Dict[str, dict] = {}
        for gap in gaps:
            domain = gap.skill_id.split(".")[0] if "." in gap.skill_id else "default"
            requirements[gap.skill_id] = {
                "min_episodes": _MIN_EPISODES.get(domain, 200),
                "data_types": ["rgb_frames", "joint_states", "gripper_state"],
                "robot_type": gap.robot_type,
                "gap_reason": gap.reason,
            }
        return requirements

    def render_bash_script(self, config: TrainingConfig) -> str:
        """Render a runnable bash training script for the given config."""
        return f"""#!/bin/bash
# Auto-generated training script for skill: {config.skill_id}
# Model: {config.model_type}, Epochs: {config.epochs}, Batch: {config.batch_size}
set -euo pipefail

SKILL_ID="{config.skill_id}"
DATASET_PATH="{config.dataset_path}"
OUTPUT_DIR="{config.output_dir}"
MODEL_TYPE="{config.model_type}"
EPOCHS={config.epochs}
BATCH_SIZE={config.batch_size}

echo "Training $SKILL_ID using $MODEL_TYPE model"
echo "Dataset: $DATASET_PATH"
echo "Output:  $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

python -m agents.training.run_training \\
    --skill "$SKILL_ID" \\
    --model "$MODEL_TYPE" \\
    --dataset "$DATASET_PATH" \\
    --output "$OUTPUT_DIR" \\
    --epochs "$EPOCHS" \\
    --batch-size "$BATCH_SIZE"

echo "Training complete. Model saved to $OUTPUT_DIR"
"""

    def render_markdown_report(self, gaps: List[CapabilityResult]) -> str:
        """Render a Markdown report listing all gaps and required training actions."""
        lines = [
            "# 能力缺口训练报告",
            "",
            f"共检测到 **{len(gaps)}** 个能力缺口，需要收集数据并训练。",
            "",
        ]
        reqs = self.generate_dataset_requirements(gaps)
        for gap in gaps:
            req = reqs[gap.skill_id]
            lines += [
                f"## {gap.skill_id}",
                "",
                f"- **缺口类型:** {gap.gap_type.value}",
                f"- **机器人类型:** {gap.robot_type}",
                f"- **原因:** {gap.reason}",
                f"- **最少采集 episodes:** {req['min_episodes']}",
                f"- **需要数据类型:** {', '.join(req['data_types'])}",
                "",
            ]
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
python -m pytest tests/test_training_script_generator.py -v
```
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add agents/training/__init__.py agents/training/script_generator.py tests/test_training_script_generator.py
git commit -m "feat(training): add TrainingScriptGenerator for dataset requirements and bash scripts"
```

---

## Task 10: Full Integration Smoke Test

**Files:**
- Create: `tests/test_phase1_integration.py`

This test wires all 7 components together: SceneSpec → PlanGenerator → GapDetector → FailureDataRecorder → TrainingScriptGenerator.

- [ ] **Step 1: Write integration test**

```python
# tests/test_phase1_integration.py
"""Phase 1 integration smoke test — wires all components end-to-end."""
import pytest
import yaml
from pathlib import Path

from agents.components.scene_spec import SceneSpec
from agents.components.voice_template_agent import VoiceTemplateAgent
from agents.components.plan_generator import PlanGenerator
from agents.data.failure_recorder import FailureDataRecorder, FailureRecord
from agents.training.script_generator import TrainingScriptGenerator
from agents.hardware.capability_registry import RobotCapabilityRegistry
from agents.hardware.gap_detector import GapDetectionEngine

REGISTRY_YAML_CONTENT = """
skills:
  - id: manipulation.grasp
    robot_types: [arm]
  - id: manipulation.place
    robot_types: [arm]
  - id: manipulation.inspect
    robot_types: [arm]
  - id: navigation.goto
    robot_types: [mobile]
"""

ANSWERS = {
    "scene_type": "warehouse_pick",
    "environment": "Warehouse with metal shelves",
    "robot_type": "arm",
    "task_description": "Pick red box and inspect it",
    "objects": "red_box",
    "constraints": "",
    "success_criteria": "box_inspected",
}


@pytest.fixture
def registry_file(tmp_path):
    p = tmp_path / "skills.yaml"
    p.write_text(REGISTRY_YAML_CONTENT)
    return str(p)


@pytest.mark.asyncio
async def test_voice_to_plan(registry_file):
    """VoiceTemplateAgent → PlanGenerator produces valid ExecutionPlan."""
    agent = VoiceTemplateAgent()
    spec = await agent.fill_from_answers(ANSWERS)

    gen = PlanGenerator(registry_yaml_path=registry_file, backend="mock")
    plan = await gen.generate(spec)

    assert len(plan.steps) > 0
    yaml_str = plan.to_yaml()
    parsed = yaml.safe_load(yaml_str)
    assert "plan_id" in parsed
    assert "steps" in parsed


@pytest.mark.asyncio
async def test_gap_detection_triggers_training_report(registry_file):
    """When arm has navigation gap, TrainingScriptGenerator produces a report.

    Note: mock planner never emits navigation.goto, so we build steps manually
    to test the gap → training-report pipeline independently of the planner.
    """
    # Manually construct steps that include navigation.goto (a hard gap for arm)
    steps_with_nav_gap = [
        {"step_id": "1", "skill": "manipulation.grasp", "params": {"target": "box"}},
        {"step_id": "2", "skill": "navigation.goto", "params": {"target": "shelf_A"}},
    ]

    tsg = TrainingScriptGenerator()
    registry = RobotCapabilityRegistry(registry_file)
    gap_engine = GapDetectionEngine(registry)
    gap_report = gap_engine.detect(steps_with_nav_gap, "arm")

    assert gap_report.has_gaps
    assert any(g.skill_id == "navigation.goto" for g in gap_report.hard_gaps)

    report_md = tsg.render_markdown_report(gap_report.hard_gaps)
    assert "navigation.goto" in report_md


@pytest.mark.asyncio
async def test_failure_recorded_and_training_script_generated(registry_file, tmp_path):
    """FailureDataRecorder saves record; TrainingScriptGenerator renders script."""
    spec = SceneSpec(
        scene_type="warehouse_pick",
        environment="Warehouse",
        robot_type="arm",
        task_description="Pick red box",
    )
    gen = PlanGenerator(registry_yaml_path=registry_file, backend="mock")
    plan = await gen.generate(spec)

    # Simulate failure
    recorder = FailureDataRecorder(base_dir=str(tmp_path / "failures"))
    failure = FailureRecord(
        scene_spec=spec,
        plan_yaml=plan.to_yaml(),
        failed_step_id="1",
        error_type="hard_gap",
    )
    path = await recorder.record(failure)
    assert Path(path).exists()

    # Generate training config using a known hard gap (navigation.goto for arm)
    from agents.hardware.capability_registry import RobotCapabilityRegistry, GapType, CapabilityResult
    synthetic_gap = CapabilityResult(
        skill_id="navigation.goto",
        robot_type="arm",
        gap_type=GapType.HARD,
        reason="navigation.goto not supported for arm",
    )
    tsg = TrainingScriptGenerator()
    config = tsg.generate_training_config(synthetic_gap, dataset_path=path)
    script = tsg.render_bash_script(config)
    assert "#!/bin/bash" in script
    assert "navigation.goto" in script


@pytest.mark.asyncio
async def test_arm_adapter_capabilities_match_registry(registry_file):
    """AGXArmAdapter capabilities intersect with skills registered for 'arm'."""
    from agents.hardware.agx_arm_adapter import AGXArmAdapter
    from agents.hardware.capability_registry import RobotCapabilityRegistry

    adapter = AGXArmAdapter(config={"mock": True})
    cap = adapter.get_capabilities()
    assert cap.robot_type == "arm"

    registry = RobotCapabilityRegistry(registry_file)
    # At least one skill from the adapter must be registered for "arm"
    registered_arm_skills = {
        sid for sid, types in registry._skills.items() if "arm" in types
    }
    adapter_skills = set(cap.supported_skills)
    assert adapter_skills & registered_arm_skills, (
        f"No overlap between adapter skills {adapter_skills} "
        f"and registry arm skills {registered_arm_skills}"
    )
```

- [ ] **Step 2: Run integration tests — expect PASS**

```bash
python -m pytest tests/test_phase1_integration.py -v
```
Expected: `4 passed`

- [ ] **Step 3: Run full test suite — no regressions**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All previously passing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_phase1_integration.py
git commit -m "test: add Phase 1 end-to-end integration smoke test"
```

---

## Task 11: Final Wiring — Update Package Inits

**Files:**
- Check `agents/components/__init__.py` — add new exports if needed

- [ ] **Step 1: Read current components __init__.py**

```bash
head -30 agents/components/__init__.py
```

- [ ] **Step 2: Add new exports**

Add to `agents/components/__init__.py`:
```python
from .scene_spec import SceneSpec
from .plan_generator import PlanGenerator, ExecutionPlan
from .voice_template_agent import VoiceTemplateAgent
```

- [ ] **Step 3: Run full suite one final time**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -10
```
Expected: All tests pass, no failures.

- [ ] **Step 4: Final commit**

```bash
git add agents/components/__init__.py
git commit -m "chore: export Phase 1 components from agents/components/__init__.py"
```

---

## Quick Reference

| Run all Phase 1 tests | `python -m pytest tests/test_arm_adapter.py tests/test_capability_registry.py tests/test_gap_detector.py tests/test_scene_spec.py tests/test_plan_generator.py tests/test_voice_template_agent.py tests/test_failure_recorder.py tests/test_training_script_generator.py tests/test_phase1_integration.py -v` |
|---|---|
| Check hardware package | `python -c "from agents.hardware import ArmAdapter, RobotCapabilityRegistry, GapDetectionEngine; print('OK')"` |
| Check full pipeline | `python -c "from agents.components import SceneSpec, PlanGenerator, VoiceTemplateAgent; print('OK')"` |
