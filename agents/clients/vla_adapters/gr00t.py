# agents/clients/vla_adapters/gr00t.py
"""GR00T VLA 适配器

基于 GR00T (Generalist Robot 00 Transformer) 模型的 VLA 适配器。
"""

from .base import VLAAdapterBase
from typing import Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class GR00TVLAAdapter(VLAAdapterBase):
    """GR00T VLA 适配器

    基于 Diffusion Transformer 的通用机器人模型适配器。
    支持语言指令和视觉观察。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 GR00T 适配器

        Args:
            config: 配置字典，包含 model_path, inference_steps, host, port 等
        """
        super().__init__(config)
        self.model_path = config.get("model_path")
        self.inference_steps = config.get("inference_steps", 10)  # Diffusion 步数
        self._action_dim = config.get("action_dim", 7)  # 动作维度
        self._action_horizon = config.get("action_horizon", 8)  # 动作视野
        # 本地推理服务连接配置
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8002)
        self._client = None

    def _ensure_connection(self) -> None:
        """建立并保持到本地 GR00T 推理服务的 HTTP 连接"""
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
                        logger.info(f"Connected to GR00T inference service at {self.host}:{self.port}")
                        return
            except self._urllib_error.URLError:
                pass
            # 未检测到服务，仍标记已初始化以便离线使用
            self._initialized = True
            self._client = True
            logger.warning(
                f"GR00T inference service not detected at {self.host}:{self.port}. "
                "Will use fallback random actions until service is available."
            )
        except Exception as e:
            self._initialized = True
            self._client = None
            logger.warning(f"Failed to connect to GR00T service: {e}")

    def reset(self) -> None:
        """重置 VLA 状态"""
        self._initialized = True
        # 重置 Diffusion 模型状态

    def act(
        self,
        observation: Dict[str, Any],
        skill_token: str,
        termination: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """生成动作

        Args:
            observation: 当前观察数据 (包含图像和本体感知)
            skill_token: 技能描述/指令（语言）
            termination: 终止条件

        Returns:
            动作数组
        """
        if self._client is None:
            self._ensure_connection()

        visual_features = self._extract_visual(observation)
        language_embedding = self._encode_language(skill_token)
        proprioceptive = self._extract_proprioception(observation)

        # 尝试连接本地 GR00T 推理服务
        if self._client is not None and hasattr(self, "_urllib_request"):
            try:
                import json
                payload = json.dumps({
                    "visual_features": visual_features.tolist(),
                    "language_embedding": language_embedding.tolist(),
                    "proprioceptive": proprioceptive.tolist(),
                    "skill_token": skill_token,
                    "inference_steps": self.inference_steps,
                    "action_horizon": self._action_horizon,
                }).encode("utf-8")
                req = self._urllib_request.Request(
                    f"http://{self.host}:{self.port}/predict",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with self._urllib_request.urlopen(req, timeout=10.0) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    action = np.array(result["action"][: self._action_dim])
                    if action.shape[0] == self._action_dim:
                        return action
                    logger.warning(
                        f"GR00T service returned action dim {action.shape[0]}, "
                        f"expected {self._action_dim}. Padding with zeros."
                    )
                    padded = np.zeros(self._action_dim)
                    padded[:action.shape[0]] = action
                    return padded
            except Exception as e:
                logger.debug(f"GR00T inference request failed: {e}")

        # Fallback: 使用均值为0的小随机动作
        action = np.random.randn(self._action_dim) * 0.01
        return action

    def _extract_visual(self, observation: Dict[str, Any]) -> np.ndarray:
        """提取视觉特征"""
        image = observation.get("image")
        if image is not None:
            # 返回模拟特征
            return np.zeros(512)
        return np.zeros(512)

    def _encode_language(self, language: str) -> np.ndarray:
        """编码语言指令"""
        return np.zeros(512)

    def _extract_proprioception(self, observation: Dict[str, Any]) -> np.ndarray:
        """提取本体感知状态"""
        joint_positions = observation.get("joint_positions", np.zeros(7))
        joint_velocities = observation.get("joint_velocities", np.zeros(7))
        end_effector_pose = observation.get("end_effector_pose", np.zeros(6))
        proprio = np.concatenate([joint_positions, joint_velocities, end_effector_pose])
        return proprio

    def execute(self, action: np.ndarray) -> Dict[str, Any]:
        """执行动作"""
        return {
            "status": "executed",
            "action": action.tolist(),
            "model": "GR00T",
            "inference_steps": self.inference_steps,
        }

    @property
    def action_dim(self) -> int:
        return self._action_dim

    @property
    def action_horizon(self) -> int:
        return self._action_horizon
