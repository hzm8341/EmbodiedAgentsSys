"""
周 3 任务：扩展框架测试

RED 阶段：编写扩展框架的失败测试
目标：验证插件加载和扩展机制
"""

import pytest


class TestPluginFramework:
    """插件框架测试"""

    def test_plugin_base_exists(self):
        """插件基类存在"""
        from agents.extensions.plugin import PluginBase

        assert PluginBase is not None

    def test_plugin_registry_exists(self):
        """插件注册表存在"""
        from agents.extensions.registry import PluginRegistry

        registry = PluginRegistry()
        assert registry is not None

    def test_plugin_loader_exists(self):
        """插件加载器存在"""
        from agents.extensions.loader import PluginLoader

        loader = PluginLoader()
        assert loader is not None


class TestPluginBase:
    """插件基类测试"""

    def test_plugin_has_metadata(self):
        """插件应该有元数据"""
        from agents.extensions.plugin import PluginBase

        class TestPlugin(PluginBase):
            name = "test_plugin"
            version = "1.0.0"
            description = "Test plugin"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "executed"

        plugin = TestPlugin()
        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_plugin_initialization(self):
        """插件可以初始化"""
        from agents.extensions.plugin import PluginBase

        class TestPlugin(PluginBase):
            name = "init_plugin"
            version = "1.0.0"

            async def initialize(self, config=None):
                self.initialized = True

            async def execute(self, *args, **kwargs):
                return "done"

        plugin = TestPlugin()
        await plugin.initialize()
        assert plugin.initialized is True

    @pytest.mark.asyncio
    async def test_plugin_execution(self):
        """插件可以执行"""
        from agents.extensions.plugin import PluginBase

        class TestPlugin(PluginBase):
            name = "exec_plugin"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, input_data=None):
                return f"processed: {input_data}"

        plugin = TestPlugin()
        result = await plugin.execute(input_data="test")
        assert "processed" in result


class TestPluginRegistry:
    """插件注册表测试"""

    def test_registry_register_plugin(self):
        """注册表可以注册插件"""
        from agents.extensions.registry import PluginRegistry
        from agents.extensions.plugin import PluginBase

        class SimplePlugin(PluginBase):
            name = "simple"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "simple"

        registry = PluginRegistry()
        plugin = SimplePlugin()
        registry.register(plugin.name, plugin)

        assert registry.get("simple") is not None

    def test_registry_get_plugin(self):
        """注册表可以获取插件"""
        from agents.extensions.registry import PluginRegistry
        from agents.extensions.plugin import PluginBase

        class MyPlugin(PluginBase):
            name = "myplugin"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "result"

        registry = PluginRegistry()
        plugin = MyPlugin()
        registry.register("myplugin", plugin)

        retrieved = registry.get("myplugin")
        assert retrieved is plugin

    def test_registry_list_plugins(self):
        """注册表可以列出所有插件"""
        from agents.extensions.registry import PluginRegistry
        from agents.extensions.plugin import PluginBase

        class PluginA(PluginBase):
            name = "plugin_a"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "a"

        class PluginB(PluginBase):
            name = "plugin_b"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "b"

        registry = PluginRegistry()
        registry.register("a", PluginA())
        registry.register("b", PluginB())

        plugins = registry.list_plugins()
        assert len(plugins) == 2
        assert "a" in plugins
        assert "b" in plugins


class TestPluginLoader:
    """插件加载器测试"""

    def test_loader_can_load_plugin(self):
        """加载器可以加载插件"""
        from agents.extensions.loader import PluginLoader
        from agents.extensions.plugin import PluginBase

        class LoadablePlugin(PluginBase):
            name = "loadable"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "loaded"

        loader = PluginLoader()
        plugin = LoadablePlugin()
        loader.register_plugin(plugin)

        retrieved = loader.get_plugin("loadable")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_loader_initializes_plugin(self):
        """加载器可以初始化插件"""
        from agents.extensions.loader import PluginLoader
        from agents.extensions.plugin import PluginBase

        class InitPlugin(PluginBase):
            name = "init_plugin"
            version = "1.0.0"

            async def initialize(self, config=None):
                self.config = config

            async def execute(self, *args, **kwargs):
                return "exec"

        loader = PluginLoader()
        plugin = InitPlugin()
        loader.register_plugin(plugin)

        config = {"key": "value"}
        await loader.initialize_plugin("init_plugin", config)

        assert plugin.config == config

    def test_loader_manages_multiple_plugins(self):
        """加载器可以管理多个插件"""
        from agents.extensions.loader import PluginLoader
        from agents.extensions.plugin import PluginBase

        class Plugin1(PluginBase):
            name = "p1"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "p1"

        class Plugin2(PluginBase):
            name = "p2"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, *args, **kwargs):
                return "p2"

        loader = PluginLoader()
        loader.register_plugin(Plugin1())
        loader.register_plugin(Plugin2())

        plugins = loader.list_plugins()
        assert len(plugins) == 2


class TestPluginIntegration:
    """插件集成测试"""

    @pytest.mark.asyncio
    async def test_full_plugin_lifecycle(self):
        """完整的插件生命周期"""
        from agents.extensions.loader import PluginLoader
        from agents.extensions.plugin import PluginBase

        class WorkflowPlugin(PluginBase):
            name = "workflow"
            version = "1.0.0"

            async def initialize(self, config=None):
                self.initialized = True
                self.config = config

            async def execute(self, data=None):
                return f"processed: {data}"

        loader = PluginLoader()
        plugin = WorkflowPlugin()
        loader.register_plugin(plugin)

        # 初始化
        await loader.initialize_plugin("workflow", {"mode": "test"})
        assert plugin.initialized is True

        # 执行
        retrieved = loader.get_plugin("workflow")
        result = await retrieved.execute(data="test_data")
        assert "processed" in result

    @pytest.mark.asyncio
    async def test_plugin_composition(self, dummy_config):
        """插件可以在代理中组合"""
        from agents.extensions.loader import PluginLoader
        from agents.extensions.plugin import PluginBase

        class PreprocessorPlugin(PluginBase):
            name = "preprocessor"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, data):
                return f"preprocessed: {data}"

        class PostprocessorPlugin(PluginBase):
            name = "postprocessor"
            version = "1.0.0"

            async def initialize(self, config=None):
                pass

            async def execute(self, data):
                return f"postprocessed: {data}"

        loader = PluginLoader()
        loader.register_plugin(PreprocessorPlugin())
        loader.register_plugin(PostprocessorPlugin())

        # 执行插件管道
        pre = loader.get_plugin("preprocessor")
        post = loader.get_plugin("postprocessor")

        result1 = await pre.execute("input")
        result2 = await post.execute(result1)

        assert "postprocessed" in result2
