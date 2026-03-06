"""
夹爪控制Skill

负责控制机械臂末端夹爪的开合动作。
"""
from typing import Dict, Any, Optional
from .status import SkillStatus


class SkillResult:
    """Skill执行结果"""
    
    def __init__(self, status: SkillStatus, output: Any = None, 
                 error: Optional[str] = None, metadata: Dict[str, Any] = None):
        self.status = status
        self.output = output
        self.error = error
        self.metadata = metadata or {}


class GripperSkill:
    """
    夹爪控制Skill
    
    控制机械臂末端夹爪的开合动作。
    支持:
    - 打开夹爪
    - 关闭夹爪
    - 设置指定开合度
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化夹爪控制Skill
        
        Args:
            config: 夹爪配置，包含最大开合度、类型等
        """
        self.config = config or {}
        self._gripper_position = 0.0  # 0.0 = 完全打开, 1.0 = 完全关闭
        self._status = SkillStatus.IDLE
        self._max_position = self.config.get("max_position", 1.0)
        
    @property
    def status(self) -> SkillStatus:
        return self._status
    
    async def execute(self, action: str, **kwargs) -> SkillResult:
        """
        执行夹爪控制
        
        Args:
            action: 动作类型 (open, close, set_position)
            **kwargs: 动作参数
                - position: 目标位置 (0.0-1.0)
                - force: 夹爪力度 (可选)
                
        Returns:
            SkillResult: 执行结果
        """
        self._status = SkillStatus.RUNNING
        result = None
        
        try:
            if action == "open":
                result = await self._open()
            elif action == "close":
                result = await self._close()
            elif action == "set_position":
                result = await self._set_position(
                    kwargs.get("position", 1.0),
                    kwargs.get("force", 0.5)
                )
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
            
        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(
                status=SkillStatus.FAILED,
                error=str(e)
            )
    
    async def _open(self) -> SkillResult:
        """打开夹爪"""
        self._gripper_position = 0.0
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "open",
                "position": self._gripper_position,
            },
            metadata={
                "gripper_action": "open",
                "executed": True,
            }
        )
    
    async def _close(self) -> SkillResult:
        """关闭夹爪"""
        self._gripper_position = self._max_position
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "close",
                "position": self._gripper_position,
            },
            metadata={
                "gripper_action": "close",
                "executed": True,
            }
        )
    
    async def _set_position(self, position: float, force: float = 0.5) -> SkillResult:
        """设置指定位置"""
        if position < 0.0 or position > self._max_position:
            return SkillResult(
                status=SkillStatus.FAILED,
                error=f"Position must be between 0.0 and {self._max_position}"
            )
        
        self._gripper_position = position
        
        return SkillResult(
            status=SkillStatus.SUCCESS,
            output={
                "action": "set_position",
                "position": position,
                "force": force,
            },
            metadata={
                "gripper_action": "position",
                "executed": True,
            }
        )
    
    def get_current_position(self) -> float:
        """获取当前夹爪位置"""
        return self._gripper_position
    
    async def validate_inputs(self, **kwargs) -> bool:
        """验证输入参数"""
        action = kwargs.get("action")
        if not action:
            return False
            
        valid_actions = ["open", "close", "set_position"]
        if action not in valid_actions:
            return False
            
        if action == "set_position":
            position = kwargs.get("position", -1)
            if position < 0.0 or position > self._max_position:
                return False
                
        return True


def create_gripper_skill(config: Dict = None) -> GripperSkill:
    """工厂函数: 创建GripperSkill实例"""
    return GripperSkill(config=config)
