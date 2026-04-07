"""
Week 9 Task 3.1：Preprocessor 插件测试

验证数据预处理插件的功能：
- 数据清理
- 数据标准化
- 数据验证
- 缓存管理
"""

import pytest


class TestPreprocessorPluginBasics:
    """Preprocessor 插件基本功能"""

    @pytest.mark.asyncio
    async def test_preprocessor_initialization(self):
        """PreprocessorPlugin 可以初始化"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        assert plugin is not None
        assert plugin.name == "preprocessor"

    @pytest.mark.asyncio
    async def test_clean_data(self):
        """数据清理功能"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        # 模拟包含噪声的数据
        raw_data = {
            "values": [1.0, None, 3.0, float('nan'), 5.0],
            "labels": ["a", "", "c", "d", None],
        }

        result = await plugin.execute(operation="clean", data=raw_data)

        assert result is not None
        assert result.get("success") is True
        assert "cleaned_data" in result

    @pytest.mark.asyncio
    async def test_normalize_data(self):
        """数据标准化功能"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        data = {"values": [1.0, 2.0, 3.0, 4.0, 5.0]}
        result = await plugin.execute(operation="normalize", data=data)

        assert result.get("success") is True
        assert "normalized_data" in result

    @pytest.mark.asyncio
    async def test_validate_data(self):
        """数据验证功能"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        # 有效的数据
        valid_data = {"temperature": 25.5, "humidity": 60.0}
        result = await plugin.execute(operation="validate", data=valid_data)

        assert result.get("success") is True
        assert result.get("is_valid") is True

    @pytest.mark.asyncio
    async def test_invalid_data_detection(self):
        """检测无效数据"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        # 无效的数据（超出范围）
        invalid_data = {"temperature": 150.0, "humidity": 200.0}
        result = await plugin.execute(operation="validate", data=invalid_data)

        assert result.get("success") is True
        assert result.get("is_valid") is False


class TestPreprocessorPluginCaching:
    """Preprocessor 插件缓存功能"""

    @pytest.mark.asyncio
    async def test_cache_preprocessed_data(self):
        """缓存预处理后的数据"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        data = {"values": [1.0, 2.0, 3.0]}

        # 第一次处理
        result1 = await plugin.execute(operation="normalize", data=data)
        assert result1.get("from_cache") is False

        # 第二次处理（应该来自缓存）
        result2 = await plugin.execute(operation="normalize", data=data)
        assert result2.get("from_cache") is True

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """清空缓存"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        # 填充缓存
        data = {"values": [1.0, 2.0, 3.0]}
        await plugin.execute(operation="normalize", data=data)

        # 清空缓存
        await plugin.execute(operation="clear_cache")

        # 再次处理应该不来自缓存
        result = await plugin.execute(operation="normalize", data=data)
        assert result.get("from_cache") is False


class TestPreprocessorPluginMetadata:
    """Preprocessor 插件元数据"""

    def test_preprocessor_plugin_metadata(self):
        """Preprocessor 插件有正确的元数据"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()

        assert plugin.name == "preprocessor"
        assert plugin.version is not None
        assert plugin.description is not None
        assert len(plugin.description) > 0

    def test_preprocessor_is_plugin_base(self):
        """Preprocessor 继承自 PluginBase"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin
        from agents.extensions.plugin import PluginBase

        assert issubclass(PreprocessorPlugin, PluginBase)


class TestPreprocessorPluginIntegration:
    """Preprocessor 插件与插件框架的集成"""

    @pytest.mark.asyncio
    async def test_preprocessor_with_plugin_registry(self):
        """Preprocessor 插件可以注册到 PluginRegistry"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin
        from agents.extensions.registry import PluginRegistry

        registry = PluginRegistry()
        plugin = PreprocessorPlugin()

        await plugin.initialize()
        registry.register(plugin.name, plugin)

        retrieved = registry.get(plugin.name)
        assert retrieved is plugin

    @pytest.mark.asyncio
    async def test_preprocessor_with_plugin_loader(self):
        """Preprocessor 插件可以通过 PluginLoader 加载"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin
        from agents.extensions.loader import PluginLoader

        loader = PluginLoader()
        plugin = PreprocessorPlugin()

        loader.register_plugin(plugin)

        loaded = loader.get_plugin(plugin.name)
        assert loaded is plugin

    @pytest.mark.asyncio
    async def test_preprocessor_cleanup(self):
        """Preprocessor 插件支持清理资源"""
        from agents.extensions.preprocessor_plugin import PreprocessorPlugin

        plugin = PreprocessorPlugin()
        await plugin.initialize()

        # 执行一些操作
        data = {"values": [1.0, 2.0, 3.0]}
        await plugin.execute(operation="normalize", data=data)

        # 清理资源
        await plugin.cleanup()

        # 验证清理后状态
        assert plugin is not None
