from __future__ import annotations
import random
import logging

logger = logging.getLogger(__name__)


class MockVLAAdapter:
    def __init__(self, success_rate: float = 0.75, action_noise: bool = True):
        self.success_rate = success_rate
        self.action_noise = action_noise

    def reset(self) -> None:
        pass

    async def act(self, observation: dict, instruction: str) -> list[float]:
        base = [0.1, 0.0, 0.2, 0.0, 0.0, 0.0, 0.5]
        if self.action_noise:
            base = [a + random.gauss(0, 0.01) for a in base]
        return base

    async def execute(self, action: list[float]) -> dict:
        success = random.random() < self.success_rate
        if not success:
            logger.warning(f"MockVLAAdapter: action execution failed (success_rate={self.success_rate})")
        return {"success": success, "action": action}
