# tests/test_gr00t_adapter.py
"""GR00T VLA 适配器测试"""
import pytest
import numpy as np


def test_gr00t_adapter_init():
    """验证GR00T适配器初始化"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={
        "model_path": "/models/gr00t",
        "inference_steps": 10,
        "action_dim": 7,
        "action_horizon": 8
    })

    assert adapter.model_path == "/models/gr00t"
    assert adapter.inference_steps == 10
    assert adapter.action_dim == 7
    assert adapter.action_horizon == 8


def test_gr00t_adapter_default_values():
    """验证GR00T适配器默认值"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={})

    assert adapter.inference_steps == 10
    assert adapter.action_dim == 7
    assert adapter.action_horizon == 8


def test_gr00t_adapter_reset():
    """验证GR00T适配器重置"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={"action_dim": 7})
    adapter.reset()

    assert adapter._initialized is True


def test_gr00t_adapter_act():
    """验证GR00T适配器act方法"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={"action_dim": 7})

    observation = {
        "image": np.zeros((224, 224, 3)),
        "joint_positions": np.zeros(7),
        "joint_velocities": np.zeros(7),
        "end_effector_pose": np.zeros(6)
    }

    action = adapter.act(observation, "grasp the cube")

    assert isinstance(action, np.ndarray)
    assert action.shape == (7,)


def test_gr00t_adapter_extract_visual():
    """验证视觉特征提取"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={})

    # 有图像
    observation_with_image = {"image": np.zeros((224, 224, 3))}
    features = adapter._extract_visual(observation_with_image)
    assert features.shape == (512,)

    # 无图像
    observation_no_image = {}
    features = adapter._extract_visual(observation_no_image)
    assert features.shape == (512,)


def test_gr00t_adapter_encode_language():
    """验证语言编码"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={})

    embedding = adapter._encode_language("grasp the cube")

    assert embedding.shape == (512,)


def test_gr00t_adapter_extract_proprioception():
    """验证本体感知提取"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={})

    observation = {
        "joint_positions": np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]),
        "joint_velocities": np.array([0.01, 0.02, 0.03, 0.0, 0.0, 0.0, 0.0]),
        "end_effector_pose": np.array([0.3, 0.0, 0.2, 0.0, 0.0, 0.0])
    }

    proprio = adapter._extract_proprioception(observation)

    assert proprio.shape == (20,)  # 7 + 7 + 6


def test_gr00t_adapter_execute():
    """验证GR00T适配器执行"""
    from agents.clients.vla_adapters.gr00t import GR00TVLAAdapter

    adapter = GR00TVLAAdapter(config={"action_dim": 7, "inference_steps": 10})

    action = np.zeros(7)
    result = adapter.execute(action)

    assert result["status"] == "executed"
    assert result["model"] == "GR00T"
    assert result["inference_steps"] == 10
    assert len(result["action"]) == 7
