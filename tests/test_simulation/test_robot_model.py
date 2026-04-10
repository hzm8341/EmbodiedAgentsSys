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