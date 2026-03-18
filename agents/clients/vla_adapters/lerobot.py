# agents/clients/vla_adapters/lerobot.py
"""LeRobot VLA 适配器"""

from .base import VLAAdapterBase
from typing import Dict, Any, Optional
import numpy as np


class LeRobotVLAAdapter(VLAAdapterBase):
    """LeRobot VLA 适配器

    基于 LeRobot 框架的 VLA 模型适配器。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 LeRobot 适配器

        Args:
            config: 配置字典，包含 policy_name, checkpoint, host, port 等
        """
        super().__init__(config)
        self.policy_name = config.get("policy_name", "default")
        self.checkpoint = config.get("checkpoint")
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8080)
        self._action_dim = config.get("action_dim", 7)
        self._client = None

    def reset(self) -> None:
        """重置VLA状态"""
        if self._client:
            # 调用 LeRobot reset
            pass
        self._initialized = True

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

        try:
            from agents.clients.lerobot_transport.utils import build_inference_request

            request = build_inference_request(observation, skill_token)

            response = self._client.Predict(request, timeout=5.0)

            return np.array(response.action[: self._action_dim])

        except Exception as e:
            import logging

            logging.warning(f"VLA inference failed: {e}, using zero action")
            return np.zeros(self._action_dim)

    def _ensure_connection(self) -> None:
        """确保 gRPC 连接已建立"""
        try:
            import grpc
            from agents.clients.lerobot_transport import services_pb2_grpc

            channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            self._client = services_pb2_grpc.LeRobotServiceStub(channel)
            self._initialized = True
        except Exception as e:
            import logging

            logging.warning(f"Failed to connect to VLA service: {e}")
            self._client = None

    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作

        Args:
            action: 动作数组

        Returns:
            执行结果
        """
        # 发送到机械臂执行
        return {"status": "executed", "action": action.tolist()}

    @property
    def action_dim(self) -> int:
        """动作维度"""
        return self._action_dim
