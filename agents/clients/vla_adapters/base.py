# agents/clients/vla_adapters/base.py
"""VLA 适配器基类"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np


class VLAAdapterBase(ABC):
    """VLA 适配器基类

    定义 VLA (Vision-Language-Action) 模型的标准接口。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 VLA 适配器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._initialized = False
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置参数"""
        pass  # 子类可以重写此方法进行验证

    @abstractmethod
    def reset(self) -> None:
        """重置 VLA 状态"""
        pass

    @abstractmethod
    def act(
        self,
        observation: Dict[str, Any],
        skill_token: str,
        termination: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """根据观察和技能令牌生成动作

        Args:
            observation: 当前观察数据
            skill_token: 技能描述/指令
            termination: 终止条件

        Returns:
            动作数组
        """
        pass

    @abstractmethod
    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作

        Args:
            action: 动作数组

        Returns:
            执行结果
        """
        pass

    @property
    @abstractmethod
    def action_dim(self) -> int:
        """动作维度"""
        pass
