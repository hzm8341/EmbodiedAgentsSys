"""MuJoCo 场景构建器"""

import mujoco
import numpy as np
from typing import Optional


class SceneBuilder:
    """MuJoCo 场景构建器

    用于创建和管理 MuJoCo 仿真场景。
    """

    def __init__(self, timestep: float = 0.002):
        """
        Args:
            timestep: 仿真时间步 (秒)
        """
        self._timestep = timestep
        self._bodies = []  # [(name, type, pos, size, rgba)]
        self._ground = True
        self._ground_friction = (1.0, 0.005, 0.0001)
        self._model = None
        self._data = None

    def add_ground(self, friction: tuple = (1.0, 0.005, 0.0001)):
        """添加地面

        Args:
            friction: (sliding, torsional, rolling) 摩擦系数
        """
        self._ground = True
        self._ground_friction = friction
        return self

    def add_body(
        self,
        name: str,
        body_type: str,
        pos: tuple,
        size: tuple,
        rgba: tuple = (0.5, 0.5, 0.5, 1.0),
    ):
        """添加几何体

        Args:
            name: 物体名称（唯一）
            body_type: 类型 (box, sphere, cylinder, capsule)
            pos: 位置 (x, y, z)
            size: 尺寸 (根据类型不同含义不同)
            rgba: 颜色和透明度
        """
        self._bodies.append({
            "name": name,
            "type": body_type,
            "pos": pos,
            "size": size,
            "rgba": rgba,
        })
        return self

    def build(self) -> tuple:
        """构建场景

        Returns:
            (model, data) 元组
        """
        # 生成 MJCF XML 字符串
        xml = self._generate_xml()

        # 加载模型和数据
        self._model = mujoco.MjModel.from_xml_string(xml)
        self._data = mujoco.MjData(self._model)

        return self._model, self._data

    def _generate_xml(self) -> str:
        """生成 MJCF XML"""
        parts = ['<mujoco model="scene">']

        # Compiler
        parts.append('<compiler angle="radian" meshdir="."/>')

        # Option
        parts.append(f'<option timestep="{self._timestep}"/>')

        # Worldbody
        parts.append('<worldbody>')

        # 地面
        if self._ground:
            parts.append('<body name="ground" pos="0 0 0">')
            friction_str = f"{self._ground_friction[0]} {self._ground_friction[1]} {self._ground_friction[2]}"
            parts.append(f'<geom type="plane" size="2 2 0.1" rgba="0.8 0.8 0.8 1" condim="3" friction="{friction_str}"/>')
            parts.append('</body>')

        # 几何体
        for body in self._bodies:
            parts.append(f'<body name="{body["name"]}" pos="{" ".join(map(str, body["pos"]))}">')
            geom_type = body["type"]
            size_str = " ".join(map(str, body["size"]))
            rgba_str = " ".join(map(str, body["rgba"]))
            parts.append(f'<geom type="{geom_type}" size="{size_str}" rgba="{rgba_str}"/>')
            parts.append('</body>')

        parts.append('</worldbody>')
        parts.append('</mujoco>')

        return "\n".join(parts)