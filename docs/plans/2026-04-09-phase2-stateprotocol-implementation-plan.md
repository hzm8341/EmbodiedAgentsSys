:orphan:

# Phase 2: State Protocol Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement State-as-a-File protocol following PhyAgentOS State-as-a-File pattern with industrial safety.

**Architecture:**
- `embodiedagentsys/state/` module with StateManager
- Markdown-based protocol files (ACTION.md, ENVIRONMENT.md, etc.)
- Optional disk persistence (default: memory-only for backward compatibility)

**Tech Stack:** Pure Python, pathlib, asyncio, watchdog (optional file watching)

---

## Task 1: Create State Module Structure

**Files:**
- Create: `embodiedagentsys/state/__init__.py`
- Create: `embodiedagentsys/state/types.py` (ProtocolType, StateEntry)
- Create: `embodiedagentsys/state/manager.py` (StateManager)
- Create: `embodiedagentsys/state/protocols/__init__.py`
- Create: `embodiedagentsys/state/protocols/action_protocol.py`
- Create: `embodiedagentsys/state/protocols/environment_protocol.py`
- Create: `embodiedagentsys/state/templates/action_template.md`
- Create: `embodiedagentsys/state/templates/environment_template.md`
- Test: `tests/test_state/test_manager.py`
- Test: `tests/test_state/test_protocols.py`

**Step 1: Create test file - state types**

```python
# tests/test_state/__init__.py
# tests/test_state/test_types.py
import pytest
from embodiedagentsys.state.types import ProtocolType, StateEntry


class TestProtocolType:
    def test_protocol_types_defined(self):
        """All required protocol types must be defined."""
        assert ProtocolType.ACTION == "action"
        assert ProtocolType.ENVIRONMENT == "environment"
        assert ProtocolType.EMBODIED == "embodied"
        assert ProtocolType.LESSONS == "lessons"


class TestStateEntry:
    def test_state_entry_creation(self):
        """StateEntry should capture state with metadata."""
        from datetime import datetime
        entry = StateEntry(
            protocol_type=ProtocolType.ACTION,
            content={"action": "move_to", "params": {"x": 1.0}},
            updated_by="agent",
            timestamp=datetime.now()
        )
        assert entry.protocol_type == ProtocolType.ACTION
        assert entry.content["action"] == "move_to"
```

**Step 2: Create embodiedagentsys/state/types.py**

```python
"""State protocol types."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProtocolType(Enum):
    """Types of state protocols following PhyAgentOS pattern."""
    ACTION = "action"
    ENVIRONMENT = "environment"
    EMBODIED = "embodied"
    LESSONS = "lessons"


@dataclass
class StateEntry:
    """Single state entry with metadata for audit trail."""
    protocol_type: ProtocolType
    content: dict
    updated_by: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "protocol_type": self.protocol_type.value,
            "content": self.content,
            "updated_by": self.updated_by,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
        }
```

**Step 3: Create test file - state manager**

```python
# tests/test_state/test_manager.py
import pytest
from embodiedagentsys.state.manager import StateManager
from embodiedagentsys.state.types import ProtocolType


class TestStateManager:
    def test_manager_creation(self):
        """StateManager should be creatable."""
        manager = StateManager()
        assert manager is not None

    def test_enable_files_false_by_default(self):
        """State files should be disabled by default for backward compat."""
        manager = StateManager()
        assert manager._enable_files is False

    def test_write_and_read_memory(self):
        """Should write and read state from memory when files disabled."""
        manager = StateManager(enable_state_files=False)
        manager.write_protocol(ProtocolType.ACTION, {"action": "test"})
        content = manager.read_protocol(ProtocolType.ACTION)
        assert content["action"] == "test"

    def test_read_empty_returns_dict(self):
        """Reading non-existent protocol should return empty dict."""
        manager = StateManager()
        content = manager.read_protocol(ProtocolType.ACTION)
        assert content == {}

    def test_enable_state_files(self):
        """Should enable state files when requested."""
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(
                workspace_path=pathlib.Path(tmpdir),
                enable_state_files=True
            )
            assert manager._enable_files is True
```

**Step 4: Create embodiedagentsys/state/manager.py**

```python
"""State manager with optional disk persistence.

Following 《工业Agent设计准则》:
- P6: Complete audit trail of state changes
- P4: 闭环设计 - state represents confirmed world state

Default is memory-only (backward compatible).
Enable disk persistence via enable_state_files=True.
"""

from pathlib import Path
from typing import Optional

from embodiedagentsys.state.types import ProtocolType, StateEntry


class StateManager:
    """Manages state protocols with optional disk persistence.

    Default behavior (enable_state_files=False) maintains memory-only
    state for backward compatibility with existing code.
    """

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        enable_state_files: bool = False
    ):
        """
        Args:
            workspace_path: Path for state files. Defaults to ~/.embodiedagents/workspace/
            enable_state_files: If True, persist state to disk. Default False.
        """
        self._workspace = workspace_path or Path.home() / ".embodiedagents" / "workspace"
        self._enable_files = enable_state_files
        self._memory_cache: dict[ProtocolType, dict] = {}

    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def enable_files(self) -> bool:
        return self._enable_files

    def write_protocol(self, protocol_type: ProtocolType, content: dict) -> None:
        """Write state to protocol.

        Args:
            protocol_type: Type of protocol to write.
            content: State content as dict.
        """
        self._memory_cache[protocol_type] = content
        if self._enable_files:
            self._write_to_disk(protocol_type, content)

    def read_protocol(self, protocol_type: ProtocolType) -> dict:
        """Read state from protocol.

        Args:
            protocol_type: Type of protocol to read.

        Returns:
            State content as dict, or empty dict if not found.
        """
        if self._enable_files:
            return self._read_from_disk(protocol_type)
        return self._memory_cache.get(protocol_type, {})

    def get_entry(self, protocol_type: ProtocolType, updated_by: str = "system") -> StateEntry:
        """Get StateEntry for current state.

        Args:
            protocol_type: Type of protocol.
            updated_by: Who updated this state.

        Returns:
            StateEntry with current state.
        """
        content = self.read_protocol(protocol_type)
        return StateEntry(
            protocol_type=protocol_type,
            content=content,
            updated_by=updated_by,
        )

    def _write_to_disk(self, protocol_type: ProtocolType, content: dict) -> None:
        """Write content to disk as markdown."""
        import json
        self._workspace.mkdir(parents=True, exist_ok=True)
        filename = self._get_filename(protocol_type)
        filepath = self._workspace / filename
        # Write as JSON for now (templates are markdown, but state is JSON)
        with open(filepath, 'w') as f:
            json.dump(content, f, indent=2)

    def _read_from_disk(self, protocol_type: ProtocolType) -> dict:
        """Read content from disk."""
        import json
        filepath = self._workspace / self._get_filename(protocol_type)
        if not filepath.exists():
            return {}
        with open(filepath, 'r') as f:
            return json.load(f)

    def _get_filename(self, protocol_type: ProtocolType) -> str:
        """Get filename for protocol type."""
        return f"{protocol_type.value.upper()}.json"
```

**Step 5: Create embodiedagentsys/state/__init__.py**

```python
"""State protocol module for State-as-a-File pattern.

Following PhyAgentOS State-as-a-File with industrial safety.
"""

from embodiedagentsys.state.types import ProtocolType, StateEntry
from embodiedagentsys.state.manager import StateManager

__all__ = ["ProtocolType", "StateEntry", "StateManager"]
```

**Step 6: Create embodiedagentsys/state/protocols/__init__.py**

```python
"""State protocol implementations."""

__all__ = []
```

**Step 7: Create embodiedagentsys/state/protocols/action_protocol.py**

```python
"""ACTION protocol - pending action commands.

Following PhyAgentOS pattern where ACTION.md represents
pending actions to be executed by HAL.
"""

from dataclasses import dataclass
from typing import Optional
from embodiedagentsys.state.types import ProtocolType


@dataclass
class ActionEntry:
    """Single action in ACTION protocol."""
    action_type: str
    params: dict
    status: str = "pending"  # pending, executing, completed, failed
    receipt_id: Optional[str] = None


def parse_action_protocol(content: dict) -> list[ActionEntry]:
    """Parse action protocol content into ActionEntry list."""
    actions = content.get("actions", [])
    return [ActionEntry(**a) for a in actions]


def format_action_protocol(actions: list[ActionEntry]) -> dict:
    """Format ActionEntry list into action protocol dict."""
    return {
        "schema_version": "EmbodiedAgentsSys.action.v1",
        "actions": [
            {
                "action_type": a.action_type,
                "params": a.params,
                "status": a.status,
                "receipt_id": a.receipt_id,
            }
            for a in actions
        ]
    }
```

**Step 8: Create embodiedagentsys/state/protocols/environment_protocol.py**

```python
"""ENVIRONMENT protocol - current environment state.

Following PhyAgentOS pattern where ENVIRONMENT.md stores
the scene graph and robot state.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ObjectState:
    """Object in environment."""
    id: str
    class_name: str
    position: dict  # {"x": 0.0, "y": 0.0, "z": 0.0}
    confidence: float = 1.0


@dataclass
class RobotState:
    """Robot state in environment."""
    id: str
    position: dict  # {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0}
    status: str = "idle"  # idle, moving, grasping


@dataclass
class EnvironmentState:
    """Complete environment state."""
    objects: list[ObjectState] = None
    robots: list[RobotState] = None
    updated_at: str = ""


def parse_environment_protocol(content: dict) -> EnvironmentState:
    """Parse environment protocol content."""
    objects = [
        ObjectState(**o) for o in content.get("objects", [])
    ]
    robots = [
        RobotState(**r) for r in content.get("robots", [])
    ]
    return EnvironmentState(
        objects=objects,
        robots=robots,
        updated_at=content.get("updated_at", ""),
    )
```

**Step 9: Create templates**

```bash
mkdir -p embodiedagentsys/state/templates
```

**Step 10: Create embodiedagentsys/state/templates/action_template.md**

```markdown
# Action Protocol

## Schema

```json
{
  "schema_version": "EmbodiedAgentsSys.action.v1",
  "updated_at": "2026-04-09T10:00:00Z",
  "actions": [
    {
      "action_type": "move_to",
      "params": {"x": 1.0, "y": 0.5, "z": 0.3},
      "status": "pending",
      "receipt_id": null
    }
  ]
}
```

## Status Values

- `pending`: Action waiting to be executed
- `executing`: Action currently being executed
- `completed`: Action completed successfully
- `failed`: Action failed

## Notes

- HAL Watchdog reads this file to get pending actions
- Agent writes actions to this file
- receipt_id links to ExecutionReceipt from HAL
```

**Step 11: Create embodiedagentsys/state/templates/environment_template.md**

```markdown
# Environment Protocol

## Schema

```json
{
  "schema_version": "EmbodiedAgentsSys.environment.v1",
  "updated_at": "2026-04-09T10:00:00Z",
  "scene_graph": {
    "objects": [...],
    "edges": [...]
  },
  "robots": {
    "robot_001": {
      "position": {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0},
      "status": "idle"
    }
  }
}
```

## Notes

- Updated by HAL Watchdog after each action
- Read by Agent for scene understanding
- scene_graph follows PhyAgentOS schema
```

**Step 12: Run tests**

```bash
pytest tests/test_state/test_manager.py tests/test_state/test_types.py -v
```

**Step 13: Commit**

```bash
git add embodiedagentsys/state/ tests/test_state/
git commit -m "feat(state): add StateManager and State Protocol

Phase 2: State-as-a-File pattern
- StateManager with optional disk persistence
- Protocol types: ACTION, ENVIRONMENT, EMBODIED, LESSONS
- Default memory-only for backward compatibility
"
```

---

## Task 2: Create LESSONS Protocol (经验避坑)

**Files:**
- Create: `embodiedagentsys/state/protocols/lessons_protocol.py`
- Create: `embodiedagentsys/state/templates/lessons_template.md`
- Test: `tests/test_state/test_lessons.py`

**Step 1: Create test file**

```python
# tests/test_state/test_lessons.py
import pytest
from embodiedagentsys.state.protocols.lessons_protocol import (
    LessonEntry, parse_lessons_protocol, format_lessons_protocol
)


class TestLessonEntry:
    def test_lesson_entry_creation(self):
        """LessonEntry should capture failed action details."""
        lesson = LessonEntry(
            action_type="move_to",
            params={"x": 1.0, "y": 0.0, "z": 0.5},
            failure_reason="Obstacle detected in path",
            avoidance_suggestion="Plan path around obstacle"
        )
        assert lesson.action_type == "move_to"
        assert "obstacle" in lesson.failure_reason.lower()


class TestLessonsProtocol:
    def test_parse_empty_lessons(self):
        """Should parse empty lessons list."""
        content = {"lessons": []}
        lessons = parse_lessons_protocol(content)
        assert lessons == []

    def test_parse_lessons(self):
        """Should parse lessons list."""
        content = {
            "lessons": [
                {
                    "action_type": "grasp",
                    "params": {"target": "red_ball"},
                    "failure_reason": "Object too far",
                    "avoidance_suggestion": "Move closer first"
                }
            ]
        }
        lessons = parse_lessons_protocol(content)
        assert len(lessons) == 1
        assert lessons[0].action_type == "grasp"

    def test_format_lessons(self):
        """Should format lessons list to protocol."""
        lesson = LessonEntry(
            action_type="move_to",
            params={"x": 1.0},
            failure_reason="Out of bounds",
            avoidance_suggestion="Check workspace limits"
        )
        content = format_lessons_protocol([lesson])
        assert "lessons" in content
        assert len(content["lessons"]) == 1
```

**Step 2: Create embodiedagentsys/state/protocols/lessons_protocol.py**

```python
"""LESSONS protocol - failed action experience for avoidance.

Following PhyAgentOS pattern where LESSONS.md records
failed actions to prevent repeating mistakes.
"""

from dataclasses import dataclass
from typing import list


@dataclass
class LessonEntry:
    """Single lesson from failed action.

    Following 《工业Agent设计准则》P4闭环:
    - Records what went wrong
    - Provides avoidance suggestion
    - Used by CriticValidator to prevent repeated failures
    """
    action_type: str
    params: dict
    failure_reason: str
    avoidance_suggestion: str = ""


def parse_lessons_protocol(content: dict) -> list[LessonEntry]:
    """Parse lessons protocol content into LessonEntry list.

    Args:
        content: Dict parsed from LESSONS.md JSON

    Returns:
        List of LessonEntry objects
    """
    lessons_data = content.get("lessons", [])
    return [LessonEntry(**lesson) for lesson in lessons_data]


def format_lessons_protocol(lessons: list[LessonEntry]) -> dict:
    """Format LessonEntry list into lessons protocol dict.

    Args:
        lessons: List of LessonEntry objects

    Returns:
        Dict ready for serialization to LESSONS.md
    """
    return {
        "schema_version": "EmbodiedAgentsSys.lessons.v1",
        "lessons": [
            {
                "action_type": lesson.action_type,
                "params": lesson.params,
                "failure_reason": lesson.failure_reason,
                "avoidance_suggestion": lesson.avoidance_suggestion,
            }
            for lesson in lessons
        ]
    }


def add_lesson(lessons: list[LessonEntry], new_lesson: LessonEntry) -> list[LessonEntry]:
    """Add a new lesson, avoiding duplicates.

    Args:
        lessons: Existing lessons list
        new_lesson: New lesson to add

    Returns:
        Updated lessons list
    """
    # Avoid exact duplicates
    for existing in lessons:
        if (existing.action_type == new_lesson.action_type and
            existing.params == new_lesson.params):
            return lessons
    return lessons + [new_lesson]
```

**Step 3: Create embodiedagentsys/state/templates/lessons_template.md**

```markdown
# Lessons Learned Protocol

## Schema

```json
{
  "schema_version": "EmbodiedAgentsSys.lessons.v1",
  "lessons": [
    {
      "action_type": "grasp",
      "params": {"target": "red_ball"},
      "failure_reason": "Object too far from gripper",
      "avoidance_suggestion": "Move to within 0.1m before grasping"
    }
  ]
}
```

## Purpose

Following 《工业Agent设计准则》P4闭环:
- Records failed action attempts
- Used by CriticValidator to prevent repeated mistakes
- Provides avoidance suggestions for Planner

## Notes

- New lessons should be added after each failed action
- Duplicate lessons (same action_type + params) should be deduplicated
- This file is append-only for audit trail
```

**Step 4: Run tests**

```bash
pytest tests/test_state/test_lessons.py -v
```

**Step 5: Commit**

```bash
git add embodiedagentsys/state/protocols/lessons_protocol.py embodiedagentsys/state/templates/
git commit -m "feat(state): add LESSONS protocol for experience avoidance

LESSONS protocol follows PhyAgentOS pattern:
- Records failed actions with failure reasons
- Provides avoidance suggestions
- Used by CriticValidator for P4闭环
"
```

---

## Task 3: Integration with HAL

**Files:**
- Create: `tests/test_state/test_hal_integration.py`
- Modify: `embodiedagentsys/hal/base_driver.py` (add scene sync)

**Step 1: Create integration test**

```python
# tests/test_state/test_hal_integration.py
import pytest
from embodiedagentsys.state.manager import StateManager
from embodiedagentsys.state.types import ProtocolType
from embodiedagentsys.hal.drivers import SimulationDriver


class TestHALStateIntegration:
    """Test HAL and State integration for闭环确认."""

    def test_driver_scene_synced_to_state(self):
        """Driver scene should sync to STATE."""
        from embodiedagentsys.state.manager import StateManager
        from embodiedagentsys.hal.drivers import SimulationDriver

        state_mgr = StateManager()
        driver = SimulationDriver()

        # Execute action
        receipt = driver.execute_action("move_to", {"x": 1.0, "y": 0.0, "z": 0.5})
        assert receipt.is_success()

        # Get scene from driver
        scene = driver.get_scene()

        # Write to state
        state_mgr.write_protocol(ProtocolType.ENVIRONMENT, scene)

        # Read back
        saved_scene = state_mgr.read_protocol(ProtocolType.ENVIRONMENT)
        assert saved_scene == scene

    def test_state_manager_with_hal_driver(self):
        """StateManager should work with HAL driver pattern."""
        driver = SimulationDriver()
        state_mgr = StateManager()

        # Driver provides allowed actions
        allowed = driver.get_allowed_actions()
        assert "move_to" in allowed
        assert "grasp" in allowed

        # Execute and record
        receipt = driver.execute_action("grasp", {"force": 0.8})
        state_mgr.write_protocol(
            ProtocolType.ACTION,
            {"last_action": receipt.action_type, "status": receipt.status.value}
        )

        action_state = state_mgr.read_protocol(ProtocolType.ACTION)
        assert action_state["last_action"] == "grasp"
```

**Step 2: Run tests**

```bash
pytest tests/test_state/test_hal_integration.py -v
```

**Step 3: Run all state tests**

```bash
pytest tests/test_state/ -v
```

**Step 4: Commit**

```bash
git add tests/test_state/test_hal_integration.py
git commit -m "test(state): add HAL-State integration tests

Verify HAL driver scene syncs with StateManager
"
```

---

## Summary

After Phase 2:

| Deliverable | Files |
|------------|-------|
| StateManager | `embodiedagentsys/state/manager.py` |
| Protocol types | `embodiedagentsys/state/types.py` |
| ACTION protocol | `embodiedagentsys/state/protocols/action_protocol.py` |
| ENVIRONMENT protocol | `embodiedagentsys/state/protocols/environment_protocol.py` |
| LESSONS protocol | `embodiedagentsys/state/protocols/lessons_protocol.py` |
| Templates | `embodiedagentsys/state/templates/*.md` |
| Tests | `tests/test_state/*.py` |

**Next:** Phase 3 - CriticValidator integration
