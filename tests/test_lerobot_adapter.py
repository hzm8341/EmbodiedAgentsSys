# tests/test_lerobot_adapter.py
"""LeRobot VLA 适配器测试"""
import pytest
import numpy as np


def test_lerobot_adapter_init():
    """验证LeRobot适配器初始化"""
    from agents.clients.vla_adapters.lerobot import LeRobotVLAAdapter

    adapter = LeRobotVLAAdapter(
        config={
            "policy_name": "test_policy",
            "checkpoint": "test/checkpoint",
            "host": "127.0.0.1",
            "port": 8080,
        }
    )
    assert adapter.config["policy_name"] == "test_policy"
    assert adapter.policy_name == "test_policy"
    assert adapter.checkpoint == "test/checkpoint"
    assert adapter.host == "127.0.0.1"
    assert adapter.port == 8080


def test_lerobot_adapter_action_dim():
    """验证动作维度"""
    from agents.clients.vla_adapters.lerobot import LeRobotVLAAdapter

    adapter = LeRobotVLAAdapter(config={"action_dim": 7})
    assert adapter.action_dim == 7


def test_lerobot_adapter_act():
    """验证act方法返回正确形状"""
    from agents.clients.vla_adapters.lerobot import LeRobotVLAAdapter

    adapter = LeRobotVLAAdapter(config={"action_dim": 7})
    observation = {"image": np.zeros((224, 224, 3))}
    action = adapter.act(observation, "test skill")
    assert isinstance(action, np.ndarray)
    assert action.shape == (7,)
