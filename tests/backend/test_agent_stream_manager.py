"""Tests for AgentStreamManager."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from backend.services.websocket_manager import AgentStreamManager


class MockWebSocket:
    def __init__(self, fail_on_send=False):
        self.accepted = False
        self.sent_messages = []
        self.fail_on_send = fail_on_send

    async def accept(self):
        self.accepted = True

    async def send_text(self, data):
        if self.fail_on_send:
            raise RuntimeError("send failed")
        self.sent_messages.append(data)


async def test_connect_accepts_and_registers():
    mgr = AgentStreamManager()
    ws = MockWebSocket()
    await mgr.connect(ws)
    assert ws.accepted is True
    assert ws in mgr.active_connections


async def test_disconnect_removes():
    mgr = AgentStreamManager()
    ws = MockWebSocket()
    await mgr.connect(ws)
    mgr.disconnect(ws)
    assert ws not in mgr.active_connections


async def test_disconnect_nonexistent_is_safe():
    mgr = AgentStreamManager()
    ws = MockWebSocket()
    # Disconnecting without connecting first should not raise
    mgr.disconnect(ws)


async def test_broadcast_sends_json_to_all():
    mgr = AgentStreamManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    await mgr.connect(ws1)
    await mgr.connect(ws2)

    message = {"type": "planning", "data": {"plan": [1, 2, 3]}}
    await mgr.broadcast(message)

    assert len(ws1.sent_messages) == 1
    assert len(ws2.sent_messages) == 1
    assert json.loads(ws1.sent_messages[0]) == message
    assert json.loads(ws2.sent_messages[0]) == message


async def test_broadcast_empty_is_safe():
    mgr = AgentStreamManager()
    await mgr.broadcast({"type": "test"})  # no connections, no error


async def test_broadcast_removes_failed_clients():
    mgr = AgentStreamManager()
    ws_ok = MockWebSocket()
    ws_bad = MockWebSocket(fail_on_send=True)
    await mgr.connect(ws_ok)
    await mgr.connect(ws_bad)

    await mgr.broadcast({"type": "x"})

    assert ws_ok in mgr.active_connections
    assert ws_bad not in mgr.active_connections


def test_singleton_instance_exists():
    from backend.services.websocket_manager import agent_stream_manager
    assert isinstance(agent_stream_manager, AgentStreamManager)


def test_original_manager_untouched():
    """Existing WebSocketManager and its instance must remain intact."""
    from backend.services.websocket_manager import WebSocketManager, manager
    assert isinstance(manager, WebSocketManager)
    assert hasattr(manager, 'active_connections')
    assert hasattr(manager, 'connect')
    assert hasattr(manager, 'send_state')
