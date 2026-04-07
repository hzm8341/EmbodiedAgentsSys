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
