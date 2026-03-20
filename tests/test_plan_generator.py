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


@pytest.mark.anyio
async def test_generate_returns_execution_plan(generator):
    plan = await generator.generate(SCENE)
    assert isinstance(plan, ExecutionPlan)


@pytest.mark.anyio
async def test_plan_has_steps(generator):
    plan = await generator.generate(SCENE)
    assert len(plan.steps) > 0


@pytest.mark.anyio
async def test_steps_use_dot_notation(generator):
    plan = await generator.generate(SCENE)
    for step in plan.steps:
        assert "." in step["skill"], f"Expected dot-notation skill, got: {step['skill']}"


@pytest.mark.anyio
async def test_yaml_output_valid(generator):
    plan = await generator.generate(SCENE)
    yaml_str = plan.to_yaml()
    parsed = yaml.safe_load(yaml_str)
    assert "plan_id" in parsed
    assert "steps" in parsed
    assert "status" in parsed


@pytest.mark.anyio
async def test_markdown_output_contains_scene_type(generator):
    plan = await generator.generate(SCENE)
    md = plan.to_markdown()
    assert "warehouse_pick" in md


@pytest.mark.anyio
async def test_gap_steps_annotated(generator):
    """navigation.goto is a gap for arm — steps injected manually to bypass mock planner."""
    import os, tempfile
    from agents.hardware.capability_registry import RobotCapabilityRegistry
    from agents.hardware.gap_detector import GapDetectionEngine

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


@pytest.mark.anyio
async def test_capability_gaps_field_informational(generator):
    plan = await generator.generate(SCENE)
    yaml_str = plan.to_yaml()
    parsed = yaml.safe_load(yaml_str)
    assert "capability_gaps" in parsed
