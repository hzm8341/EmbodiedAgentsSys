# tests/test_act_adapter.py
"""ACT VLA 适配器测试"""
import pytest
import numpy as np


def test_act_adapter_init():
    """验证ACT适配器初始化"""
    from agents.clients.vla_adapters.act import ACTVLAAdapter

    adapter = ACTVLAAdapter(config={
        "model_path": "/models/act",
        "chunk_size": 100,
        "horizon": 1,
        "action_dim": 7
    })

    assert adapter.model_path == "/models/act"
    assert adapter.chunk_size == 100
    assert adapter.horizon == 1
    assert adapter.action_dim == 7


def test_act_adapter_default_values():
    """验证ACT适配器默认值"""
    from agents.clients.vla_adapters.act import ACTVLAAdapter

    adapter = ACTVLAAdapter(config={})

    assert adapter.chunk_size == 100
    assert adapter.horizon == 1
    assert adapter.state_dim == 14
    assert adapter.action_dim == 7


def test_act_adapter_reset():
    """验证ACT适配器重置"""
    from agents.clients.vla_adapters.act import ACTVLAAdapter

    adapter = ACTVLAAdapter(config={"action_dim": 7})
    adapter.reset()

    assert adapter._initialized is True


def test_act_adapter_act():
    """验证ACT适配器act方法"""
    from agents.clients.vla_adapters.act import ACTVLAAdapter

    adapter = ACTVLAAdapter(config={"action_dim": 7})

    observation = {
        "joint_positions": np.zeros(7),
        "joint_velocities": np.zeros(7)
    }

    action = adapter.act(observation, "test skill")

    assert isinstance(action, np.ndarray)
    assert action.shape == (7,)


def test_act_adapter_extract_state():
    """验证状态提取"""
    from agents.clients.vla_adapters.act import ACTVLAAdapter

    adapter = ACTVLAAdapter(config={})

    observation = {
        "joint_positions": np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]),
        "joint_velocities": np.array([0.01, 0.02, 0.03, 0.0, 0.0, 0.0, 0.0])
    }

    state = adapter._extract_state(observation)

    assert state.shape == (14,)
    assert np.allclose(state[:7], observation["joint_positions"])
    assert np.allclose(state[7:], observation["joint_velocities"])


def test_act_adapter_execute():
    """验证ACT适配器执行"""
    from agents.clients.vla_adapters.act import ACTVLAAdapter

    adapter = ACTVLAAdapter(config={"action_dim": 7})

    action = np.zeros(7)
    result = adapter.execute(action)

    assert result["status"] == "executed"
    assert result["model"] == "ACT"
    assert len(result["action"]) == 7
