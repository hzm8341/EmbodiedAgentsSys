"""机器人模型加载器"""

import os
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
        abs_path = Path(urdf_path).resolve()
        if not abs_path.exists():
            raise FileNotFoundError(f"URDF not found: {urdf_path}")

        old_cwd = os.getcwd()
        try:
            os.chdir(abs_path.parent)
            self._model = mujoco.MjModel.from_xml_path(str(abs_path))
            self._data = mujoco.MjData(self._model)
            self._joint_names = [
                mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, i)
                for i in range(self._model.njnt)
                if mujoco.mj_id2name(self._model, mujoco.mjtObj.mjOBJ_JOINT, i)
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to load URDF: {e}") from e
        finally:
            os.chdir(old_cwd)

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

        Raises:
            RuntimeError: 如果数据未初始化
        """
        if self._data is None:
            raise RuntimeError("Data not initialized")

        for name, value in positions.items():
            self._data.joint(name).qpos = value

    def get_joint_positions(self) -> dict[str, float]:
        """获取当前关节位置"""
        positions = {}
        for name in self._joint_names:
            positions[name] = self._data.joint(name).qpos
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