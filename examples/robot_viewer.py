#!/usr/bin/env python3
"""
简化版机器人查看器 - 使用原生 MuJoCo
直接加载 XML 模型，提供交互式命令控制
"""

import sys
sys.path.insert(0, "/media/hzm/Data/EmbodiedAgentsSys")

import mujoco
import mujoco.viewer
import numpy as np


class SimpleRobotViewer:
    """简化版机器人查看器"""

    def __init__(self, xml_path=None):
        self.xml_path = xml_path or "/media/hzm/Data/EmbodiedAgentsSys/RL-Robot-Manipulation/panda_mujoco_gym/assets/push.xml"
        self.model = None
        self.data = None
        self.running = True
        self.viewer = None

        # 关节控制
        self.target_pos = np.zeros(7)  # 7 个关节
        self.gripper_target = 0.04  # 夹爪开度

    def load(self):
        """加载模型"""
        print(f"加载模型: {self.xml_path}")
        self.model = mujoco.MjModel.from_xml_path(self.xml_path)
        self.data = mujoco.MjData(self.model)
        print("模型加载成功!")

        # 打印模型信息
        print(f"关节数量: {self.model.njnt}")
        print(f"控制数量: {self.model.nu}")

    def start(self):
        """启动查看器"""
        print("=" * 60)
        print("简化版机器人查看器")
        print("=" * 60)
        print("支持的命令:")
        print("  joint <j0> <j1> ... <j6>  - 设置关节角度 (7个值)")
        print("  gripper <value>          - 设置夹爪开度 (0=关闭, 0.04=打开)")
        print("  move <x> <y> <z>        - 移动末端到目标位置")
        print("  status                   - 查看状态")
        print("  quit                     - 退出")
        print("=" * 60)

        self.load()

        # 创建被动查看器
        print("打开查看器窗口...")
        self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        print("查看器窗口已打开!")
        print()

        # 保持查看器运行，同时处理命令
        self._command_loop()

        self.viewer.close()

    def _command_loop(self):
        """命令循环"""
        while self.running and self.viewer.is_running():
            try:
                # 非阻塞输入检查
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.readline()
                    if cmd:
                        self._execute_command(cmd.strip())
            except (EOFError, OSError):
                break
            except KeyboardInterrupt:
                print("\n退出中...")
                break

    def _execute_command(self, cmd: str):
        """执行命令"""
        cmd = cmd.lower().strip()

        if not cmd:
            return

        if cmd == "quit" or cmd == "exit":
            self.running = False
            return

        if cmd == "status":
            self._show_status()
            return

        if cmd.startswith("joint"):
            self._cmd_joint(cmd)
            return

        if cmd.startswith("gripper"):
            self._cmd_gripper(cmd)
            return

        if cmd.startswith("move"):
            self._cmd_move(cmd)
            return

        print(f"未知命令: {cmd}")

    def _cmd_joint(self, cmd: str):
        """设置关节角度"""
        parts = cmd.split()
        if len(parts) < 7:
            print(f"需要7个关节值，得到 {len(parts)-1}")
            return

        try:
            joints = [float(p) for p in parts[1:7]]
            joints = np.array(joints)

            # 7 个关节 + 2 个夹爪 = 9 个控制
            nu = self.model.nu
            n_joints = min(len(joints), nu)

            # 设置关节控制 (前7个)
            self.data.ctrl[:7] = joints[:7]

            # 仿真几步
            for _ in range(50):
                mujoco.mj_step(self.model, self.data)

            print(f"关节角度已设置: {joints}")
            self._show_status()
        except ValueError as e:
            print(f"解析错误: {e}")

    def _cmd_gripper(self, cmd: str):
        """设置夹爪开度"""
        parts = cmd.split()
        if len(parts) < 2:
            print("需要夹爪开度值")
            return

        try:
            self.gripper_target = float(parts[1])
            # 设置夹爪控制 (最后两个 ctrl)
            if self.model.nu >= 9:
                self.data.ctrl[7] = self.gripper_target
                self.data.ctrl[8] = self.gripper_target

                for _ in range(50):
                    mujoco.mj_step(self.model, self.data)

                print(f"夹爪开度已设置为: {self.gripper_target}")
                self._show_status()
        except ValueError as e:
            print(f"解析错误: {e}")

    def _cmd_move(self, cmd: str):
        """移动末端到目标位置 (简化版)"""
        parts = cmd.split()
        if len(parts) < 4:
            print("需要 x y z 三个值")
            return

        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            print(f"目标位置: x={x}, y={y}, z={z}")
            print("(简化版: 调整关节角度到合适位置)")

            # 简化为设置默认关节角度
            # 真实场景需要逆运动学
            default_joints = np.array([0.0, 0.5, 0.0, -1.5, 0.0, 2.0, 0.5])
            self.data.ctrl[:7] = default_joints

            for _ in range(100):
                mujoco.mj_step(self.model, self.data)

            self._show_status()
        except ValueError as e:
            print(f"解析错误: {e}")

    def _show_status(self):
        """显示状态"""
        try:
            ee_id = self.model.site_name2id("ee_center_site")
            ee_pos = self.data.site_xpos[ee_id]
        except Exception:
            ee_pos = np.zeros(3)

        print("-" * 40)
        print(f"末端执行器位置: x={ee_pos[0]:.3f}, y={ee_pos[1]:.3f}, z={ee_pos[2]:.3f}")
        print(f"关节角度: {self.data.qpos[:7] if len(self.data.qpos) >= 7 else 'N/A'}")
        print(f"夹爪开度: {self.data.ctrl[7]:.4f if self.model.nu >= 8 else 'N/A'}")
        print("-" * 40)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", default=None, help="XML 模型路径")
    args = parser.parse_args()

    viewer = SimpleRobotViewer(xml_path=args.xml)
    viewer.start()


if __name__ == "__main__":
    main()
