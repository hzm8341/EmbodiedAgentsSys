"""MockArm factory for test use."""
import asyncio
import random
from agents.hardware.arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities


class _MockArmAdapter(ArmAdapter):
    """Mock arm adapter for testing."""

    def __init__(self, joint_error_rate: float, latency_ms: int):
        """Initialize mock arm adapter.

        Args:
            joint_error_rate: Probability of joint movement failure (0-1).
            latency_ms: Simulated latency in milliseconds.
        """
        self._joint_error_rate = joint_error_rate
        self._latency_ms = latency_ms
        self._joints = [0.0] * 7
        self._gripper = 0.0

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        """Move end effector to target pose.

        Args:
            pose: Target pose.
            speed: Movement speed (0-1).

        Returns:
            True if movement succeeded, False otherwise.
        """
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = [0.1] * 7
        return True

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        """Move joints to target angles.

        Args:
            angles: Target joint angles.
            speed: Movement speed (0-1).

        Returns:
            True if movement succeeded, False otherwise.
        """
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = angles[:]
        return True

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        """Set gripper opening.

        Args:
            opening: Gripper opening (0-1, 0=closed, 1=open).
            force: Gripper force in Newtons.

        Returns:
            True if command succeeded.
        """
        self._gripper = max(0.0, min(1.0, opening))
        return True

    async def get_state(self) -> RobotState:
        """Get current robot state.

        Returns:
            Current state including joint angles, pose, and gripper opening.
        """
        return RobotState(
            joint_angles=self._joints[:],
            end_effector_pose=Pose6D(0.3, 0.0, 0.2, 0, 0, 0),
            gripper_opening=self._gripper,
            is_moving=False,
            error_code=0,
        )

    async def is_ready(self) -> bool:
        """Check if robot is ready to execute commands.

        Returns:
            Always True for mock.
        """
        return True

    async def emergency_stop(self) -> None:
        """Emergency stop the robot."""
        pass

    def get_capabilities(self) -> RobotCapabilities:
        """Get robot capabilities.

        Returns:
            Robot capabilities descriptor.
        """
        return RobotCapabilities(robot_type="arm", supported_skills=[])


def make_mock_arm(joint_error_rate: float = 0.0, latency_ms: int = 0) -> _MockArmAdapter:
    """Factory function to create a mock arm adapter.

    Args:
        joint_error_rate: Probability of joint movement failure (0-1).
        latency_ms: Simulated latency in milliseconds.

    Returns:
        Mock arm adapter instance.
    """
    return _MockArmAdapter(joint_error_rate=joint_error_rate, latency_ms=latency_ms)
