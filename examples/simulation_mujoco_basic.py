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