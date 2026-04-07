# tests/test_mcp.py
import asyncio
import json
import pytest
from pathlib import Path
from agents.mcp.config import MCPConfig, MCPScope
from agents.mcp.auth import MCPAuthStore


class TestMCPConfig:
    def test_default_scope_is_project(self):
        cfg = MCPConfig(name="test", command="python", args=["-m", "server"])
        assert cfg.scope == MCPScope.PROJECT

    def test_server_id_is_name(self):
        cfg = MCPConfig(name="my-server", command="npx", args=["server"])
        assert cfg.server_id == "my-server"

    def test_from_dict(self):
        data = {
            "name": "vision",
            "command": "python",
            "args": ["-m", "vision_server"],
            "env": {"MODEL_PATH": "/models"},
            "timeout": 60.0,
            "scope": "global",
        }
        cfg = MCPConfig.from_dict(data)
        assert cfg.name == "vision"
        assert cfg.env["MODEL_PATH"] == "/models"
        assert cfg.scope == MCPScope.GLOBAL
        assert cfg.timeout == 60.0


class TestMCPAuthStore:
    def test_save_and_read_token(self, tmp_path):
        store = MCPAuthStore(tmp_path / "tokens.json")
        store.save_token("server1", "abc123")
        assert store.read_token("server1") == "abc123"

    def test_missing_token_returns_none(self, tmp_path):
        store = MCPAuthStore(tmp_path / "tokens.json")
        assert store.read_token("nonexistent") is None

    def test_clear_token(self, tmp_path):
        store = MCPAuthStore(tmp_path / "tokens.json")
        store.save_token("s1", "tok")
        store.clear_token("s1")
        assert store.read_token("s1") is None

    def test_tokens_persist_across_instances(self, tmp_path):
        path = tmp_path / "tokens.json"
        MCPAuthStore(path).save_token("server", "mytoken")
        assert MCPAuthStore(path).read_token("server") == "mytoken"


class TestMCPClient:
    def test_initial_state_disconnected(self):
        from agents.mcp.client import MCPClient, HealthStatus
        cfg = MCPConfig(name="test", command="echo", args=["hello"])
        client = MCPClient(cfg)
        assert client.health_status == HealthStatus.DISCONNECTED

    def test_disconnect_when_not_connected_is_noop(self):
        from agents.mcp.client import MCPClient
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        asyncio.run(client.disconnect())

    def test_health_check_returns_status(self):
        from agents.mcp.client import MCPClient, HealthStatus
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        status = asyncio.run(client.health_check())
        assert isinstance(status, HealthStatus)

    def test_list_tools_returns_empty_when_disconnected(self):
        from agents.mcp.client import MCPClient
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        tools = asyncio.run(client.list_tools())
        assert tools == []

    def test_call_tool_raises_when_disconnected(self):
        from agents.mcp.client import MCPClient
        from agents.exceptions import HardwareError
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        with pytest.raises(HardwareError):
            asyncio.run(client.call_tool("some_tool", {}))


class TestMCPServerManager:
    def test_add_and_list_servers(self):
        from agents.mcp.server_manager import MCPServerManager
        mgr = MCPServerManager()
        cfg = MCPConfig(name="vision", command="python", args=[])
        mgr.add_server(cfg)
        statuses = mgr.list_servers()
        assert any(s["name"] == "vision" for s in statuses)

    def test_get_server_by_id(self):
        from agents.mcp.server_manager import MCPServerManager
        from agents.mcp.client import MCPClient
        mgr = MCPServerManager()
        mgr.add_server(MCPConfig(name="s1", command="echo", args=[]))
        client = mgr.get_server("s1")
        assert isinstance(client, MCPClient)

    def test_get_nonexistent_returns_none(self):
        from agents.mcp.server_manager import MCPServerManager
        mgr = MCPServerManager()
        assert mgr.get_server("unknown") is None

    def test_remove_server(self):
        from agents.mcp.server_manager import MCPServerManager
        mgr = MCPServerManager()
        mgr.add_server(MCPConfig(name="temp", command="echo", args=[]))
        mgr.remove_server("temp")
        assert mgr.get_server("temp") is None

    def test_check_all_health_returns_dict(self):
        from agents.mcp.server_manager import MCPServerManager
        mgr = MCPServerManager()
        mgr.add_server(MCPConfig(name="s1", command="echo", args=[]))
        results = asyncio.run(mgr.check_all_health())
        assert "s1" in results
