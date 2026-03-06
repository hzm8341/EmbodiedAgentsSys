"""
关节运动控制Skill

负责控制机械臂各关节的运动。
"""
from typing import Dict, Any, Optional, List
from .status import SkillStatus


class SkillResult:
    """Skill执行结果"""
    
    def __init__(self, status: SkillStatus, output: Any = None, 
                 error: Optional[str] = None, metadata: Dict[str, Any] = None):
        self.status = status
        self.output = output
        self.error = error
        self.metadata = metadata or {}


class JointSkill:
    """
    关节运动控制Skill
    
    直接控制机械臂各关节的角度。
    支持:
    - 关节角度移动
    - 关节速度控制
    - 关节位置查询
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._joint_count = self.config.get("joint_count", 6)
        self._joint_positions = [0.0] * self._joint_count
        self._joint_limits = self.config.get("joint_limits", {
            "min": [-3.14] * 6,
            "max": [3.14] * 6,
        })
        self._status = SkillStatus.IDLE
        
    @property
    def status(self) -> SkillStatus:
        return self._status
    
    async def execute(self, action: str, **kwargs) -> SkillResult:
        self._status = SkillStatus.RUNNING
        result = None
        
        try:
            if action == "move_j":
                result = await self._move_joints(kwargs.get("positions", []))
            elif action == "move_j_relative":
                result = await self._move_joints_relative(kwargs.get("positions", []))
            elif action == "move_single_joint":
                result = await self._move_single_joint(
                    kwargs.get("joint_index", 0),
                    kwargs.get("angle", 0.0)
                )
            elif action == "set_velocity":
                result = await self._set_velocity(kwargs.get("velocities", []))
            else:
                result = SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Unknown action: {action}"
                )
            
            if result is None:
                result = SkillResult(
                    status=SkillStatus.FAILED,
                    error="Action returned None"
                )
            
            self._status = SkillStatus.SUCCESS
            return result
            
        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(
                status=SkillStatus.FAILED,
                error=str(e)
            )
    
    async def _move_joints(self, positions: List[float]) -> SkillResult:
        if len(positions) != self._joint_count:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Expected {self._joint_count} joints, got {len(positions)}"
            )
        
        for i, pos in enumerate(positions):
            if pos < self._joint_limits["min"][i] or pos > self._joint_limits["max"][i]:
                return SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Joint {i} position {pos} out of limits"
                )
        
        self._joint_positions = positions.copy()
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={"action": "move_j", "positions": self._joint_positions},
            metadata={"motion_type": "joint", "executed": True}
        )
    
    async def _move_joints_relative(self, delta: List[float]) -> SkillResult:
        if len(delta) != self._joint_count:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Expected {self._joint_count} delta values"
            )
        
        new_positions = [self._joint_positions[i] + delta[i] for i in range(self._joint_count)]
        
        for i, pos in enumerate(new_positions):
            if pos < self._joint_limits["min"][i] or pos > self._joint_limits["max"][i]:
                return SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Joint {i} would be out of limits"
                )
        
        self._joint_positions = new_positions
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={"action": "move_j_relative", "positions": self._joint_positions},
            metadata={"motion_type": "joint_relative", "executed": True}
        )
    
    async def _move_single_joint(self, joint_index: int, angle: float) -> SkillResult:
        if joint_index < 0 or joint_index >= self._joint_count:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Invalid joint index: {joint_index}"
            )
        
        if angle < self._joint_limits["min"][joint_index] or \
           angle > self._joint_limits["max"][joint_index]:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Joint {joint_index} angle out of limits"
            )
        
        self._joint_positions[joint_index] = angle
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "move_single_joint",
                "joint_index": joint_index,
                "angle": angle,
                "positions": self._joint_positions
            },
            metadata={"motion_type": "single_joint", "executed": True}
        )
    
    async def _set_velocity(self, velocities: List[float]) -> SkillResult:
        if len(velocities) != self._joint_count:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Expected {self._joint_count} velocities"
            )
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={"action": "set_velocity", "velocities": velocities},
            metadata={"motion_type": "velocity", "executed": True}
        )
    
    def get_current_positions(self) -> List[float]:
        return self._joint_positions.copy()
    
    async def validate_inputs(self, **kwargs) -> bool:
        action = kwargs.get("action")
        if not action:
            return False
        valid_actions = ["move_j", "move_j_relative", "move_single_joint", "set_velocity"]
        return action in valid_actions


def create_joint_skill(config: Dict = None) -> JointSkill:
    return JointSkill(config=config)
