# agents/skills/manipulation/inspect.py
"""InspectSkill 检查技能

VLA 驱动的物体检查/识别技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List, Optional


class InspectSkill(VLASkill):
    """检查技能

    用于检查/识别物体、验证任务执行结果。
    """

    required_inputs: List[str] = ["observation"]
    produced_outputs: List[str] = ["detections", "inspections"]
    max_steps: int = 20

    def __init__(
        self,
        target_object: Optional[str] = None,
        inspection_type: str = "detect",
        **kwargs
    ):
        """初始化检查技能

        Args:
            target_object: 目标物体名称（可选）
            inspection_type: 检查类型 (detect/verify/quality)
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.target_object = target_object
        self.inspection_type = inspection_type

    def build_skill_token(self) -> str:
        """构建技能令牌"""
        if self.target_object:
            return f"inspect(object={self.target_object}, type={self.inspection_type})"
        return f"inspect(type={self.inspection_type})"

    def check_preconditions(self, observation: Dict) -> bool:
        """检查执行前置条件

        视觉系统可用
        """
        # 检查是否有视觉输入
        has_vision = any(
            key in observation
            for key in ["image", "rgb", "depth", "point_cloud"]
        )
        return has_vision

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        检查完成（检测到目标或超时）
        """
        # 方式1: 检查完成标志
        if "inspection_complete" in observation:
            return observation["inspection_complete"]

        # 方式2: 检测到目标物体
        if self.target_object and "detections" in observation:
            detections = observation["detections"]
            return any(
                d.get("class") == self.target_object
                for d in detections
            )

        # 方式3: 超时
        return False

    def get_detections(self, observation: Dict) -> List[Dict]:
        """从观察中获取检测结果"""
        return observation.get("detections", [])

    def verify_object(self, observation: Dict, object_class: str) -> bool:
        """验证特定物体是否存在"""
        detections = self.get_detections(observation)
        return any(d.get("class") == object_class for d in detections)

    def get_inspection_result(self) -> Dict[str, Any]:
        """获取检查结果"""
        return {
            "type": self.inspection_type,
            "target": self.target_object,
            "status": "completed"
        }
