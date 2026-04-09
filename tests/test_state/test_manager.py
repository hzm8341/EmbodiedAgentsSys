"""Tests for StateManager."""
import pytest
from embodiedagentsys.state.manager import StateManager
from embodiedagentsys.state.types import ProtocolType


class TestStateManager:
    def test_manager_creation(self):
        manager = StateManager()
        assert manager is not None

    def test_enable_files_false_by_default(self):
        manager = StateManager()
        assert manager._enable_files is False

    def test_write_and_read_memory(self):
        manager = StateManager(enable_state_files=False)
        manager.write_protocol(ProtocolType.ACTION, {"action": "test"})
        content = manager.read_protocol(ProtocolType.ACTION)
        assert content["action"] == "test"

    def test_read_empty_returns_dict(self):
        manager = StateManager()
        content = manager.read_protocol(ProtocolType.ACTION)
        assert content == {}
