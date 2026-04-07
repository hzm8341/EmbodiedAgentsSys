"""
agents/execution/tools/gripper_tool.py - 机械爪控制工具

提供机器人机械爪的控制功能：
- 打开/关闭
- 力度控制
- 位置反馈
"""

from .base import ToolBase


class GripperTool(ToolBase):
    """机械爪控制工具"""

    name = "gripper"
    description = "Robotic gripper control for object manipulation"
    keywords = ["gripper", "grasp", "open", "close", "manipulation"]

    def __init__(self):
        """初始化机械爪工具"""
        super().__init__()
        self.current_position = 0.0  # 0.0 = closed, 1.0 = open
        self.max_force = 1.0
        self.min_force = 0.0

    async def execute(self, action: str, force: float = 1.0) -> dict:
        """
        执行机械爪动作

        Args:
            action: 动作类型（'open', 'close', 'grasp'）
            force: 夹持力度（0.0 - 1.0），默认 1.0

        Returns:
            dict: 执行结果，包含 action, success, position, force 等

        Raises:
            ValueError: 无效的动作或力度
        """
        # 验证力度范围
        if force < self.min_force or force > self.max_force:
            raise ValueError(
                f"Force must be between {self.min_force} and {self.max_force}, "
                f"got {force}"
            )

        # 验证动作
        valid_actions = ["open", "close", "grasp"]
        if action not in valid_actions:
            raise ValueError(
                f"Invalid action '{action}'. Must be one of: {valid_actions}"
            )

        # 执行动作
        if action == "open":
            self.current_position = 1.0
        elif action == "close":
            self.current_position = 0.0
        elif action == "grasp":
            # grasp 动作：保持在关闭状态，使用指定的力度
            self.current_position = 0.0

        return {
            "action": action,
            "success": True,
            "position": self.current_position,
            "force": force,
            "message": f"Gripper {action} executed with force {force}",
        }

    async def validate(self, action: str, force: float = 1.0) -> bool:
        """
        验证动作的有效性

        Args:
            action: 动作类型
            force: 夹持力度

        Returns:
            bool: 是否有效
        """
        try:
            if force < self.min_force or force > self.max_force:
                return False
            if action not in ["open", "close", "grasp"]:
                return False
            return True
        except Exception:
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        # 打开机械爪以释放任何被抓取的物体
        await self.execute(action="open")
