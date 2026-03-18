# agents/skills/vla_skill.py
"""VLA Skill 基类

基于 VLA (Vision-Language-Action) 的 Skill 抽象基类。
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class SkillStatus(Enum):
    """技能执行状态"""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class SkillResult:
    """技能执行结果"""

    status: SkillStatus
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VLASkill(ABC):
    """基于 VLA 的 Skill 抽象基类

    定义了 VLA 驱动技能的标准接口和行为。
    """

    required_inputs: List[str] = []
    produced_outputs: List[str] = []
    default_vla: Optional[str] = None
    max_steps: int = 100

    def __init__(self, vla_adapter=None, ros_node=None, **kwargs):
        """初始化 VLASkill

        Args:
            vla_adapter: VLA 适配器实例
            ros_node: ROS2 节点实例（可选）
            **kwargs: 其他配置参数
        """
        self.vla = vla_adapter
        self._node = ros_node
        self._status = SkillStatus.IDLE
        self._config = kwargs

        self._latest_joint_state = None
        self._latest_image = None
        self._gripper_force = 0.0

        self._setup_subscribers()

    def _setup_subscribers(self) -> None:
        """设置 ROS2 话题订阅"""
        if self._node is None:
            return

        try:
            from sensor_msgs.msg import JointState, Image

            self._node.create_subscription(
                JointState, "/joint_states", self._on_joint_state, 10
            )
            self._node.create_subscription(
                Image, "/camera/color/image_raw", self._on_image, 1
            )
        except ImportError:
            pass

    def _on_joint_state(self, msg) -> None:
        """处理关节状态消息"""
        self._latest_joint_state = msg

    def _on_image(self, msg) -> None:
        """处理图像消息"""
        self._latest_image = msg

    @abstractmethod
    def build_skill_token(self) -> str:
        """构建 VLA 推理用的任务描述

        Returns:
            技能令牌字符串
        """
        pass

    @abstractmethod
    def check_preconditions(self, observation: Dict) -> bool:
        """检查执行前置条件

        Args:
            observation: 当前观察数据

        Returns:
            是否满足前置条件
        """
        pass

    @abstractmethod
    def check_termination(self, observation: Dict) -> bool:
        """检查是否满足终止条件

        Args:
            observation: 当前观察数据

        Returns:
            是否应该终止
        """
        pass

    async def execute(self, observation: Dict) -> SkillResult:
        """执行 Skill（异步封装同步逻辑）

        Args:
            observation: 当前观察数据

        Returns:
            技能执行结果
        """
        self._status = SkillStatus.RUNNING

        try:
            # 检查前置条件
            if not self.check_preconditions(observation):
                return SkillResult(
                    status=SkillStatus.FAILED, error="Preconditions not met"
                )

            skill_token = self.build_skill_token()

            for step in range(self.max_steps):
                # 检查终止条件
                if self.check_termination(observation):
                    return SkillResult(
                        status=SkillStatus.SUCCESS, output={"steps": step + 1}
                    )

                # VLA 推理
                action = self.vla.act(observation, skill_token)

                # 执行动作
                result = self.vla.execute(action)

                # 更新观察（需要子类实现）
                observation = await self._get_observation()

                # 添加延迟避免过快执行
                await asyncio.sleep(0.01)

            return SkillResult(
                status=SkillStatus.SUCCESS, output={"steps": self.max_steps}
            )

        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(status=SkillStatus.FAILED, error=str(e))

    async def _get_observation(self) -> Dict:
        """获取观察数据（从 ROS2 话题）"""
        obs = {}

        if self._latest_joint_state:
            obs["joint_positions"] = list(self._latest_joint_state.position)
            obs["joint_velocities"] = list(self._latest_joint_state.velocity)

        if self._latest_image:
            obs["image"] = self._latest_image

        obs["gripper_force"] = self._gripper_force

        return obs

    def get_joint_positions(self) -> np.ndarray:
        """获取当前关节位置"""
        if self._latest_joint_state and self._latest_joint_state.position:
            return np.array(list(self._latest_joint_state.position))
        return np.zeros(7)

    def get_end_effector_pose(self) -> np.ndarray:
        """获取末端位姿"""
        joints = self.get_joint_positions()
        x = joints[0] * 0.3
        y = joints[1] * 0.3
        z = joints[2] * 0.3 + 0.2
        return np.array([x, y, z, 0.0, 0.0, 0.0])

    @property
    def status(self) -> SkillStatus:
        """获取当前状态"""
        return self._status

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._status == SkillStatus.RUNNING

    @property
    def is_idle(self) -> bool:
        """是否空闲"""
        return self._status == SkillStatus.IDLE
