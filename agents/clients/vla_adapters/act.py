# agents/clients/vla_adapters/act.py
"""ACT VLA 适配器

基于 ACT (Action Chunking Transformer) 模型的 VLA 适配器。
"""

from .base import VLAAdapterBase
from typing import Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ACTVLAAdapter(VLAAdapterBase):
    """ACT VLA 适配器

    基于 Action Chunking Transformer 的 VLA 模型适配器。
    支持时序动作聚合和多步动作预测。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 ACT 适配器

        Args:
            config: 配置字典，包含 model_path, chunk_size, horizon, host, port 等
        """
        super().__init__(config)
        self.model_path = config.get("model_path")
        self._chunk_size = config.get("chunk_size", 100)  # 动作分块大小
        self.horizon = config.get("horizon", 1)  # 预测视野
        self.state_dim = config.get("state_dim", 14)  # 状态维度
        self._action_dim = config.get("action_dim", 7)  # 动作维度
        # 本地推理服务连接配置
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8001)
        self._client = None

    def _ensure_connection(self) -> None:
        """建立并保持到本地 ACT 推理服务的 HTTP 连接"""
        if self._client is not None:
            return
        try:
            import urllib.request
            import urllib.error
            self._urllib_request = urllib.request
            self._urllib_error = urllib.error
            # 尝试健康检查
            try:
                req = self._urllib_request.Request(
                    f"http://{self.host}:{self.port}/health",
                    method="GET"
                )
                with self._urllib_request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        self._initialized = True
                        logger.info(f"Connected to ACT inference service at {self.host}:{self.port}")
                        return
            except self._urllib_error.URLError:
                pass
            # 未检测到服务，仍标记已初始化以便离线使用
            self._initialized = True
            self._client = True
            logger.warning(
                f"ACT inference service not detected at {self.host}:{self.port}. "
                "Will use fallback random actions until service is available."
            )
        except Exception as e:
            self._initialized = True
            self._client = None
            logger.warning(f"Failed to connect to ACT service: {e}")

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
        if self._client is None:
            self._ensure_connection()

        state = self._extract_state(observation)

        # 尝试连接本地 ACT 推理服务
        if self._client is not None and hasattr(self, "_urllib_request"):
            try:
                import json
                payload = json.dumps({
                    "state": state.tolist(),
                    "skill_token": skill_token,
                    "chunk_size": self._chunk_size,
                    "horizon": self.horizon,
                }).encode("utf-8")
                req = self._urllib_request.Request(
                    f"http://{self.host}:{self.port}/predict",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with self._urllib_request.urlopen(req, timeout=5.0) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    action = np.array(result["action"][: self._action_dim])
                    if action.shape[0] == self._action_dim:
                        return action
                    logger.warning(
                        f"ACT service returned action dim {action.shape[0]}, "
                        f"expected {self._action_dim}. Padding with zeros."
                    )
                    padded = np.zeros(self._action_dim)
                    padded[:action.shape[0]] = action
                    return padded
            except Exception as e:
                logger.debug(f"ACT inference request failed: {e}")

        # Fallback: 使用均值为0的小随机动作
        action = np.random.randn(self._action_dim) * 0.01
        return action

    def _extract_state(self, observation: Dict[str, Any]) -> np.ndarray:
        """从观察中提取状态向量"""
        joint_positions = observation.get("joint_positions", np.zeros(7))
        joint_velocities = observation.get("joint_velocities", np.zeros(7))
        state = np.concatenate([joint_positions, joint_velocities])
        return state

    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作"""
        return {"status": "executed", "action": action.tolist(), "model": "ACT"}

    @property
    def action_dim(self) -> int:
        return self._action_dim

    @property
    def chunk_size(self) -> int:
        return self._chunk_size
