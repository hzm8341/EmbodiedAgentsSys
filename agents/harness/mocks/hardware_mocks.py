from __future__ import annotations
import asyncio
import random
from agents.hardware.arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities


class MockArmAdapter(ArmAdapter):
    def __init__(
        self,
        joint_error_rate: float = 0.05,
        gripper_slope_rate: float = 0.1,
        position_noise: float = 0.005,
        latency_ms: int = 50,
    ):
        self._joint_error_rate = joint_error_rate
        self._gripper_slope_rate = gripper_slope_rate
        self._position_noise = position_noise
        self._latency_ms = latency_ms
        self._gripper_open = 0.0
        self._joints = [0.0] * 7

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = [0.1] * 7
        return True

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = angles[:]
        return True

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        await asyncio.sleep(self._latency_ms / 2000.0)
        if random.random() < self._gripper_slope_rate:
            return False
        self._gripper_open = max(0.0, min(1.0, opening))
        return True

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=self._joints[:],
            end_effector_pose=Pose6D(x=0.3, y=0.0, z=0.2, roll=0, pitch=0, yaw=0),
            gripper_opening=self._gripper_open,
            is_moving=False,
            error_code=0,
        )

    async def is_ready(self) -> bool:
        return True

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=["manipulation.grasp", "manipulation.place", "manipulation.reach"],
        )
