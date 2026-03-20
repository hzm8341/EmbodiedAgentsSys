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


@pytest.mark.anyio
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


@pytest.mark.anyio
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


@pytest.mark.anyio
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


@pytest.mark.anyio
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
