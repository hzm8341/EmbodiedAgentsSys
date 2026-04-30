:orphan:

# MuJoCo 仿真环境集成实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 MuJoCo 仿真驱动，支持基础运动控制和力觉反馈，与 HAL 接口对齐。

**Architecture:** 独立 `simulation/mujoco/` 模块，不继承 HAL BaseDriver，实现相同接口。包含 SceneBuilder（场景构建）、RobotModel（URDF 加载）、MuJoCoDriver（核心驱动）和 Sensors（传感器）。

**Tech Stack:** mujoco>=3.0.0, numpy, Python 3.10+

---

## 目录结构

```
embodiedagentsys/
├── hal/                          # 现有（不变）
│
└── simulation/                   # 新增
    └── mujoco/
        ├── __init__.py
        ├── mujoco_driver.py      # 核心驱动
        ├── scene_builder.py      # 场景构建
        ├── robot_model.py        # URDF 加载
        ├── sensors.py            # 力觉传感器
        └── config.py             # 配置常量
```

---

## Task 1: 创建模块基础结构

**Files:**
- Create: `simulation/__init__.py`
- Create: `simulation/mujoco/__init__.py`
- Create: `simulation/mujoco/config.py`

**Step 1: 创建仿真模块目录和基础文件**

```bash
mkdir -p simulation/mujoco
touch simulation/__init__.py
touch simulation/mujoco/__init__.py
```

**Step 2: 创建配置常量**

```python
# simulation/mujoco/config.py
"""MuJoCo 仿真配置常量"""

# 仿真参数
DEFAULT_TIMESTEP = 0.002  # 2ms, MuJoCo 推荐
DEFAULT_FRAME_SKIP = 1

# 物理参数
DEFAULT_GRAVITY = (0.0, 0.0, -9.81)
CONTACT_STIFFNESS = 1.0e4
CONTACT_DAMPING = 1.0e3

# 动作约束
POSITION_LIMIT = 2.0  # 工作空间半径 (m)
Z_HEIGHT_LIMIT = 1.5  # Z 轴最大高度 (m)
VELOCITY_LIMIT = 1.0  # 最大速度 (m/s)
FORCE_LIMIT = 100.0  # 最大力 (N)

# 场景参数
DEFAULT_SCENE = {
    "ground": True,
    "table_height": 0.0,
    "table_size": (1.0, 1.0),
}

# 传感器参数
FORCE_SENSOR_SIZE = 6  # Fx, Fy, Fz, Mx, My, Mz
CONTACT_SENSOR_SIZE = 100  # 最大接触点数
```

**Step 3: 提交**

```bash
git add simulation/
git commit -m "feat(simulation): add mujoco module base structure"
```

---

## Task 2: 实现 SceneBuilder（场景构建器）

**Files:**
- Create: `simulation/mujoco/scene_builder.py`
- Test: `tests/test_simulation/test_scene_builder.py`

**Step 1: 写失败测试**

```python
# tests/test_simulation/test_scene_builder.py
import pytest
from simulation.mujoco.scene_builder import SceneBuilder


class TestSceneBuilder:
    def test_create_empty_scene(self):
        """应该能创建空场景"""
        builder = SceneBuilder()
        assert builder is not None

    def test_add_ground(self):
        """应该能添加地面"""
        builder = SceneBuilder()
        builder.add_ground()
        model, data = builder.build()
        assert model is not None
        assert data is not None

    def test_add_box(self):
        """应该能添加方块"""
        builder = SceneBuilder()
        builder.add_body("box", "box", pos=(0, 0, 0.5), size=(0.1, 0.1, 0.1))
        model, data = builder.build()
        assert model is not None

    def test_build_returns_model_and_data(self):
        """build() 应返回 (model, data) 元组"""
        builder = SceneBuilder()
        result = builder.build()
        assert isinstance(result, tuple)
        assert len(result) == 2
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_simulation/test_scene_builder.py -v
```

**Step 3: 实现 SceneBuilder**

```python
# simulation/mujoco/scene_builder.py
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
        self._model = None
        self._data = None

    def add_ground(self, friction: tuple = (1.0, 0.005, 0.0001)):
        """添加地面

        Args:
            friction: (sliding, torsional, rolling) 摩擦系数
        """
        self._ground = True
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
            parts.append('<geom type="plane" size="2 2 0.1" rgba="0.8 0.8 0.8 1"/>')
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
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_simulation/test_scene_builder.py -v
```

**Step 5: 提交**

```bash
git add simulation/mujoco/scene_builder.py tests/test_simulation/test_scene_builder.py
git commit -m "feat(simulation): add SceneBuilder for MuJoCo scene creation"
```

---

## Task 3: 实现 RobotModel（URDF 加载）

**Files:**
- Create: `simulation/mujoco/robot_model.py`
- Test: `tests/test_simulation/test_robot_model.py`

**Step 1: 写失败测试**

```python
# tests/test_simulation/test_robot_model.py
import pytest
import os
from simulation.mujoco.robot_model import RobotModel


class TestRobotModel:
    def test_load_urdf(self):
        """应该能从 URDF 加载机器人模型"""
        # 注意：测试时需要模拟或不依赖真实 URDF
        model = RobotModel()
        assert model is not None

    def test_get_joint_names(self):
        """应该能获取关节名称"""
        model = RobotModel()
        joints = model.get_joint_names()
        assert isinstance(joints, list)

    def test_set_joint_positions(self):
        """应该能设置关节位置"""
        model = RobotModel()
        # 空模型测试
        model.set_joint_positions({})
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_simulation/test_robot_model.py -v
```

**Step 3: 实现 RobotModel（简化版，支持空载和 URDF）**

```python
# simulation/mujoco/robot_model.py
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
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_simulation/test_robot_model.py -v
```

**Step 5: 提交**

```bash
git add simulation/mujoco/robot_model.py tests/test_simulation/test_robot_model.py
git commit -m "feat(simulation): add RobotModel for URDF loading"
```

---

## Task 4: 实现 Sensors（力觉传感器）

**Files:**
- Create: `simulation/mujoco/sensors.py`
- Test: `tests/test_simulation/test_sensors.py`

**Step 1: 写失败测试**

```python
# tests/test_simulation/test_sensors.py
import pytest
import numpy as np
from simulation.mujoco.sensors import ForceSensor, ContactSensor


class TestForceSensor:
    def test_create_force_sensor(self):
        """应该能创建力传感器"""
        sensor = ForceSensor()
        assert sensor is not None

    def test_get_force_torque(self):
        """应该能获取力/力矩数据"""
        sensor = ForceSensor()
        ft = sensor.get_force_torque()
        assert isinstance(ft, dict)
        assert "force" in ft
        assert "torque" in ft
        assert len(ft["force"]) == 3
        assert len(ft["torque"]) == 3


class TestContactSensor:
    def test_create_contact_sensor(self):
        """应该能创建接触传感器"""
        sensor = ContactSensor()
        assert sensor is not None

    def test_get_contacts(self):
        """应该能获取接触点列表"""
        sensor = ContactSensor()
        contacts = sensor.get_contacts()
        assert isinstance(contacts, list)
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_simulation/test_sensors.py -v
```

**Step 3: 实现 Sensors**

```python
# simulation/mujoco/sensors.py
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
        # 这里简化处理，实际应该用 wrench 或专门的 sensor
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
            if contact.dist < 0:  # 有效接触
                contacts.append({
                    "position": contact.pos.copy(),
                    "normal": contact.frame[:3].copy(),  # 法向量
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
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_simulation/test_sensors.py -v
```

**Step 5: 提交**

```bash
git add simulation/mujoco/sensors.py tests/test_simulation/test_sensors.py
git commit -m "feat(simulation): add ForceSensor and ContactSensor"
```

---

## Task 5: 实现 MuJoCoDriver（核心驱动）

**Files:**
- Create: `simulation/mujoco/mujoco_driver.py`
- Test: `tests/test_simulation/test_mujoco_driver.py`

**Step 1: 写失败测试**

```python
# tests/test_simulation/test_mujoco_driver.py
import pytest
from simulation.mujoco.mujoco_driver import MuJoCoDriver
from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus


class TestMuJoCoDriver:
    def test_create_driver(self):
        """应该能创建驱动"""
        driver = MuJoCoDriver()
        assert driver is not None

    def test_execute_action_returns_receipt(self):
        """execute_action 应返回 ExecutionReceipt"""
        driver = MuJoCoDriver()
        receipt = driver.execute_action("move_to", {"x": 0.1, "y": 0.0, "z": 0.5})
        assert isinstance(receipt, ExecutionReceipt)
        assert receipt.receipt_id is not None
        assert receipt.action_type == "move_to"

    def test_get_scene_returns_dict(self):
        """get_scene 应返回场景字典"""
        driver = MuJoCoDriver()
        scene = driver.get_scene()
        assert isinstance(scene, dict)

    def test_emergency_stop(self):
        """emergency_stop 应返回 EMERGENCY_STOP 状态"""
        driver = MuJoCoDriver()
        receipt = driver.emergency_stop()
        assert receipt.status == ExecutionStatus.EMERGENCY_STOP

    def test_get_allowed_actions(self):
        """get_allowed_actions 应返回动作白名单"""
        driver = MuJoCoDriver()
        actions = driver.get_allowed_actions()
        assert isinstance(actions, list)
        assert "move_to" in actions
        assert "grasp" in actions
        assert "release" in actions

    def test_invalid_action_rejected(self):
        """白名单外动作应被拒绝"""
        driver = MuJoCoDriver()
        receipt = driver.execute_action("invalid_action", {})
        assert receipt.status == ExecutionStatus.FAILED
        assert "not in whitelist" in receipt.result_message
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_simulation/test_mujoco_driver.py -v
```

**Step 3: 实现 MuJoCoDriver**

```python
# simulation/mujoco/mujoco_driver.py
"""MuJoCo 仿真驱动 - 核心"""

import mujoco
import numpy as np
from typing import Optional

from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus
from simulation.mujoco.scene_builder import SceneBuilder
from simulation.mujoco.robot_model import RobotModel
from simulation.mujoco.sensors import ForceSensor, ContactSensor
from simulation.mujoco.config import (
    POSITION_LIMIT, Z_HEIGHT_LIMIT, VELOCITY_LIMIT,
    DEFAULT_TIMESTEP
)


class MuJoCoDriver:
    """MuJoCo 仿真驱动

    实现与 HAL 接口对齐的仿真驱动，支持：
    - 位置控制移动
    - 抓取/释放
    - 力觉反馈
    - 碰撞检测
    """

    def __init__(
        self,
        urdf_path: Optional[str] = None,
        timestep: float = DEFAULT_TIMESTEP,
    ):
        """
        Args:
            urdf_path: 机器人 URDF 路径（可选）
            timestep: 仿真时间步
        """
        self._timestep = timestep
        self._scene_builder = SceneBuilder(timestep=timestep)
        self._robot = RobotModel(urdf_path=urdf_path)
        self._force_sensor = ForceSensor()
        self._contact_sensor = ContactSensor()
        self._emergency_stopped = False
        self._grasped_object: Optional[str] = None

        # 构建场景
        self._model = self._robot.get_model()
        self._data = self._robot.get_data()

        # 关联传感器
        self._force_sensor.attach_to_body("base", self._model, self._data)
        self._contact_sensor.attach(self._model, self._data)

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """执行动作，返回 ExecutionReceipt

        Args:
            action_type: 动作类型
            params: 动作参数

        Returns:
            ExecutionReceipt: 执行凭证
        """
        # 紧急停止状态检查
        if self._emergency_stopped:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.EMERGENCY_STOP,
                result_message="Driver is in emergency stop state"
            )

        # 白名单验证
        allowed = self.get_allowed_actions()
        if action_type not in allowed:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Action '{action_type}' not in whitelist"
            )

        # 执行动作
        try:
            if action_type == "move_to":
                return self._move_to(params)
            elif action_type == "move_relative":
                return self._move_relative(params)
            elif action_type == "grasp":
                return self._grasp(params)
            elif action_type == "release":
                return self._release(params)
            elif action_type == "get_scene":
                return self._get_scene_receipt(params)
            else:
                return ExecutionReceipt(
                    action_type=action_type,
                    params=params,
                    status=ExecutionStatus.FAILED,
                    result_message=f"Unknown action: {action_type}"
                )
        except Exception as e:
            return ExecutionReceipt(
                action_type=action_type,
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Execution failed: {str(e)}"
            )

    def _move_to(self, params: dict) -> ExecutionReceipt:
        """移动到目标位置"""
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        z = params.get("z", 0.0)

        # 范围检查
        if abs(x) > POSITION_LIMIT or abs(y) > POSITION_LIMIT or z > Z_HEIGHT_LIMIT:
            return ExecutionReceipt(
                action_type="move_to",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Position out of bounds: x={x}, y={y}, z={z}"
            )

        # 简单位置控制：直接设置位置
        self._data.body("base").xpos = np.array([x, y, z])
        mujoco.mj_forward(self._model, self._data)

        return ExecutionReceipt(
            action_type="move_to",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved to ({x}, {y}, {z})",
            result_data={"position": [x, y, z]}
        )

    def _move_relative(self, params: dict) -> ExecutionReceipt:
        """相对移动"""
        dx = params.get("dx", 0.0)
        dy = params.get("dy", 0.0)
        dz = params.get("dz", 0.0)

        # 速度限制
        velocity = np.sqrt(dx**2 + dy**2 + dz**2)
        if velocity > VELOCITY_LIMIT:
            return ExecutionReceipt(
                action_type="move_relative",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message=f"Velocity {velocity} exceeds limit {VELOCITY_LIMIT}"
            )

        # 获取当前位置
        current_pos = self._data.body("base").xpos.copy()
        new_pos = current_pos + np.array([dx, dy, dz])

        # 范围检查
        if abs(new_pos[0]) > POSITION_LIMIT or abs(new_pos[1]) > POSITION_LIMIT or new_pos[2] > Z_HEIGHT_LIMIT:
            return ExecutionReceipt(
                action_type="move_relative",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="Target position out of bounds"
            )

        # 应用移动
        self._data.body("base").xpos = new_pos
        mujoco.mj_forward(self._model, self._data)

        return ExecutionReceipt(
            action_type="move_relative",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved relative by ({dx}, {dy}, {dz})",
            result_data={"new_position": new_pos.tolist()}
        )

    def _grasp(self, params: dict) -> ExecutionReceipt:
        """抓取物体（简化版：无真实物理抓取）"""
        object_id = params.get("object_id", "target")
        force = params.get("force", 0.5)

        # 检查接触
        contacts = self._contact_sensor.get_contacts()
        has_contact = len(contacts) > 0

        if has_contact:
            self._grasped_object = object_id
            return ExecutionReceipt(
                action_type="grasp",
                params=params,
                status=ExecutionStatus.SUCCESS,
                result_message=f"Grasped {object_id}",
                result_data={"gripper_state": "closed", "force": force, "object": object_id}
            )
        else:
            return ExecutionReceipt(
                action_type="grasp",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="No contact detected, cannot grasp"
            )

    def _release(self, params: dict) -> ExecutionReceipt:
        """释放物体"""
        if self._grasped_object is None:
            return ExecutionReceipt(
                action_type="release",
                params=params,
                status=ExecutionStatus.FAILED,
                result_message="No object currently grasped"
            )

        released = self._grasped_object
        self._grasped_object = None

        return ExecutionReceipt(
            action_type="release",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Released {released}",
            result_data={"gripper_state": "open"}
        )

    def _get_scene_receipt(self, params: dict) -> ExecutionReceipt:
        """获取场景状态"""
        return ExecutionReceipt(
            action_type="get_scene",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Scene state retrieved",
            result_data=self.get_scene()
        )

    def get_scene(self) -> dict:
        """获取当前场景状态"""
        return {
            "robot_position": self._data.body("base").xpos.tolist() if self._data else [0, 0, 0],
            "grasped_object": self._grasped_object,
            "contacts": len(self._contact_sensor.get_contacts()),
        }

    def get_allowed_actions(self) -> list[str]:
        """返回允许的动作白名单"""
        return ["move_to", "move_relative", "grasp", "release", "get_scene"]

    def emergency_stop(self) -> ExecutionReceipt:
        """紧急停止"""
        self._emergency_stopped = True
        mujoco.mj_resetData(self._model, self._data)
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Emergency stop executed"
        )

    def reset(self) -> None:
        """重置驱动状态"""
        self._emergency_stopped = False
        mujoco.mj_resetData(self._model, self._data)

    def get_force_feedback(self) -> dict:
        """获取力觉反馈"""
        return self._force_sensor.get_force_torque()

    def get_contact_info(self) -> list:
        """获取接触信息"""
        return self._contact_sensor.get_contacts()

    def step(self) -> None:
        """执行一步仿真"""
        mujoco.mj_step(self._model, self._data)
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_simulation/test_mujoco_driver.py -v
```

**Step 5: 提交**

```bash
git add simulation/mujoco/mujoco_driver.py tests/test_simulation/test_mujoco_driver.py
git commit -m "feat(simulation): add MuJoCoDriver core implementation

Implements:
- execute_action() returning ExecutionReceipt
- move_to, move_relative, grasp, release actions
- ForceSensor and ContactSensor integration
- emergency_stop() with HAL interface alignment
"
```

---

## Task 6: 更新模块导出

**Files:**
- Modify: `simulation/mujoco/__init__.py`

**Step 1: 更新 __init__.py**

```python
# simulation/mujoco/__init__.py
"""MuJoCo 仿真模块

提供基于 MuJoCo 的物理仿真环境，用于端到端系统测试。
"""

from simulation.mujoco.mujoco_driver import MuJoCoDriver
from simulation.mujoco.scene_builder import SceneBuilder
from simulation.mujoco.robot_model import RobotModel
from simulation.mujoco.sensors import ForceSensor, ContactSensor

__all__ = [
    "MuJoCoDriver",
    "SceneBuilder",
    "RobotModel",
    "ForceSensor",
    "ContactSensor",
]
```

**Step 2: 提交**

```bash
git add simulation/mujoco/__init__.py
git commit -m "feat(simulation): update __init__.py exports"
```

---

## Task 7: 创建示例脚本

**Files:**
- Create: `examples/simulation_mujoco_basic.py`

**Step 1: 创建示例脚本**

```python
#!/usr/bin/env python3
"""MuJoCo 仿真基础示例"""

from simulation.mujoco import MuJoCoDriver


def main():
    print("MuJoCo 仿真示例")

    # 创建驱动（无 URDF，使用空载）
    driver = MuJoCoDriver()

    # 获取场景
    scene = driver.get_scene()
    print(f"初始场景: {scene}")

    # 移动到目标位置
    receipt = driver.execute_action("move_to", {"x": 0.1, "y": 0.2, "z": 0.3})
    print(f"move_to 结果: status={receipt.status.value}, message={receipt.result_message}")

    # 相对移动
    receipt = driver.execute_action("move_relative", {"dx": 0.1, "dy": 0.0, "dz": 0.0})
    print(f"move_relative 结果: {receipt.status.value}")

    # 获取力觉反馈
    force = driver.get_force_feedback()
    print(f"力觉反馈: {force}")

    # 紧急停止
    receipt = driver.emergency_stop()
    print(f"紧急停止: {receipt.status.value}")

    print("示例完成")


if __name__ == "__main__":
    main()
```

**Step 2: 运行示例**

```bash
python examples/simulation_mujoco_basic.py
```

**Step 3: 提交**

```bash
git add examples/simulation_mujoco_basic.py
git commit -m "docs: add MuJoCo simulation basic example"
```

---

## 总结

完成上述任务后，将有：

| 组件 | 文件 | 功能 |
|------|------|------|
| `SceneBuilder` | `scene_builder.py` | 场景构建（地面、物体） |
| `RobotModel` | `robot_model.py` | URDF 加载 |
| `ForceSensor` | `sensors.py` | 力觉反馈 |
| `ContactSensor` | `sensors.py` | 接触检测 |
| `MuJoCoDriver` | `mujoco_driver.py` | 核心驱动 |
| 示例 | `examples/simulation_mujoco_basic.py` | 使用演示 |

**下一步:** Phase 2 - 完善抓取物理交互 + 可视化调试
