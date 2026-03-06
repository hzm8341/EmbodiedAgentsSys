# skills/force_control/force_control.py
"""Force Control Module

力控模块，提供机械臂柔顺控制功能。
"""

from enum import Enum
from typing import Optional
import numpy as np


class ForceControlMode(Enum):
    """力控模式"""
    POSITION = "position"      # 位置模式
    FORCE = "force"           # 力控模式
    HYBRID = "hybrid"         # 位置/力混合模式
    COMPLIANCE = "compliance"  # 柔顺模式


class ForceController:
    """力控制器

    提供机械臂末端力控功能，支持多种控制模式。
    """

    def __init__(
        self,
        max_force: float = 10.0,
        contact_threshold: float = 0.5,
        stiffness: float = 500.0
    ):
        """初始化力控制器

        Args:
            max_force: 最大允许力 (N)
            contact_threshold: 接触检测阈值 (N)
            stiffness: 刚度 (N/m)
        """
        self.max_force = max_force
        self.contact_threshold = contact_threshold
        self.stiffness = stiffness
        self._mode = ForceControlMode.POSITION
        self._current_force = np.zeros(6)  # 6轴力/力矩

    @property
    def mode(self) -> ForceControlMode:
        """获取当前模式"""
        return self._mode

    def set_mode(self, mode: ForceControlMode) -> None:
        """设置控制模式"""
        self._mode = mode

    def apply_force(self, target_force: np.ndarray) -> bool:
        """施加目标力

        Args:
            target_force: 目标力向量 [Fx, Fy, Fz, Mx, My, Mz]

        Returns:
            是否成功
        """
        # 限制力大小
        clamped_force = self.clamp_force(target_force)
        self._current_force = clamped_force
        return True

    def clamp_force(self, force: np.ndarray) -> np.ndarray:
        """限制力大小

        Args:
            force: 输入力向量

        Returns:
            限制后的力向量
        """
        force_magnitude = np.linalg.norm(force[:3])  # 只考虑力，不考虑力矩

        if force_magnitude > self.max_force:
            scale = self.max_force / force_magnitude
            force[:3] *= scale

        return force

    def read_force_sensor(self, raw_data: np.ndarray) -> np.ndarray:
        """读取力传感器数据

        Args:
            raw_data: 原始传感器数据

        Returns:
            处理后的力数据
        """
        # 简单的滤波处理
        filtered = 0.9 * self._current_force + 0.1 * raw_data
        self._current_force = filtered
        return filtered

    def detect_contact(self, force: np.ndarray) -> bool:
        """检测是否接触

        Args:
            force: 力向量

        Returns:
            是否检测到接触
        """
        force_magnitude = np.linalg.norm(force[:3])
        return force_magnitude > self.contact_threshold

    def compute_compliance(self, force: np.ndarray) -> np.ndarray:
        """计算柔顺补偿

        基于力计算位置补偿，实现力柔顺控制。

        Args:
            force: 当前力

        Returns:
            位置补偿量
        """
        # 简化的柔顺控制：F = k * x => x = F / k
        displacement = force[:3] / self.stiffness
        return displacement

    async def execute(self, target_force: np.ndarray) -> dict:
        """异步执行力控

        Args:
            target_force: 目标力

        Returns:
            执行结果
        """
        # 检测接触
        if self.detect_contact(self._current_force):
            # 检测到接触，切换到柔顺模式
            self.set_mode(ForceControlMode.COMPLIANCE)

            # 计算补偿
            displacement = self.compute_compliance(self._current_force)

            return {
                "status": "contact",
                "displacement": displacement.tolist(),
                "mode": self._mode.value
            }

        # 施加目标力
        self.apply_force(target_force)

        return {
            "status": "applied",
            "force": self._current_force.tolist(),
            "mode": self._mode.value
        }
