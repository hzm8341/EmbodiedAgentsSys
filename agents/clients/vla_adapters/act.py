# agents/clients/vla_adapters/act.py
"""ACT VLA 适配器

基于 ACT (Action Chunking Transformer) 模型的 VLA 适配器。
"""

from .base import VLAAdapterBase
from typing import Dict, Any, Optional
import numpy as np


class ACTVLAAdapter(VLAAdapterBase):
    """ACT VLA 适配器

    基于 Action Chunking Transformer 的 VLA 模型适配器。
    支持时序动作聚合和多步动作预测。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 ACT 适配器

        Args:
            config: 配置字典，包含 model_path, chunk_size, horizon 等
        """
        super().__init__(config)
        self.model_path = config.get("model_path")
        self.chunk_size = config.get("chunk_size", 100)  # 动作分块大小
        self.horizon = config.get("horizon", 1)  # 预测视野
        self.state_dim = config.get("state_dim", 14)  # 状态维度
        self.action_dim = config.get("action_dim", 7)  # 动作维度
        self._model = None

    def reset(self) -> None:
        """重置 VLA 状态"""
        self._initialized = True
        # 重置模型状态

    def act(
        self,
        observation: Dict[str, Any],
        skill_token: str,
        termination: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """生成动作

        Args:
            observation: 当前观察数据
            skill_token: 技能描述/指令
            termination: 终止条件

        Returns:
            动作数组
        """
        state = self._extract_state(observation)

        # TODO: Connect to local ACT inference service
        # Replace with: action = self._model.predict(state, skill_token)

        # Placeholder: return small random action to simulate real inference
        action = np.random.randn(self.action_dim) * 0.01

        return action

    def _extract_state(self, observation: Dict[str, Any]) -> np.ndarray:
        """从观察中提取状态向量"""
        # 提取关节位置
        joint_positions = observation.get("joint_positions", np.zeros(7))
        # 提取关节速度
        joint_velocities = observation.get("joint_velocities", np.zeros(7))

        # 拼接状态
        state = np.concatenate([joint_positions, joint_velocities])
        return state

    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作

        Args:
            action: 动作数组

        Returns:
            执行结果
        """
        return {"status": "executed", "action": action.tolist(), "model": "ACT"}

    @property
    def action_dim(self) -> int:
        """动作维度"""
        return self._action_dim

    @property
    def chunk_size(self) -> int:
        """动作分块大小"""
        return self._chunk_size
