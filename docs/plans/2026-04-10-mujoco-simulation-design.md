# MuJoCo 仿真环境集成设计

**日期:** 2026-04-10
**状态:** 已批准
**目标:** 使用 MuJoCo 实现端到端系统仿真测试

---

## 1. 背景

用户拥有自己的机器人 URDF 文件，需要搭建 MuJoCo 仿真场景进行端到端测试。现有 HAL 架构已有 `SimulationDriver`，但缺乏真实物理仿真能力。

**用户基础:** 了解 MuJoCo 基础，有过简单实验

---

## 2. 架构决策

### 2.1 独立仿真模块

采用方案 **独立仿真模块** (`simulation/mujoco/`)，与 HAL 模块并行。

**原因:**
- 保持 HAL 架构纯净，专注硬件抽象
- MuJoCo 仿真层可独立演进
- 避免与现有简单仿真驱动耦合
- 支持未来多仿真后端扩展

### 2.2 目录结构

```
embodiedagentsys/
├── hal/                          # 现有 HAL 模块（不变）
│   ├── base_driver.py
│   ├── types.py
│   └── drivers/
│       └── simulation_driver.py
│
└── simulation/                   # 新增：独立仿真模块
    └── mujoco/
        ├── __init__.py
        ├── mujoco_driver.py      # MuJoCo 驱动核心
        ├── scene_builder.py      # 场景构建器
        ├── robot_model.py        # URDF 机器人模型加载
        └── sensors.py            # 传感器接口（力觉）
```

---

## 3. 核心组件设计

### 3.1 MuJoCoDriver

**接口对齐 HAL:**
```python
class MuJoCoDriver:
    def __init__(self, config: dict):
        """初始化 MuJoCo 仿真"""
        self._scene = None
        self._model = None
        self._data = None

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """执行动作，返回 ExecutionReceipt"""

    def get_scene(self) -> dict:
        """获取当前场景状态"""

    def emergency_stop(self) -> ExecutionReceipt:
        """紧急停止"""

    def get_allowed_actions(self) -> list[str]:
        """返回允许的动作白名单"""
```

**支持的动作类型:**
| Action | Parameters | Description |
|--------|------------|-------------|
| `move_to` | x, y, z | 移动到目标位置 |
| `move_relative` | dx, dy, dz | 相对移动 |
| `grasp` | object_id, force | 抓取物体 |
| `release` | - | 释放物体 |

### 3.2 SceneBuilder

**功能:**
- 从 XML/MJCF 加载场景
- 支持添加地面、桌面、障碍物
- 配置物理参数（摩擦系数、弹性）
- 管理仿真 timestep

```python
class SceneBuilder:
    def __init__(self):
        self._bodies = []

    def load_robot_from_urdf(self, urdf_path: str) -> mujoco.MjModel:
        """加载用户 URDF"""

    def add_body(self, name: str, type: str, pos: tuple, size: tuple):
        """添加简单几何体"""

    def build(self) -> tuple[mujoco.MjModel, mujoco.MjData]:
        """构建完整场景"""
```

### 3.3 传感器接口

**力觉反馈:**
```python
class ForceSensor:
    def get_force_torque(self) -> dict:
        """返回末端执行器力/力矩"""

    def get_contact_forces(self) -> list[dict]:
        """返回接触力列表"""
```

---

## 4. 物理特性支持

### 4.1 基础运动
- 位置控制 (move_to)
- 相对运动 (move_relative)
- 抓取/释放 (grasp/release)

### 4.2 接触力反馈
- 碰撞检测
- 力/力矩感知
- 接触点信息

---

## 5. 与 HAL 集成方式

MuJoCoDriver **不继承** BaseDriver，而是实现相同接口：

```python
# simulation/mujoco/mujoco_driver.py
class MuJoCoDriver:
    """独立仿真驱动，与 HAL 接口对齐但独立演进"""

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        # 与 HAL ExecutionReceipt 格式一致
        pass

# 使用时通过适配器桥接
class HALMuJoCoAdapter:
    """可选：桥接 HAL 与 MuJoCoDriver"""
    pass
```

---

## 6. 实施计划

### Phase 1: 基础框架
1. 创建 `simulation/mujoco/` 目录结构
2. 实现 `SceneBuilder` 加载 URDF
3. 实现基础 `MuJoCoDriver`（位置控制）

### Phase 2: 物理仿真
4. 添加抓取/释放物理交互
5. 实现 `ForceSensor` 力觉反馈
6. 完善碰撞检测

### Phase 3: 系统集成
7. 与 agent 系统联调
8. 端到端测试

---

## 7. 依赖

```txt
mujoco>=3.0.0
numpy
```

---

## 8. 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| URDF 格式兼容 | 提供验证脚本和错误提示 |
| 物理不稳定 | 提供默认稳定参数，可配置 |
| 性能问题 | 减少仿真 timestep，调优 |
