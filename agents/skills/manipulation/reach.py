# agents/skills/manipulation/reach.py
"""ReachSkill 到达技能

VLA 驱动的机械臂到达目标位置技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List


class ReachSkill(VLASkill):
    """到达技能

    用于控制机械臂到达指定位置。
    """

    required_inputs: List[str] = ["target_position", "observation"]
    produced_outputs: List[str] = ["success", "actual_position"]
    max_steps: int = 30
    position_threshold: float = 0.02  # 位置误差阈值 (m)

    def __init__(self, target_position: List[float], **kwargs):
        """初始化到达技能

        Args:
            target_position: 目标位置 [x, y, z]
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.target_position = target_position
        # 从 kwargs 获取阈值
        self.position_threshold = kwargs.get("position_threshold", self.position_threshold)

    def build_skill_token(self) -> str:
        """构建技能令牌"""
        return f"reach {self.target_position}"

    def check_preconditions(self, observation: Dict) -> bool:
        """检查执行前置条件

        机械臂必须处于安全状态（无碰撞）
        """
        # 检查是否有碰撞检测
        if "collision_detected" in observation:
            return not observation["collision_detected"]
        return True  # 默认允许执行

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        到达目标位置（通过距离判断）
        """
        # 方式1: 直接检查 position_reached 标志
        if "position_reached" in observation:
            return observation["position_reached"]

        # 方式2: 通过距离判断
        if "distance_to_target" in observation:
            return observation["distance_to_target"] < self.position_threshold

        return False

    def get_target_position(self) -> List[float]:
        """获取目标位置"""
        return self.target_position

    def set_position_threshold(self, threshold: float) -> None:
        """设置位置误差阈值"""
        self.position_threshold = threshold
