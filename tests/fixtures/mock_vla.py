"""MockVLA factory for test use."""
import random


class _MockVLAAdapter:
    """Mock VLA adapter for testing."""

    def __init__(self, success_rate: float, action_noise: bool):
        """Initialize mock VLA adapter.

        Args:
            success_rate: Probability of successful execution (0-1).
            action_noise: Whether to add Gaussian noise to actions.
        """
        self.success_rate = success_rate
        self.action_noise = action_noise
        self.action_history: list = []

    def reset(self) -> None:
        """Reset action history."""
        self.action_history.clear()

    async def act(self, observation: dict, instruction: str) -> list[float]:
        """Generate 7-DOF action from observation and instruction.

        Args:
            observation: Input observation dict (typically with "image" key).
            instruction: Natural language instruction.

        Returns:
            7-dimensional action array.
        """
        base = [0.1, 0.0, 0.2, 0.0, 0.0, 0.0, 0.5]
        if self.action_noise:
            base = [a + random.gauss(0, 0.01) for a in base]
        self.action_history.append(base)
        return base

    async def execute(self, action: list[float]) -> dict:
        """Execute action on robot.

        Args:
            action: 7-dimensional action array.

        Returns:
            Dict with 'success' bool and 'action' array.
        """
        return {"success": random.random() < self.success_rate, "action": action}


def make_mock_vla(success_rate: float = 1.0, action_noise: bool = False) -> _MockVLAAdapter:
    """Factory function to create a mock VLA adapter.

    Args:
        success_rate: Probability of successful execution (0-1).
        action_noise: Whether to add noise to actions.

    Returns:
        Mock VLA adapter instance.
    """
    return _MockVLAAdapter(success_rate=success_rate, action_noise=action_noise)
