:orphan:

# Gymnasium 环境驱动集成设计

**日期:** 2026-04-10
**目标:** 将 RL-Robot-Manipulation 的 Gymnasium 环境集成到 simulation/mujoco/

---

## 1. 背景

用户希望将 `RL-Robot-Manipulation` 中的 Franka MuJoCo 环境（基于 gymnasium-robotics）集成到现有仿真框架中，实现与 HAL 接口对齐。

## 2. 架构决策

### 2.1 目录结构

```
simulation/mujoco/
├── gymnasium_env_driver.py   # 新增：Gymnasium 环境包装器
└── ...

RL-Robot-Manipulation/         # 外部依赖，不修改
├── panda_mujoco_gym/
│   └── envs/
```

### 2.2 GymnasiumEnvDriver 设计

```python
class GymnasiumEnvDriver:
    """包装 Gymnasium 环境的驱动

    将离散动作（move_to, grasp, release）映射到连续控制。
    """

    def __init__(
        self,
        env_name: str = "FrankaPushSparse-v0",
        render_mode: str = None
    ):
        """
        Args:
            env_name: Gymnasium 环境名称
            render_mode: 渲染模式 (None, "human", "rgb_array")
        """
        self._env = gym.make(env_name, render_mode=render_mode)
        self._action_space = self._env.action_space

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """执行动作，返回 ExecutionReceipt"""

    def get_scene(self) -> dict:
        """获取当前场景状态"""

    def get_allowed_actions(self) -> list[str]:
        return ["move_to", "move_relative", "grasp", "release"]

    def emergency_stop(self) -> ExecutionReceipt:
        """紧急停止 - 重置环境"""
```

### 2.3 动作映射

| HAL Action | 连续 Action | 说明 |
|------------|-------------|------|
| `move_to` | dx, dy, dz (3D) | 末端位置增量 |
| `move_relative` | dx, dy, dz (3D) | 相对移动 |
| `grasp` | gripper=-1 | 关闭夹爪 |
| `release` | gripper=+1 | 打开夹爪 |

## 3. 实施计划

### Task 1: 创建 GymnasiumEnvDriver

**文件:**
- `simulation/mujoco/gymnasium_env_driver.py`
- `tests/test_simulation/test_gymnasium_env_driver.py`

### Task 2: 添加环境配置

**文件:**
- `simulation/mujoco/env_configs.py` - 环境名称映射

### Task 3: 创建示例

**文件:**
- `examples/simulation_gymnasium.py`

## 4. 依赖

```
gymnasium>=0.29.0
gymnasium-robotics
```

---

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| gymnasium-robotics 安装复杂 | 提供 requirements.txt |
| 动作空间不匹配 | 动态检测 action_space 类型 |
