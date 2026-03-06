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
    adapter = VLAAdapterBase(config={})
    assert hasattr(adapter, "reset")
    assert hasattr(adapter, "act")
    assert hasattr(adapter, "execute")
    assert hasattr(adapter, "action_dim")
