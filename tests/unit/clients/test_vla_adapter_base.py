# tests/test_vla_adapter_base.py
"""VLA Adapter 基类测试"""
import pytest
from abc import ABC


def test_vla_adapter_is_abc():
    """验证VLAAdapterBase是抽象基类"""
    from agents.clients.vla_adapters.base import VLAAdapterBase
    assert issubclass(VLAAdapterBase, ABC)


def test_vla_adapter_base_methods():
    """验证基类定义了必要方法"""
    from agents.clients.vla_adapters.base import VLAAdapterBase
    # Abstract class cannot be instantiated; check the class interface directly
    assert hasattr(VLAAdapterBase, "reset")
    assert hasattr(VLAAdapterBase, "act")
    assert hasattr(VLAAdapterBase, "execute")
    assert hasattr(VLAAdapterBase, "action_dim")
