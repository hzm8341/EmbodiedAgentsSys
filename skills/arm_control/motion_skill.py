"""
机械臂运动控制Skill

负责执行基于解析结果的机械臂运动动作。
支持基础运动、位置移动、轨迹运动等。
"""
from typing import Dict, Any, Optional, List
from .status import SkillStatus

from .status import SkillStatus

# SkillResult类

class SkillResult:
    """Skill执行结果"""
    
    def __init__(self, status: SkillStatus, output: Any = None, 
                 error: Optional[str] = None, metadata: Dict[str, Any] = None):
        self.status = status
        self.output = output
        self.error = error
        self.metadata = metadata or {}


class MotionSkill:
    """
    机械臂运动控制Skill
    
    根据输入的运动参数控制机械臂末端执行器移动。
    支持:
    - 方向+距离移动
    - 绝对位置移动
    - 预设位置移动
    """
    
    # 预设位置坐标
    PRESET_POSITIONS = {
        "home": [0.0, -0.5, 0.3, 0.0, 0.5, 0.0],  # 关节角度或笛卡尔位置
        "photo_position": [0.3, 0.0, 0.4, 0.0, 0.3, 0.0],
        "拍照位置": [0.3, 0.0, 0.4, 0.0, 0.3, 0.0],  # 中文别名
        "wait_position": [0.0, 0.0, 0.5, 0.0, 0.0, 0.0],
        "bin": [0.4, -0.3, 0.2, 0.0, 0.2, 0.0],
        "料框": [0.4, -0.3, 0.2, 0.0, 0.2, 0.0],  # 中文别名
        "production_line": [-0.3, 0.2, 0.3, 0.0, 0.4, 0.0],
        "产线": [-0.3, 0.2, 0.3, 0.0, 0.4, 0.0],  # 中文别名
    }
    
    # 方向向量（相对于基坐标系）
    DIRECTION_VECTORS = {
        "forward": [0.1, 0, 0],   # X正方向
        "backward": [-0.1, 0, 0], # X负方向
        "up": [0, 0, 0.1],        # Z正方向
        "down": [0, 0, -0.1],    # Z负方向
        "left": [0, 0.1, 0],     # Y正方向
        "right": [0, -0.1, 0],   # Y负方向
    }
    
    def __init__(self, robot_config: Optional[Dict] = None):
        """
        初始化运动控制Skill
        
        Args:
            robot_config: 机器人配置，包含连接参数等
        """
        self.robot_config = robot_config or {}
        self._connected = False
        self._current_position = [0.0, -0.5, 0.3, 0.0, 0.5, 0.0]
        self._status = SkillStatus.IDLE
        
    @property
    def status(self) -> SkillStatus:
        """获取当前状态"""
        return self._status
    
    async def execute(self, action: str, **kwargs) -> SkillResult:
        """
        执行运动控制
        
        Args:
            action: 动作类型 (move, move_to, move_relative)
            **kwargs: 动作参数
                - direction: 移动方向 (forward, backward, up, down, left, right)
                - distance: 移动距离（米）
                - target: 目标位置名称或坐标
                - position: [x, y, z, roll, pitch, yaw]
                
        Returns:
            SkillResult: 执行结果
        """
        self._status = SkillStatus.RUNNING
        
        try:
            if action == "move":
                # 方向+距离移动
                result = await self._move_direction(
                    kwargs.get("direction"),
                    kwargs.get("distance", 0.1)
                )
            elif action == "move_to":
                # 移动到目标位置
                result = await self._move_to_target(kwargs.get("target"))
            elif action == "move_relative":
                # 相对移动
                result = await self._move_relative(kwargs.get("position"))
            else:
                result = SkillResult(
                    status=SkillStatus.FAILED,
                    error=f"Unknown action: {action}"
                )
            
            # 确保result被正确赋值
            if result is None:
                result = SkillResult(
                    status=SkillStatus.FAILED,
                    error="Action returned None"
                )
            
            self._status = SkillStatus.SUCCESS
            return result
                
            self._status = SkillStatus.SUCCESS
            return result
            
        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(
                status=SkillStatus.FAILED,
                error=str(e)
            )
    
    async def _move_direction(self, direction: str, distance: float) -> SkillResult:
        """按方向移动"""
        if direction not in self.DIRECTION_VECTORS:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Invalid direction: {direction}"
            )
        
        # 计算目标位置
        direction_vector = self.DIRECTION_VECTORS[direction]
        target_position = [
            self._current_position[0] + direction_vector[0] * distance * 10,  # 放大距离
            self._current_position[1] + direction_vector[1] * distance * 10,
            self._current_position[2] + direction_vector[2] * distance * 10,
            self._current_position[3],
            self._current_position[4],
            self._current_position[5],
        ]
        
        # 模拟移动（实际会调用ROS/机械臂接口）
        self._current_position = target_position
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "move_direction",
                "direction": direction,
                "distance": distance,
                "current_position": self._current_position,
            },
            metadata={
                "motion_type": "direction",
                "executed": True,
            }
        )
    
    async def _move_to_target(self, target: str) -> SkillResult:
        """移动到预设位置"""
        if target not in self.PRESET_POSITIONS:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Unknown target: {target}"
            )
        
        target_position = self.PRESET_POSITIONS[target]
        
        # 模拟移动
        self._current_position = target_position
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "move_to",
                "target": target,
                "position": target_position,
            },
            metadata={
                "motion_type": "preset",
                "executed": True,
            }
        )
    
    async def _move_relative(self, position: List[float]) -> SkillResult:
        """相对移动"""
        if len(position) != 6:
            return SkillResult(
                status=SkillStatus.FAILED,
                error="Position must have 6 values [x, y, z, roll, pitch, yaw]"
            )
        
        # 计算相对移动
        target_position = [
            self._current_position[0] + position[0],
            self._current_position[1] + position[1],
            self._current_position[2] + position[2],
            self._current_position[3] + position[3],
            self._current_position[4] + position[4],
            self._current_position[5] + position[5],
        ]
        
        self._current_position = target_position
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "move_relative",
                "relative": position,
                "current_position": self._current_position,
            },
            metadata={
                "motion_type": "relative",
                "executed": True,
            }
        )
    
    def get_current_position(self) -> List[float]:
        """获取当前位置"""
        return self._current_position.copy()
    
    async def validate_inputs(self, **kwargs) -> bool:
        """验证输入参数"""
        action = kwargs.get("action")
        if not action:
            return False
            
        valid_actions = ["move", "move_to", "move_relative"]
        return action in valid_actions


def create_motion_skill(robot_config: Dict = None) -> MotionSkill:
    """工厂函数: 创建MotionSkill实例"""
    return MotionSkill(robot_config=robot_config)
