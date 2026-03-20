"""LeRobot ArmAdapter wrapper — delegates to LeRobot client if available."""
import logging
from typing import Any

from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities

_LOG = logging.getLogger(__name__)

_LEROBOT_SKILLS = [
    "manipulation.grasp",
    "manipulation.place",
    "manipulation.reach",
]


class LeRobotArmAdapter(ArmAdapter):
    """Wraps LeRobot transport client under the ArmAdapter ABC.

    mock=True when no real LeRobot endpoint is configured.
    """

    def __init__(self, config: dict[str, Any]):
        self._mock = config.get("mock", False)
        self._endpoint = config.get("endpoint", "")
        self._client = None
        if not self._mock and self._endpoint:
            self._try_connect()

    def _try_connect(self) -> None:
        try:
            from agents.clients.lerobot import LeRobotClient  # noqa: F401
        except ImportError:
            _LOG.warning("LeRobot client not available — mock mode")
            self._mock = True

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("LeRobot move_to_pose requires Phase 2 bridge")

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("LeRobot move_joints requires Phase 2 bridge")

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("LeRobot set_gripper requires Phase 2 bridge")

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=[0.0] * 6,
            end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
            gripper_opening=0.5,
            is_moving=False,
        )

    async def is_ready(self) -> bool:
        return self._mock

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=list(_LEROBOT_SKILLS),
            max_payload_kg=1.0,
            reach_m=0.65,
        )
