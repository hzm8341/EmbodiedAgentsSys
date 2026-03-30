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
