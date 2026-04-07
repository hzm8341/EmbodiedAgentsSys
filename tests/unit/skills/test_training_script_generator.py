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
