"""Gymnasium 环境驱动 - 包装 RL 环境为 HAL 接口"""

import gymnasium as gym
import numpy as np
from typing import Optional, Tuple

from embodiedagentsys.hal.types import ExecutionReceipt, ExecutionStatus


class GymnasiumEnvDriver:
    """包装 Gymnasium 环境的驱动

    将离散动作（move_to, grasp, release）映射到 Gymnasium 连续控制。
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
        if "observation" in self._obs:
            obs_arr = self._obs["observation"]
            self._initial_ee_pos = obs_arr[:3].copy()
        return self._obs, info

    def execute_action(self, action_type: str, params: dict) -> ExecutionReceipt:
        """执行动作，返回 ExecutionReceipt"""
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

    def _compute_action(
        self, dx: float, dy: float, dz: float, gripper: float = 0.0
    ) -> np.ndarray:
        """计算连续动作"""
        action = np.zeros(self._action_space_shape)
        if self._initial_ee_pos is not None:
            target = self._initial_ee_pos + np.array([dx, dy, dz])
            scale = 2.0
            action[:3] = np.clip((target - self._initial_ee_pos) * scale, -1, 1)
        else:
            action[:3] = np.clip([dx, dy, dz], -1, 1)
        if self._action_space_shape[0] > 3:
            action[3] = gripper
        return action

    def _move_to(self, params: dict) -> ExecutionReceipt:
        """移动到目标位置"""
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        z = params.get("z", 0.0)
        gripper = params.get("gripper", 0.0)

        action = self._compute_action(x, y, z, gripper)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        if terminated or truncated:
            self._obs, _ = self._env.reset()

        return ExecutionReceipt(
            action_type="move_to",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved to ({x}, {y}, {z})",
            result_data={"position": [x, y, z], "reward": float(reward) if reward else 0},
        )

    def _move_relative(self, params: dict) -> ExecutionReceipt:
        """相对移动"""
        dx = params.get("dx", 0.0)
        dy = params.get("dy", 0.0)
        dz = params.get("dz", 0.0)
        gripper = params.get("gripper", 0.0)

        action = self._compute_action(dx, dy, dz, gripper)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        if terminated or truncated:
            self._obs, _ = self._env.reset()

        return ExecutionReceipt(
            action_type="move_relative",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message=f"Moved relative by ({dx}, {dy}, {dz})",
            result_data={"delta": [dx, dy, dz], "reward": float(reward) if reward else 0},
        )

    def _grasp(self, params: dict) -> ExecutionReceipt:
        """抓取 - 关闭夹爪"""
        action = self._compute_action(0, 0, 0, gripper=-1.0)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        if terminated or truncated:
            self._obs, _ = self._env.reset()

        return ExecutionReceipt(
            action_type="grasp",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Grasp executed",
            result_data={"gripper_state": "closed"},
        )

    def _release(self, params: dict) -> ExecutionReceipt:
        """释放 - 打开夹爪"""
        action = self._compute_action(0, 0, 0, gripper=1.0)
        self._obs, reward, terminated, truncated, info = self._env.step(action)
        if terminated or truncated:
            self._obs, _ = self._env.reset()

        return ExecutionReceipt(
            action_type="release",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Release executed",
            result_data={"gripper_state": "open"},
        )

    def _get_scene_receipt(self, params: dict) -> ExecutionReceipt:
        """获取场景状态"""
        return ExecutionReceipt(
            action_type="get_scene",
            params=params,
            status=ExecutionStatus.SUCCESS,
            result_message="Scene state retrieved",
            result_data=self.get_scene(),
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
            result_message="Emergency stop executed",
        )

    def close(self) -> None:
        """关闭环境"""
        if self._env is not None:
            self._env.close()
            self._env = None
