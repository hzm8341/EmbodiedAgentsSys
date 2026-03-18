# agents/skills/manipulation/reach.py
"""ReachSkill 到达技能

VLA 驱动的机械臂到达目标位置技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List
import numpy as np


class ReachSkill(VLASkill):
    """到达技能

    用于控制机械臂到达指定位置。
    """

    required_inputs: List[str] = ["target_position", "observation"]
    produced_outputs: List[str] = ["success", "actual_position"]
    max_steps: int = 30
    DEFAULT_POSITION_THRESHOLD: float = 0.01

    def __init__(
        self, target_position: List[float], position_threshold: float = None, **kwargs
    ):
        """初始化到达技能

        Args:
            target_position: 目标位置 [x, y, z]
            position_threshold: 位置误差阈值 (m)
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.target_position = target_position
        self.position_threshold = position_threshold or self.DEFAULT_POSITION_THRESHOLD

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        到达目标条件：
        1. 末端位置到达目标位置误差 < 阈值
        2. 显式标记到达
        """
        if "end_effector_pos" in observation:
            current_pos = np.array(observation["end_effector_pos"][:3])
            target = np.array(self.target_position[:3])
            error = np.linalg.norm(current_pos - target)
            if error < self.position_threshold:
                return True

        if "distance_to_target" in observation:
            distance = observation["distance_to_target"]
            if distance < self.position_threshold:
                return True

        if observation.get("position_reached", False):
            return True

        return False

    def get_target_position(self) -> List[float]:
        """获取目标位置"""
        return self.target_position

    def set_position_threshold(self, threshold: float) -> None:
        """设置位置误差阈值"""
        self.position_threshold = threshold
