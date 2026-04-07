# tests/test_plugins.py
import asyncio
import pytest
from agents.plugins.base import Plugin, Hook, HookEvent
from agents.plugins.registry import PluginRegistry


class ConcretePlugin(Plugin):
    name = "test-plugin"
    version = "1.0.0"
    description = "A test plugin"

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.initialized = False

    def get_tools(self):
        return []

    def get_skills(self):
        return []

    def get_hooks(self):
        return []


class TestPlugin:
    def test_plugin_initialize(self):
        p = ConcretePlugin()
        asyncio.run(p.initialize())
        assert p.initialized is True

    def test_plugin_shutdown(self):
        p = ConcretePlugin()
        asyncio.run(p.initialize())
        asyncio.run(p.shutdown())
        assert p.initialized is False


class TestPluginRegistry:
    def test_register_and_list(self):
        reg = PluginRegistry()
        p = ConcretePlugin()
        reg.register(p)
        assert "test-plugin" in [pl.name for pl in reg.get_all()]

    def test_enable_persists_state(self, tmp_path):
        reg = PluginRegistry(config_path=tmp_path / "plugins.yaml")
        p = ConcretePlugin()
        reg.register(p)
        reg.enable("test-plugin")
        assert "test-plugin" in [pl.name for pl in reg.get_enabled()]

    def test_disable_removes_from_enabled(self, tmp_path):
        reg = PluginRegistry(config_path=tmp_path / "plugins.yaml")
        p = ConcretePlugin()
        reg.register(p)
        reg.enable("test-plugin")
        reg.disable("test-plugin")
        assert "test-plugin" not in [pl.name for pl in reg.get_enabled()]

    def test_initialize_all_calls_enabled_plugins(self, tmp_path):
        reg = PluginRegistry(config_path=tmp_path / "plugins.yaml")
        p = ConcretePlugin()
        reg.register(p)
        reg.enable("test-plugin")
        asyncio.run(reg.initialize_all())
        assert p.initialized is True

    def test_get_plugin_by_name(self):
        reg = PluginRegistry()
        p = ConcretePlugin()
        reg.register(p)
        found = reg.get("test-plugin")
        assert found is p

    def test_get_unknown_returns_none(self):
        reg = PluginRegistry()
        assert reg.get("unknown") is None


class TestBuiltinPlugins:
    def test_vla_plugin_has_correct_name(self):
        from agents.plugins.builtin.vla_plugin import VLAPlugin
        p = VLAPlugin()
        assert p.name == "vla"
        assert p.version != ""

    def test_llm_plugin_has_correct_name(self):
        from agents.plugins.builtin.llm_plugin import LLMPlugin
        p = LLMPlugin()
        assert p.name == "llm"

    def test_sensor_plugin_has_correct_name(self):
        from agents.plugins.builtin.sensor_plugin import SensorPlugin
        p = SensorPlugin()
        assert p.name == "sensor"

    def test_vla_plugin_provides_tools(self):
        from agents.plugins.builtin.vla_plugin import VLAPlugin
        p = VLAPlugin()
        tools = p.get_tools()
        names = [t["name"] for t in tools]
        assert "start_policy" in names
        assert "change_policy" in names

    def test_llm_plugin_provides_tools(self):
        from agents.plugins.builtin.llm_plugin import LLMPlugin
        p = LLMPlugin()
        tools = p.get_tools()
        assert any(t["name"] == "llm_query" for t in tools)

    def test_sensor_plugin_provides_tools(self):
        from agents.plugins.builtin.sensor_plugin import SensorPlugin
        p = SensorPlugin()
        tools = p.get_tools()
        assert any(t["name"] == "env_summary" for t in tools)
