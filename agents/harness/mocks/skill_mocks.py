from __future__ import annotations
import random
from dataclasses import dataclass, field


@dataclass
class SkillResult:
    success: bool
    content: str
    data: dict = field(default_factory=dict)


class MockSkillRegistry:
    def __init__(self, default_success_rate: float = 0.85,
                 per_skill_rate: dict | None = None):
        self.default_success_rate = default_success_rate
        self.per_skill_rate = per_skill_rate or {}

    def call_skill(self, skill_id: str, args: dict) -> SkillResult:
        rate = self.per_skill_rate.get(skill_id, self.default_success_rate)
        success = random.random() < rate
        return SkillResult(
            success=success,
            content=f"[mock] {skill_id} {'succeeded' if success else 'failed'}",
            data={"skill_id": skill_id},
        )
