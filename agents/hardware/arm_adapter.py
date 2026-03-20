"""ArmAdapter — 机械臂硬件抽象接口 (Phase 1)."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Pose6D:
    """6-DOF end-effector pose in Cartesian space (metres, radians)."""
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


@dataclass
class RobotState:
    """Snapshot of robot state at a single instant."""
    joint_angles: list[float]
    end_effector_pose: Pose6D
    gripper_opening: float   # 0.0 = closed, 1.0 = fully open
    is_moving: bool
    error_code: int = 0


@dataclass
class RobotCapabilities:
    """Static capabilities metadata reported by the adapter."""
    robot_type: str                          # "arm" | "mobile" | "mobile_arm"
    supported_skills: list[str]              # dot-notation skill IDs
    max_payload_kg: float = 0.0
    reach_m: float = 0.0


class ArmAdapter(ABC):
    """Abstract base class for all robotic arm hardware adapters."""

    @abstractmethod
    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        """Move end-effector to Pose6D. Returns True on success."""

    @abstractmethod
    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        """Command joint angles (radians). Returns True on success."""

    @abstractmethod
    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        """Set gripper opening [0,1] with force limit (N). Returns True on success."""

    @abstractmethod
    async def get_state(self) -> RobotState:
        """Return current robot state snapshot."""

    @abstractmethod
    async def is_ready(self) -> bool:
        """Return True if the arm is powered, homed, and ready for commands."""

    @abstractmethod
    async def emergency_stop(self) -> None:
        """Immediately halt all motion."""

    @abstractmethod
    def get_capabilities(self) -> RobotCapabilities:
        """Return static capabilities metadata."""
