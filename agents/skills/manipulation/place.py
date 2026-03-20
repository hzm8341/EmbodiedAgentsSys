# agents/skills/manipulation/place.py
"""PlaceSkill 放置技能

VLA 驱动的物体放置技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List
import numpy as np


class PlaceSkill(VLASkill):
    """放置技能

    用于将物体放置到指定位置。
    """

    required_inputs: List[str] = ["target_position", "observation"]
    produced_outputs: List[str] = ["success", "place_position"]
    max_steps: int = 50

    DEFAULT_POSITION_THRESHOLD: float = 0.005

    def __init__(
        self, target_position: List[float], position_threshold: float = None, **kwargs
    ):
        """初始化放置技能

        Args:
            target_position: 目标位置 [x, y, z]
            position_threshold: 位置误差阈值 (m)
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.target_position = target_position
        self._position_threshold = position_threshold or self.DEFAULT_POSITION_THRESHOLD

    def build_skill_token(self) -> str:
        """构建技能令牌"""
        return f"place(position={self.target_position})"

    def check_preconditions(self, observation: Dict) -> bool:
        """检查前置条件：物体已被抓取"""
        return bool(observation.get("object_held", False))

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        放置成功条件：
        1. 末端位置到达目标位置误差 < 阈值
        2. 显式标记放置成功
        """
        if "end_effector_pos" in observation:
            current_pos = np.array(observation["end_effector_pos"][:3])
            target = np.array(self.target_position[:3])
            error = np.linalg.norm(current_pos - target)
            if error < self._position_threshold:
                return True

        if "distance_to_target" in observation:
            distance = observation["distance_to_target"]
            if distance < self._position_threshold:
                return True

        if observation.get("placement_success", False):
            return True

        return False

    def get_target_position(self) -> List[float]:
        """获取目标位置"""
        return self.target_position
