"""机器人模型加载器"""

import mujoco
import numpy as np
from pathlib import Path
from typing import Optional


class RobotModel:
    """机器人模型管理器

    支持从 URDF 加载机器人模型，或创建空载进行测试。
    """

    def __init__(self, urdf_path: Optional[str] = None):
        """
        Args:
            urdf_path: URDF 文件路径。如果为 None，创建空载。
        """
        self._urdf_path = urdf_path
        self._model: Optional[mujoco.MjModel] = None
        self._data: Optional[mujoco.MjData] = None
        self._joint_names: list[str] = []

        if urdf_path:
            self.load_urdf(urdf_path)
        else:
            self._create_empty_robot()

    def load_urdf(self, urdf_path: str) -> None:
        """从 URDF 文件加载机器人

        Args:
            urdf_path: URDF 文件路径

        Raises:
            FileNotFoundError: 如果文件不存在
            RuntimeError: 如果加载失败
        """
        if not Path(urdf_path).exists():
            raise FileNotFoundError(f"URDF not found: {urdf_path}")

        try:
            self._model = mujoco.MjModel.from_xml_path(urdf_path)
            self._data = mujoco.MjData(self._model)
            self._joint_names = [name for name in self._model.names if name]
        except Exception as e:
            raise RuntimeError(f"Failed to load URDF: {e}")

    def _create_empty_robot(self) -> None:
        """创建空载（用于测试）"""
        xml = """
        <mujoco model="empty_robot">
            <worldbody>
                <body name="base" pos="0 0 0">
                    <joint name="base_joint" type="free"/>
                    <geom type="box" size="0.05 0.05 0.1" rgba="0.5 0.5 0.8 1"/>
                </body>
            </worldbody>
        </mujoco>
        """
        self._model = mujoco.MjModel.from_xml_string(xml)
        self._data = mujoco.MjData(self._model)
        self._joint_names = []

    def get_model(self) -> mujoco.MjModel:
        """获取模型"""
        if self._model is None:
            raise RuntimeError("Model not loaded")
        return self._model

    def get_data(self) -> mujoco.MjData:
        """获取数据"""
        if self._data is None:
            raise RuntimeError("Data not initialized")
        return self._data

    def get_joint_names(self) -> list[str]:
        """获取关节名称列表"""
        return list(self._joint_names)

    def set_joint_positions(self, positions: dict[str, float]) -> None:
        """设置关节位置

        Args:
            positions: 字典，key 为关节名，value 为目标位置（弧度或米）
        """
        if self._data is None:
            return

        for name, value in positions.items():
            joint_id = self._model.name2id(name, "joint")
            self._data.joint(name).qpos = value

    def get_joint_positions(self) -> dict[str, float]:
        """获取当前关节位置"""
        positions = {}
        for name in self._joint_names:
            try:
                positions[name] = self._data.joint(name).qpos
            except Exception:
                pass
        return positions

    def get_base_position(self) -> np.ndarray:
        """获取基座位置"""
        if self._data is None:
            return np.zeros(3)
        return self._data.body("base").xpos.copy()

    def forward(self) -> None:
        """执行前向动力学"""
        if self._data is not None:
            mujoco.mj_forward(self._model, self._data)