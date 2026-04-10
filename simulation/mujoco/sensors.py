"""传感器接口 - 力觉和接触检测"""

import mujoco
import numpy as np
from typing import Optional, List


class ForceSensor:
    """力觉传感器

    获取末端执行器的力/力矩数据。
    """

    def __init__(self, model: Optional[mujoco.MjModel] = None, data: Optional[mujoco.MjData] = None):
        """
        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据
        """
        self._model = model
        self._data = data
        self._sensor_id: Optional[int] = None

    def attach_to_body(self, body_name: str, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        """附加到指定 body

        Args:
            body_name: body 名称
            model: MuJoCo 模型
            data: MuJoCo 数据
        """
        self._model = model
        self._data = data
        try:
            self._sensor_id = model.name2id(body_name, "body")
        except Exception:
            self._sensor_id = None

    def get_force_torque(self) -> dict:
        """获取力/力矩

        Returns:
            dict: {
                "force": [Fx, Fy, Fz],  # 牛顿
                "torque": [Mx, My, Mz],  # 牛米
            }
        """
        if self._data is None:
            return {"force": np.zeros(3), "torque": np.zeros(3)}

        # 获取末端执行器力/力矩
        # 从 cfrc_ext 获取 body 上的外部合力/力矩 (wrench)
        wrench = np.zeros(6)
        if self._sensor_id is not None:
            # 从 cfrc_ext 获取外部力
            wrench = self._data.cfrc_ext[self._sensor_id]

        return {
            "force": wrench[:3].copy(),
            "torque": wrench[3:].copy(),
        }

    def get_joint_torques(self) -> np.ndarray:
        """获取关节力矩"""
        if self._data is None:
            return np.zeros(6)
        return self._data.qfrc_actuator.copy()


class ContactSensor:
    """接触传感器

    获取接触点位置、法向量、力大小等信息。
    """

    def __init__(self, model: Optional[mujoco.MjModel] = None, data: Optional[mujoco.MjData] = None):
        """
        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据
        """
        self._model = model
        self._data = data

    def attach(self, model: mujoco.MjModel, data: mujoco.MjData) -> None:
        """附加到仿真

        Args:
            model: MuJoCo 模型
            data: MuJoCo 数据
        """
        self._model = model
        self._data = data

    def get_contacts(self) -> List[dict]:
        """获取当前接触点列表

        Returns:
            List[dict]: 每个接触点的信息
                - position: [x, y, z] 接触点位置
                - normal: [nx, ny, nz] 接触法向量
                - force: 力大小
                - geom1: 几何体1 ID
                - geom2: 几何体2 ID
        """
        if self._data is None:
            return []

        contacts = []
        for i in range(self._data.ncon):
            contact = self._data.contact[i]
            if contact.dist >= 0:  # 有效接触 (dist >= 0 表示几何体重叠)
                contacts.append({
                    "position": contact.pos.copy(),
                    "normal": contact.frame[:3].reshape(3, 3)[:, 0].copy(),  # first column = normal
                    "force": np.linalg.norm(contact.force),
                    "geom1": contact.geom1,
                    "geom2": contact.geom2,
                })

        return contacts

    def has_contact(self, geom_name: Optional[str] = None) -> bool:
        """检查是否有接触

        Args:
            geom_name: 可选，指定几何体名称

        Returns:
            bool: 是否有接触
        """
        contacts = self.get_contacts()
        if geom_name is None:
            return len(contacts) > 0

        if self._model is None:
            return False

        try:
            geom_id = self._model.name2id(geom_name, "geom")
            return any(c["geom1"] == geom_id or c["geom2"] == geom_id for c in contacts)
        except Exception:
            return False