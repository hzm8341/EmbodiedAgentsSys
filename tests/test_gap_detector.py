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
