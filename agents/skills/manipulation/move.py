# agents/skills/manipulation/move.py
"""MoveSkill 关节运动技能

VLA 驱动的机械臂关节运动技能。
"""

from ..vla_skill import VLASkill, SkillResult, SkillStatus
from typing import Dict, Any, List, Optional


class MoveSkill(VLASkill):
    """关节运动技能

    用于控制机械臂关节运动到指定位置或姿态。
    """

    required_inputs: List[str] = ["target_joints", "observation"]
    produced_outputs: List[str] = ["success", "actual_joints"]
    max_steps: int = 30
    joint_threshold: float = 0.01  # 关节误差阈值 (rad)

    def __init__(
        self,
        target_joints: Optional[List[float]] = None,
        target_pose: Optional[List[float]] = None,
        **kwargs
    ):
        """初始化关节运动技能

        Args:
            target_joints: 目标关节角度 [j1, j2, ..., jn]
            target_pose: 目标末端位姿 [x, y, z, roll, pitch, yaw]
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self.target_joints = target_joints
        self.target_pose = target_pose
        self.joint_threshold = kwargs.get("joint_threshold", self.joint_threshold)

    def build_skill_token(self) -> str:
        """构建技能令牌"""
        if self.target_joints:
            return f"move(joints={self.target_joints})"
        elif self.target_pose:
            return f"move(pose={self.target_pose})"
        return "move()"

    def check_preconditions(self, observation: Dict) -> bool:
        """检查执行前置条件

        机械臂必须处于安全状态（无碰撞）
        """
        if "collision_detected" in observation:
            return not observation["collision_detected"]
        return True

    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        到达目标关节角度或末端位姿
        """
        # 方式1: 直接检查 position_reached 标志
        if "position_reached" in observation:
            return observation["position_reached"]

        # 方式2: 通过关节误差判断
        if "joint_error" in observation:
            return observation["joint_error"] < self.joint_threshold

        # 方式3: 通过末端位置误差判断
        if "pose_error" in observation:
            return observation["pose_error"] < 0.005  # 5mm

        return False

    def get_target_joints(self) -> Optional[List[float]]:
        """获取目标关节角度"""
        return self.target_joints

    def get_target_pose(self) -> Optional[List[float]]:
        """获取目标末端位姿"""
        return self.target_pose

    def set_joint_threshold(self, threshold: float) -> None:
        """设置关节误差阈值"""
        self.joint_threshold = threshold
