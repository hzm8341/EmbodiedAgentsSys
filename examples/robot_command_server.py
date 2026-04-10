#!/usr/bin/env python3
"""
机器人命令服务器
长期运行的 MuJoCo 仿真窗口，接收命令控制机器人

用法:
    python3 examples/robot_command_server.py
    # 然后在另一个终端输入命令，如:
    # move_to x=10 y=0 z=20
    # grasp
    # release
    # quit
"""

import sys
import os

# 添加路径
sys.path.insert(0, "/media/hzm/Data/EmbodiedAgentsSys")
sys.path.insert(0, "/media/hzm/Data/EmbodiedAgentsSys/RL-Robot-Manipulation")

# 注册环境
import panda_mujoco_gym.envs  # noqa: F401

import gymnasium as gym
import numpy as np
import threading
import socket
import time


class RobotCommandServer:
    """机器人命令服务器 - 控制仿真环境"""

    def __init__(self, env_name="FrankaPushSparse-v0"):
        self.env_name = env_name
        self.env = None
        self.running = True
        self.obs = None
        self.info = None
        self.ee_position = np.zeros(3)
        self.gripper_state = "open"

    def start(self):
        """启动服务器"""
        print("=" * 60)
        print("机器人命令服务器")
        print("=" * 60)
        print("支持的命令:")
        print("  move_to x=<值> y=<值> z=<值>  - 移动到目标位置")
        print("  move dx=<值> dy=<值> dz=<值>   - 相对移动")
        print("  grasp                            - 抓取")
        print("  release                          - 释放")
        print("  status                            - 查看状态")
        print("  quit                             - 退出")
        print("=" * 60)

        # 创建环境
        print(f"创建环境: {self.env_name}")
        self.env = gym.make(self.env_name, render_mode="human")
        self.obs, self.info = self.env.reset()
        print("环境已创建，窗口应该已打开")
        print()

        # 启动渲染线程
        render_thread = threading.Thread(target=self._render_loop, daemon=True)
        render_thread.start()

        # 命令循环
        self._command_loop()

    def _render_loop(self):
        """渲染循环 - 保持窗口更新"""
        while self.running:
            if self.env is not None:
                try:
                    self.env.render()
                except Exception:
                    pass
            time.sleep(0.01)  # ~100 FPS

    def _command_loop(self):
        """命令循环"""
        while self.running:
            try:
                cmd = input("命令> ").strip()
                if not cmd:
                    continue
                self._execute_command(cmd)
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n退出中...")
                break

        self._cleanup()

    def _execute_command(self, cmd: str):
        """执行命令"""
        cmd = cmd.lower().strip()

        if cmd == "quit" or cmd == "exit":
            self.running = False
            return

        if cmd == "status":
            self._show_status()
            return

        if cmd.startswith("move_to"):
            self._cmd_move_to(cmd)
            return

        if cmd.startswith("move"):
            self._cmd_move(cmd)
            return

        if cmd == "grasp":
            self._cmd_grasp()
            return

        if cmd == "release":
            self._cmd_release()
            return

        print(f"未知命令: {cmd}")

    def _parse_position(self, cmd: str) -> tuple:
        """解析位置参数"""
        x, y, z = 0.0, 0.0, 0.0
        parts = cmd.replace(",", " ").split()
        for part in parts:
            if part.startswith("x="):
                x = float(part[2:])
            elif part.startswith("y="):
                y = float(part[2:])
            elif part.startswith("z="):
                z = float(part[2:])
        return x, y, z

    def _compute_action(self, dx: float, dy: float, dz: float, gripper: float = 0.0) -> np.ndarray:
        """计算连续动作"""
        action_space = self.env.action_space
        action = np.zeros(action_space.shape)

        # 获取当前 ee 位置
        if self.obs is not None and "observation" in self.obs:
            obs = self.obs["observation"]
            current_ee = obs[:3]
        else:
            current_ee = np.array([0.5, 0.0, 0.2])  # 默认位置

        # 计算目标位置
        target = current_ee + np.array([dx, dy, dz])

        # 转换为动作 (简化版：直接用位置差)
        action[:3] = np.clip((target - current_ee) * 2, -1, 1)

        if len(action) > 3:
            action[3] = gripper

        return action

    def _cmd_move_to(self, cmd: str):
        """移动到目标位置"""
        x, y, z = self._parse_position(cmd)
        print(f"移动到: x={x}, y={y}, z={z}")

        # 计算相对位移
        if self.obs is not None and "observation" in self.obs:
            obs = self.obs["observation"]
            current = obs[:3]
            dx, dy, dz = x - current[0], y - current[1], z - current[2]
        else:
            dx, dy, dz = x, y, z

        action = self._compute_action(dx, dy, dz, self._get_gripper_value())
        self._step(action)
        print(f"  结果: {self.obs is not None}")

    def _cmd_move(self, cmd: str):
        """相对移动"""
        x, y, z = self._parse_position(cmd)
        print(f"相对移动: dx={x}, dy={y}, dz={z}")

        action = self._compute_action(x, y, z, self._get_gripper_value())
        self._step(action)
        print(f"  结果: {self.obs is not None}")

    def _cmd_grasp(self):
        """抓取"""
        print("执行抓取")
        gripper = -1.0  # 关闭夹爪
        action = self._compute_action(0, 0, 0, gripper)
        self._step(action)
        self.gripper_state = "closed"
        print("  夹爪已关闭")

    def _cmd_release(self):
        """释放"""
        print("执行释放")
        gripper = 1.0  # 打开夹爪
        action = self._compute_action(0, 0, 0, gripper)
        self._step(action)
        self.gripper_state = "open"
        print("  夹爪已打开")

    def _get_gripper_value(self) -> float:
        """获取夹爪控制值"""
        return -1.0 if self.gripper_state == "closed" else 1.0

    def _step(self, action):
        """执行一步仿真"""
        self.obs, reward, terminated, truncated, info = self.env.step(action)
        if terminated or truncated:
            print("  (环境重置)")
            self.obs, _ = self.env.reset()
        # 更新 ee 位置
        if self.obs is not None and "observation" in self.obs:
            self.ee_position = self.obs["observation"][:3].copy()

    def _show_status(self):
        """显示状态"""
        if self.obs is not None and "observation" in self.obs:
            obs = self.obs["observation"]
            ee_pos = obs[:3]
            obj_pos = obs[6:9] if len(obs) > 6 else np.zeros(3)
        else:
            ee_pos = np.zeros(3)
            obj_pos = np.zeros(3)

        print("-" * 40)
        print(f"末端执行器位置: x={ee_pos[0]:.3f}, y={ee_pos[1]:.3f}, z={ee_pos[2]:.3f}")
        print(f"物体位置: x={obj_pos[0]:.3f}, y={obj_pos[1]:.3f}, z={obj_pos[2]:.3f}")
        print(f"夹爪状态: {self.gripper_state}")
        print("-" * 40)

    def _cleanup(self):
        """清理"""
        self.running = False
        if self.env is not None:
            self.env.close()
        print("服务器已关闭")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="机器人命令服务器")
    parser.add_argument(
        "--env",
        default="FrankaPushSparse-v0",
        choices=["FrankaPushSparse-v0", "FrankaPushDense-v0",
                 "FrankaSlideSparse-v0", "FrankaSlideDense-v0",
                 "FrankaPickAndPlaceSparse-v0", "FrankaPickAndPlaceDense-v0"],
        help="环境名称"
    )
    args = parser.parse_args()

    server = RobotCommandServer(env_name=args.env)
    server.start()


if __name__ == "__main__":
    main()
