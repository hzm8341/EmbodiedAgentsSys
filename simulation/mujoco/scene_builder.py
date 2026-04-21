"""MuJoCo 场景构建器"""

import mujoco
import numpy as np
from pathlib import Path
from typing import Optional, Tuple


# 工作台尺寸常量（用于物体位置对齐）
_TABLE_TOP_Z = 0.68   # 台面顶部 z 坐标（台面中心 0.34 + 半高 0.34）

# 场景中可抓取物体的初始位置（世界坐标系，放在工作台上）
GRASPABLE_OBJECTS = {
    "red_cube":     {"pos": [0.45,  0.12,  _TABLE_TOP_Z + 0.038], "size": [0.038, 0.038, 0.038], "type": mujoco.mjtGeom.mjGEOM_BOX,    "rgba": [0.85, 0.18, 0.18, 1], "mass": 0.12},
    "blue_block":   {"pos": [0.45, -0.12,  _TABLE_TOP_Z + 0.028], "size": [0.050, 0.036, 0.028], "type": mujoco.mjtGeom.mjGEOM_BOX,    "rgba": [0.18, 0.32, 0.85, 1], "mass": 0.15},
    "yellow_sphere":{"pos": [0.52,  0.0,   _TABLE_TOP_Z + 0.032], "size": [0.032, 0.032, 0.032], "type": mujoco.mjtGeom.mjGEOM_SPHERE,  "rgba": [0.90, 0.75, 0.10, 1], "mass": 0.08},
}


def build_robot_scene(urdf_path: str) -> Tuple[mujoco.MjModel, mujoco.MjData]:
    """使用 MjSpec 加载机器人 URDF 并附加场景元素。

    场景包含：
    - 蓝天背景 + 双光源
    - 棋盘格地面
    - 工作台
    - 3 个可抓取物体（red_cube / blue_block / yellow_sphere）

    Returns:
        (model, data) 元组
    """
    abs_path = str(Path(urdf_path).resolve())
    spec = mujoco.MjSpec.from_file(abs_path)

    # ── 视觉设置 ──────────────────────────────────────────────
    spec.visual.rgba.haze = [0.35, 0.55, 0.82, 1.0]   # 天空蓝色
    spec.visual.rgba.fog  = [0.35, 0.55, 0.82, 0.0]
    spec.visual.headlight.active   = 1
    spec.visual.headlight.diffuse  = [0.85, 0.85, 0.85]
    spec.visual.headlight.specular = [0.25, 0.25, 0.25]
    spec.visual.quality.shadowsize = 2048

    wb = spec.worldbody

    # ── 光源 ──────────────────────────────────────────────────
    sun = wb.add_light()
    sun.name = "sun"
    sun.type = mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
    sun.pos = [0, 0, 5]
    sun.dir = [0, 0.3, -1]
    sun.diffuse = [0.85, 0.85, 0.85]
    sun.specular = [0.25, 0.25, 0.25]
    sun.castshadow = True

    fill = wb.add_light()
    fill.name = "fill"
    fill.type = mujoco.mjtLightType.mjLIGHT_DIRECTIONAL
    fill.pos = [-2, -2, 3]
    fill.dir = [0.5, 0.5, -0.8]
    fill.diffuse = [0.35, 0.35, 0.35]
    fill.specular = [0.05, 0.05, 0.05]
    fill.castshadow = False

    # ── 地面（机器人底座固定在 z=0，地面与底座齐平） ────────
    floor = wb.add_geom()
    floor.name = "floor"
    floor.type = mujoco.mjtGeom.mjGEOM_PLANE
    floor.pos = [0, 0, 0]
    floor.size = [4, 4, 0.1]
    floor.rgba = [0.78, 0.78, 0.78, 1]
    floor.friction = [1.0, 0.005, 0.0001]
    floor.condim = 3

    # ── 工作台（底部贴地 z=0，台面顶部 z=0.68） ─────────────
    table = wb.add_geom()
    table.name = "table_top"
    table.type = mujoco.mjtGeom.mjGEOM_BOX
    table.pos = [0.45, 0.0, 0.34]   # center z=0.34 → bottom z=0, top z=0.68
    table.size = [0.28, 0.38, 0.34]
    table.rgba = [0.55, 0.38, 0.22, 1]
    table.friction = [0.8, 0.005, 0.0001]
    table.condim = 3

    # ── 基座标系（原点 + XYZ 轴，RGB = X/Y/Z 标准色） ─────────
    _AX_LEN = 0.18   # 轴长 18 cm
    _AX_R   = 0.005  # 轴半径 5 mm
    _Z_OFF  = 0.001  # 略高于地面，避免 z-fighting

    _ori = wb.add_geom()
    _ori.name        = "coord_origin"
    _ori.type        = mujoco.mjtGeom.mjGEOM_SPHERE
    _ori.pos         = [0, 0, _Z_OFF + 0.01]
    _ori.size        = [0.013, 0, 0]
    _ori.rgba        = [1.0, 1.0, 1.0, 1.0]
    _ori.contype     = 0
    _ori.conaffinity = 0

    _gx = wb.add_geom()
    _gx.name         = "coord_x"
    _gx.type         = mujoco.mjtGeom.mjGEOM_CYLINDER
    _gx.fromto       = [0.001, 0, _Z_OFF, _AX_LEN, 0, _Z_OFF]
    _gx.size         = [_AX_R, 0, 0]
    _gx.rgba         = [1.0, 0.12, 0.12, 1.0]
    _gx.contype      = 0
    _gx.conaffinity  = 0

    _gy = wb.add_geom()
    _gy.name         = "coord_y"
    _gy.type         = mujoco.mjtGeom.mjGEOM_CYLINDER
    _gy.fromto       = [0, 0.001, _Z_OFF, 0, _AX_LEN, _Z_OFF]
    _gy.size         = [_AX_R, 0, 0]
    _gy.rgba         = [0.12, 0.9, 0.12, 1.0]
    _gy.contype      = 0
    _gy.conaffinity  = 0

    _gz = wb.add_geom()
    _gz.name         = "coord_z"
    _gz.type         = mujoco.mjtGeom.mjGEOM_CYLINDER
    _gz.fromto       = [0, 0, _Z_OFF, 0, 0, _AX_LEN]
    _gz.size         = [_AX_R, 0, 0]
    _gz.rgba         = [0.12, 0.12, 1.0, 1.0]
    _gz.contype      = 0
    _gz.conaffinity  = 0

    # ── 可抓取物体（带 free joint） ───────────────────────────
    for obj_name, cfg in GRASPABLE_OBJECTS.items():
        body = wb.add_body()
        body.name = obj_name
        body.pos = cfg["pos"]

        fj = body.add_freejoint()
        fj.name = f"{obj_name}_free"

        geom = body.add_geom()
        geom.name = f"{obj_name}_geom"
        geom.type = cfg["type"]
        geom.size = cfg["size"]
        geom.rgba = cfg["rgba"]
        geom.mass = cfg["mass"]
        geom.friction = [1.2, 0.01, 0.001]
        geom.condim = 4

    model = spec.compile()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


class SceneBuilder:
    """MuJoCo 场景构建器（原有轻量版，保留向后兼容）"""

    def __init__(self, timestep: float = 0.002):
        self._timestep = timestep
        self._bodies = []
        self._ground = True
        self._ground_friction = (1.0, 0.005, 0.0001)
        self._model = None
        self._data = None

    def add_ground(self, friction: tuple = (1.0, 0.005, 0.0001)):
        self._ground = True
        self._ground_friction = friction
        return self

    def add_body(self, name, body_type, pos, size, rgba=(0.5, 0.5, 0.5, 1.0)):
        self._bodies.append({"name": name, "type": body_type, "pos": pos, "size": size, "rgba": rgba})
        return self

    def build(self):
        xml = self._generate_xml()
        self._model = mujoco.MjModel.from_xml_string(xml)
        self._data = mujoco.MjData(self._model)
        return self._model, self._data

    def _generate_xml(self):
        parts = ['<mujoco model="scene">',
                 '<compiler angle="radian" meshdir="."/>',
                 f'<option timestep="{self._timestep}"/>',
                 '<worldbody>']
        if self._ground:
            fr = self._ground_friction
            parts += [
                '<body name="ground" pos="0 0 0">',
                f'<geom type="plane" size="2 2 0.1" rgba="0.8 0.8 0.8 1" condim="3" friction="{fr[0]} {fr[1]} {fr[2]}"/>',
                '</body>'
            ]
        for b in self._bodies:
            pos_s = " ".join(map(str, b["pos"]))
            size_s = " ".join(map(str, b["size"]))
            rgba_s = " ".join(map(str, b["rgba"]))
            parts += [
                f'<body name="{b["name"]}" pos="{pos_s}">',
                f'<geom type="{b["type"]}" size="{size_s}" rgba="{rgba_s}"/>',
                '</body>'
            ]
        parts += ['</worldbody>', '</mujoco>']
        return "\n".join(parts)
