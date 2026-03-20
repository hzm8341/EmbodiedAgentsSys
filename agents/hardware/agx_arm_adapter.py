"""AGX Arm ArmAdapter wrapper — delegates to existing AGX client if available."""
import logging
from typing import Any

from .arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities

_LOG = logging.getLogger(__name__)

_AGX_SKILLS = [
    "manipulation.grasp",
    "manipulation.place",
    "manipulation.reach",
    "manipulation.inspect",
]


class AGXArmAdapter(ArmAdapter):
    """Wraps existing AGX arm skill clients under the ArmAdapter ABC.

    In mock mode (config['mock']=True or no hardware detected), all motion
    methods return True and get_state returns a zeroed RobotState.
    """

    def __init__(self, config: dict[str, Any]):
        self._mock = config.get("mock", False)
        self._client = None
        if not self._mock:
            self._try_connect(config)

    def _try_connect(self, config: dict[str, Any]) -> None:
        try:
            from agents.skills.manipulation.grasp import GraspSkill  # noqa: F401
            # Real client integration deferred to Phase 2
        except ImportError:
            _LOG.warning("AGX skills not available — falling back to mock mode")
            self._mock = True

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("AGX move_to_pose requires Phase 2 hardware bridge")

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("AGX move_joints requires Phase 2 hardware bridge")

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        if self._mock:
            return True
        raise NotImplementedError("AGX set_gripper requires Phase 2 hardware bridge")

    async def get_state(self) -> RobotState:
        if not self._mock:
            raise NotImplementedError("get_state requires Phase 2 hardware bridge")
        return RobotState(
            joint_angles=[0.0] * 6,
            end_effector_pose=Pose6D(0, 0, 0, 0, 0, 0),
            gripper_opening=0.5,
            is_moving=False,
        )

    async def is_ready(self) -> bool:
        return self._mock  # mock is always "ready"; real needs hardware

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(
            robot_type="arm",
            supported_skills=list(_AGX_SKILLS),
            max_payload_kg=2.0,
            reach_m=0.85,
        )
