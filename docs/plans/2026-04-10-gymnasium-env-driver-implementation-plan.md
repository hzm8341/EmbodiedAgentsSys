# GymnasiumEnvDriver 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 RL-Robot-Manipulation 的 Gymnasium 环境包装为 HAL 接口兼容的驱动。

**Architecture:** 新增 `simulation/mujoco/gymnasium_env_driver.py`，独立于原生 MuJoCo 驱动存在。离散动作映射到连续控制。

**Tech Stack:** gymnasium>=0.29.0, gymnasium-robotics, numpy

---

## Task 1: 创建 GymnasiumEnvDriver

**Files:**
- Create: `simulation/mujoco/gymnasium_env_driver.py`
- Test: `tests/test_simulation/test_gymnasium_env_driver.py`

**Step 1: 写失败测试**

```python
# tests/test_simulation/test_gymnasium_env_driver.py
import pytest
from simulation.mujoco.gymnasium_env_driver import GymnasiumEnvDriver
from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus


class TestGymnasiumEnvDriver:
    def test_create_driver(self):
        """应该能创建驱动"""
        driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")
        assert driver is not None

    def test_reset_returns_obs(self):
        """reset 应该返回观察"""
        driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")
        obs, _ = driver.reset()
        assert isinstance(obs, dict)
        assert "observation" in obs or "achieved_goal" in obs

    def test_execute_move_to(self):
        """move_to 应该成功执行"""
        driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")
        driver.reset()
        receipt = driver.execute_action("move_to", {"x": 0.1, "y": 0.0, "z": 0.0})
        assert receipt.status == ExecutionStatus.SUCCESS

    def test_get_allowed_actions(self):
        """应该返回允许的动作"""
        driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")
        actions = driver.get_allowed_actions()
        assert "move_to" in actions
        assert "grasp" in actions
        assert "release" in actions
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/test_simulation/test_gymnasium_env_driver.py -v
```

**Step 3: 实现 GymnasiumEnvDriver**

```python
# simulation/mujoco/gymnasium_env_driver.py
"""Gymnasium 环境驱动 - 包装 RL 环境为 HAL 接口"""

import gymnasium as gym
import numpy as np
from typing import Optional, Tuple

from embodiedagents.hal.types import ExecutionReceipt, ExecutionStatus


class GymnasiumEnvDriver:
    """包装 Gymnasium 环境的驱动

    将离散动作（move_to, grasp, release）映射到 Gymnasium 连续控制。
    继承 HAL 接口模式但不继承 BaseDriver。
    """

    def __init__(
        self,
        env_name: str = "FrankaPushSparse-v0",
        render_mode: Optional[str] = None,
    ):
        """
        Args:
            env_name: Gymnasium 环境名称
            render_mode: 渲染模式 (None, "human", "rgb_array")
        """
        self._env_name = env_name
        self._render_mode = render_mode
        self._env: Optional[gym.Env] = None
        self._obs: Optional[dict] = None
        self._action_space_shape: Optional[tuple] = None
        self._initial_ee_pos: Optional[np.ndarray] = None

    def _ensure_env(self) -> gym.Env:
        """延迟创建环境"""
        if self._env is None:
            self._env = gym.make(self._env_name, render_mode=self._render_mode)
            self._action_space_shape = self._env.action_space.shape
        return self._env

    def reset(self) -> Tuple[dict, dict]:
        """重置环境，返回观察和 info"""
        env = self._ensure_env()
        self._obs, info = env.reset()
        # 记录初始末端执行器位置
        if "observation" in self._obs:
            obs_arr = self._obs["observation"]
            self._initial_ee_pos = obs_arr[:3].copy()
        return self._obs, info

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """执行动作，返回 ExecutionReceipt

        Args:
            action_type: 动作类型 (move_to, move_relative, grasp, release)
            params: 动作参数

        Returns:
            ExecutionReceipt: 执行凭证
        """
        env = self._ensure_env()

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

    def _compute_action(self, dx: float, dy: float, dz: float, gripper: float = 0.0) -> np.ndarray:
        """计算连续动作

        Args:
            dx, dy, dz: 位置增量
            gripper: gripper 控制值

        Returns:
            连续动作数组
        """
        action = np.zeros(self._action_space_shape)
        # 位置控制（相对于初始位置或当前 ee 位置）
        if self._initial_ee_pos is not None:
            target = self._initial_ee_pos + np.array([dx, dy, dz])
            # 归一化到 [-1, 1]（假设工作空间 0.5m）
            scale = 2.0  # 0.5m -> [-1, 1]
            action[:3] = np.clip((target - self._initial_ee_pos) * scale, -1, 1)
        else:
            action[:3] = np.clip([dx, dy, dz], -1, 1)
        # gripper
        if self._action_space_shape[0] > 3:
            action[3] = gripper
        return action

    def _move_to(self, params: dict) -> ExecutionReceipt:
        """移动到目标位置（相对于初始位置）"""
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        z = params.get("z", 0.0)
        gripper = params.get("gripper", 0.0)

        action = self._compute_action(x, y, z, gripper)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        self._obs, _ = self._env.reset() if terminated or truncated else (self._obs, {})

        return ExecutionReceipt(
            action_type="move_to",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved to ({x}, {y}, {z})",
            result_data={"position": [x, y, z], "reward": reward}
        )

    def _move_relative(self, params: dict) -> ExecutionReceipt:
        """相对移动"""
        dx = params.get("dx", 0.0)
        dy = params.get("dy", 0.0)
        dz = params.get("dz", 0.0)
        gripper = params.get("gripper", 0.0)

        action = self._compute_action(dx, dy, dz, gripper)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        self._obs, _ = self._env.reset() if terminated or truncated else (self._obs, {})

        return ExecutionReceipt(
            action_type="move_relative",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved relative by ({dx}, {dy}, {dz})",
            result_data={"delta": [dx, dy, dz], "reward": reward}
        )

    def _grasp(self, params: dict) -> ExecutionReceipt:
        """抓取 - 关闭夹爪"""
        action = self._compute_action(0, 0, 0, gripper=-1.0)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        self._obs, _ = self._env.reset() if terminated or truncated else (self._obs, {})

        return ExecutionReceipt(
            action_type="grasp",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Grasp executed",
            result_data={"gripper_state": "closed"}
        )

    def _release(self, params: dict) -> ExecutionReceipt:
        """释放 - 打开夹爪"""
        action = self._compute_action(0, 0, 0, gripper=1.0)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        self._obs, _ = self._env.reset() if terminated or truncated else (self._obs, {})

        return ExecutionReceipt(
            action_type="release",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Release executed",
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
        if self._obs is None:
            return {"robot_position": [0, 0, 0], "object_position": [0, 0, 0]}

        obs = self._obs.get("observation", np.zeros(18))
        ee_pos = obs[:3] if len(obs) >= 3 else np.zeros(3)
        obj_pos = obs[6:9] if len(obs) >= 9 else np.zeros(3)

        return {
            "robot_position": ee_pos.tolist(),
            "object_position": obj_pos.tolist(),
        }

    def get_allowed_actions(self) -> list[str]:
        """返回允许的动作白名单"""
        return ["move_to", "move_relative", "grasp", "release", "get_scene"]

    def emergency_stop(self) -> ExecutionReceipt:
        """紧急停止 - 重置环境"""
        if self._env is not None:
            self._obs, _ = self._env.reset()
        return ExecutionReceipt(
            action_type="emergency_stop",
            params={},
            status=ExecutionStatus.EMERGENCY_STOP,
            result_message="Emergency stop executed, env reset"
        )

    def close(self) -> None:
        """关闭环境"""
        if self._env is not None:
            self._env.close()
            self._env = None
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/test_simulation/test_gymnasium_env_driver.py -v
```

**Step 5: 提交**

```bash
git add simulation/mujoco/gymnasium_env_driver.py tests/test_simulation/test_gymnasium_env_driver.py
git commit -m "feat(simulation): add GymnasiumEnvDriver for RL environment integration"
```

---

## Task 2: 创建示例脚本

**Files:**
- Create: `examples/simulation_gymnasium.py`

```python
#!/usr/bin/env python3
"""Gymnasium 环境示例"""

from simulation.mujoco import GymnasiumEnvDriver


def main():
    print("Gymnasium 环境示例")

    # 创建驱动
    driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")

    # 重置环境
    obs, info = driver.reset()
    print(f"初始观察: {obs}")

    # 移动
    receipt = driver.execute_action("move_to", {"x": 0.1, "y": 0.0, "z": 0.0})
    print(f"move_to: {receipt.status.value} - {receipt.result_message}")

    # 获取场景
    scene = driver.get_scene()
    print(f"场景: {scene}")

    # 抓取
    receipt = driver.execute_action("grasp", {})
    print(f"grasp: {receipt.status.value}")

    # 紧急停止
    receipt = driver.emergency_stop()
    print(f"emergency_stop: {receipt.status.value}")

    driver.close()
    print("示例完成")


if __name__ == "__main__":
    main()
```

---

## Task 3: 更新导出

**Modify:** `simulation/mujoco/__init__.py`

添加:
```python
from simulation.mujoco.gymnasium_env_driver import GymnasiumEnvDriver
```
