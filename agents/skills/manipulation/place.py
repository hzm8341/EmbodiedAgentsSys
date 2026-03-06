# agents/skills/manipulation/place.py
"""PlaceSkill 放置技能

VLA 驱动的物体放置技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List


class PlaceSkill(VLASkill):
    """放置技能

    用于将物体放置到指定位置。
    """

    required_inputs: List[str] = ["target_position", "observation"]
    produced_outputs: List[str] = ["success", "place_position"]
    max_steps: int = 50

    def __init__(self, target_position: List[float], **kwargs):
        """初始化放置技能

        Args:
            target_position: 目标位置 [x, y, z]
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.target_position = target_position

    def build_skill_token(self) -> str:
        """构建技能令牌"""
        return f"place at {self.target_position}"

    def check_preconditions(self, observation: Dict) -> bool:
        """检查执行前置条件

        物体必须已被抓取（在手中）
        """
        return observation.get("object_held", False)

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        放置成功（通过位置和力传感器判断）
        """
        return observation.get("placement_success", False)

    def get_target_position(self) -> List[float]:
        """获取目标位置"""
        return self.target_position
