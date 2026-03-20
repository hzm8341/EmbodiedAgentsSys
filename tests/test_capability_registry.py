# tests/test_capability_registry.py
import pytest
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
