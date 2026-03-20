# tests/test_environment.py
"""环境验证测试"""
import pytest


@pytest.mark.skipif(
    not __import__("shutil").which("ros2"),
    reason="sugarcoat requires ROS2/rclpy which is not installed",
)
def test_sugarcoat_import():
    """验证Sugarcoat依赖可用"""
    from sugarcoat import Node
    assert Node is not None


def test_agents_module_import():
    """验证EmbodiedAgentsSys模块可导入"""
    import agents
    assert agents is not None
    assert hasattr(agents, "check_sugarcoat_version")


def test_vla_adapters_import():
    """验证VLA适配器模块可导入"""
    from agents.clients.vla_adapters import VLAAdapterBase, LeRobotVLAAdapter
    assert VLAAdapterBase is not None
    assert LeRobotVLAAdapter is not None
