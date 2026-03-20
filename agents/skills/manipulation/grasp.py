# agents/skills/manipulation/grasp.py
"""GraspSkill 抓取技能

VLA 驱动的物体抓取技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List


class GraspSkill(VLASkill):
    """抓取技能

    用于抓取指定物体的技能。
    """

    required_inputs: List[str] = ["object_name", "observation"]
    produced_outputs: List[str] = ["success", "grasp_position"]
    max_steps: int = 50

    DEFAULT_CONTACT_THRESHOLD: float = 0.5

    def __init__(self, object_name: str, contact_threshold: float = None, **kwargs):
        """初始化抓取技能

        Args:
            object_name: 要抓取的物体名称
            contact_threshold: 接触力阈值 (N)
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.object_name = object_name
        self._contact_threshold = contact_threshold or self.DEFAULT_CONTACT_THRESHOLD

    def build_skill_token(self) -> str:
        """构建技能令牌"""
        return f"grasp(object={self.object_name})"

    def check_preconditions(self, observation: Dict) -> bool:
        """检查前置条件：目标物体已被检测到"""
        return bool(observation.get("object_detected", False))

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        抓取成功条件（满足任一即终止）：
        1. 夹爪力超过接触阈值
        2. 显式标记抓取成功
        """
        gripper_force = observation.get("gripper_force", 0.0)
        if gripper_force > self._contact_threshold:
            return True

        if observation.get("grasp_success", False):
            return True

        return False

    def get_grasp_position(self) -> Dict[str, float]:
        """获取抓取位置（子类可实现）"""
        return {"x": 0.0, "y": 0.0, "z": 0.0}
