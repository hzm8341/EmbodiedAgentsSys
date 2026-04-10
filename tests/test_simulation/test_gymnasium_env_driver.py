"""测试 GymnasiumEnvDriver"""

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

    def test_grasp_action(self):
        """grasp 应该成功执行"""
        driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")
        driver.reset()
        receipt = driver.execute_action("grasp", {})
        assert receipt.status == ExecutionStatus.SUCCESS

    def test_release_action(self):
        """release 应该成功执行"""
        driver = GymnasiumEnvDriver(env_name="FrankaPushSparse-v0")
        driver.reset()
        receipt = driver.execute_action("release", {})
        assert receipt.status == ExecutionStatus.SUCCESS
