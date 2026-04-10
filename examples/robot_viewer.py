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

    def load(self):
        """加载模型"""
        print("加载模型: %s" % self.xml_path)
        self.model = mujoco.MjModel.from_xml_path(self.xml_path)
        self.data = mujoco.MjData(self.model)
        print("模型加载成功!")

        # 运行前向运动学初始化位置
        mujoco.mj_forward(self.model, self.data)

        print("关节数量: %d" % self.model.njnt)
        print("控制数量: %d" % self.model.nu)

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
        print("查看器窗口已打开! MuJoCo 窗口会实时显示仿真结果")
        print()

        # 启动查看器和仿真循环
        self._viewer_loop()

    def _viewer_loop(self):
        """查看器和仿真主循环"""
        while self.running and self.viewer.is_running():
            # 运行仿真
            mujoco.mj_step(self.model, self.data)

            # 同步查看器
            self.viewer.sync()

            # 处理命令（非阻塞）
            try:
                import select
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    cmd = sys.stdin.readline()
                    if cmd:
                        self._execute_command(cmd.strip())
                    else:
                        break
            except (EOFError, OSError):
                break
            except KeyboardInterrupt:
                print("\n退出中...")
                break

        self.viewer.close()

    def _command_loop(self):
        """命令循环"""
        while self.running:
            try:
                import select
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.readline()
                    if cmd:
                        self._execute_command(cmd.strip())
                    else:
                        break
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
            if self.viewer:
                self.viewer.close()
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

        print("未知命令: %s" % cmd)

    def _cmd_joint(self, cmd: str):
        """设置关节角度"""
        parts = cmd.split()
        if len(parts) < 8:
            print("需要7个关节值，例如: joint 0.0 0.5 0.0 -1.5 0.0 2.0 0.5")
            return

        try:
            joints = [float(p) for p in parts[1:8]]
            joints = np.array(joints)

            # 设置关节控制 (前7个)
            self.data.ctrl[:7] = joints

            # 运行几步仿真
            for _ in range(200):
                mujoco.mj_step(self.model, self.data)

            print("关节角度已设置: %s" % str(joints))
            self._show_status()
        except ValueError as e:
            print("解析错误: %s" % str(e))

    def _cmd_gripper(self, cmd: str):
        """设置夹爪开度"""
        parts = cmd.split()
        if len(parts) < 2:
            print("需要夹爪开度值，例如: gripper 0.02")
            return

        try:
            value = float(parts[1])
            self.data.ctrl[7] = value
            self.data.ctrl[8] = value

            for _ in range(100):
                mujoco.mj_step(self.model, self.data)

            mujoco.mj_forward(self.model, self.data)

            print("夹爪开度已设置为: %.4f" % value)
            self._show_status()
        except ValueError as e:
            print("解析错误: %s" % str(e))

    def _cmd_move(self, cmd: str):
        """移动末端到目标位置 (简化版)"""
        parts = cmd.split()
        if len(parts) < 4:
            print("需要 x y z 三个值，例如: move 0.5 0.0 0.3")
            return

        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            print("目标位置: x=%.3f, y=%.3f, z=%.3f" % (x, y, z))
            print("(简化版: 调整到默认关节角度)")
            # 简化：设置默认关节角度
            default_joints = np.array([0.0, 0.4, 0.0, -1.2, 0.0, 1.8, 0.5])
            self.data.ctrl[:7] = default_joints

            for _ in range(100):
                mujoco.mj_step(self.model, self.data)

            mujoco.mj_forward(self.model, self.data)
            self._show_status()
        except ValueError as e:
            print("解析错误: %s" % str(e))

    def _show_status(self):
        """显示状态"""
        # 获取 ee_center_body 位置
        ee_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "ee_center_body")
        ee_pos = self.data.xpos[ee_id]

        print("-" * 40)
        print("末端执行器位置: x=%.3f, y=%.3f, z=%.3f" % (ee_pos[0], ee_pos[1], ee_pos[2]))
        print("关节角度: %s" % str(self.data.qpos[:7]))
        print("夹爪开度: %.4f" % self.data.ctrl[7])
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
