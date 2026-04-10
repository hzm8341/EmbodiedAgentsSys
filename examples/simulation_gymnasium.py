#!/usr/bin/env python3
"""Gymnasium 环境示例 - 使用 RL-Robot-Manipulation 环境"""

from simulation.mujoco import GymnasiumEnvDriver


def main():
    print("Gymnasium 环境示例")
    print("=" * 50)

    # 创建驱动 - 使用 Franka Push 环境
    driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")

    # 重置环境
    obs, info = driver.reset()
    print(f"初始观察 keys: {obs.keys() if isinstance(obs, dict) else 'N/A'}")

    # 移动到目标位置
    receipt = driver.execute_action("move_to", {"x": 0.1, "y": 0.0, "z": 0.0})
    print(f"move_to: {receipt.status.value} - {receipt.result_message}")

    # 相对移动
    receipt = driver.execute_action("move_relative", {"dx": 0.05, "dy": 0.05, "dz": 0.0})
    print(f"move_relative: {receipt.status.value} - {receipt.result_message}")

    # 获取场景状态
    scene = driver.get_scene()
    print(f"场景状态: robot={scene['robot_position']}, object={scene['object_position']}")

    # 抓取
    receipt = driver.execute_action("grasp", {})
    print(f"grasp: {receipt.status.value}")

    # 释放
    receipt = driver.execute_action("release", {})
    print(f"release: {receipt.status.value}")

    # 紧急停止
    receipt = driver.emergency_stop()
    print(f"emergency_stop: {receipt.status.value}")

    driver.close()
    print("=" * 50)
    print("示例完成")


if __name__ == "__main__":
    main()
