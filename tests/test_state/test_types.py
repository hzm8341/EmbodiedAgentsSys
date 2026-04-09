"""Tests for state types."""
import pytest
from embodiedagentsys.state.types import ProtocolType, StateEntry


class TestProtocolType:
    def test_protocol_types_defined(self):
        assert ProtocolType.ACTION.value == "action"
        assert ProtocolType.ENVIRONMENT.value == "environment"


class TestStateEntry:
    def test_state_entry_creation(self):
        entry = StateEntry(
            protocol_type=ProtocolType.ACTION,
            content={"action": "move_to"}
        )
        assert entry.protocol_type == ProtocolType.ACTION
        assert entry.content["action"] == "move_to"
