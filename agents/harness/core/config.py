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
