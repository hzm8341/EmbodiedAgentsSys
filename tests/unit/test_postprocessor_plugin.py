"""
Week 9 Task 3.2：Postprocessor 插件测试

验证结果后处理插件的功能：
- 结果格式化
- 结果聚合
- 置信度过滤
- 结果转换
"""

import pytest


class TestPostprocessorPluginBasics:
    """Postprocessor 插件基本功能"""

    @pytest.mark.asyncio
    async def test_postprocessor_initialization(self):
        """PostprocessorPlugin 可以初始化"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        assert plugin is not None
        assert plugin.name == "postprocessor"

    @pytest.mark.asyncio
    async def test_format_results(self):
        """结果格式化功能"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        raw_results = {
            "detections": [
                {"class": "obj1", "score": 0.95},
                {"class": "obj2", "score": 0.87},
            ]
        }

        result = await plugin.execute(operation="format", data=raw_results)

        assert result.get("success") is True
        assert "formatted_data" in result

    @pytest.mark.asyncio
    async def test_aggregate_results(self):
        """结果聚合功能"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        results_list = [
            {"value": 10, "weight": 1.0},
            {"value": 20, "weight": 1.0},
            {"value": 30, "weight": 1.0},
        ]

        result = await plugin.execute(operation="aggregate", data=results_list)

        assert result.get("success") is True
        assert "aggregated_result" in result
        assert result.get("aggregated_result").get("mean") == 20.0

    @pytest.mark.asyncio
    async def test_filter_by_confidence(self):
        """置信度过滤功能"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        detections = [
            {"id": 1, "confidence": 0.95},
            {"id": 2, "confidence": 0.45},
            {"id": 3, "confidence": 0.85},
        ]

        result = await plugin.execute(
            operation="filter",
            data=detections,
            threshold=0.8
        )

        assert result.get("success") is True
        assert len(result.get("filtered_results")) == 2

    @pytest.mark.asyncio
    async def test_transform_results(self):
        """结果转换功能"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        raw_data = {
            "x": 100,
            "y": 200,
            "z": 50,
        }

        result = await plugin.execute(
            operation="transform",
            data=raw_data,
            scale=0.1
        )

        assert result.get("success") is True
        assert "transformed_data" in result


class TestPostprocessorPluginFiltering:
    """Postprocessor 插件过滤功能"""

    @pytest.mark.asyncio
    async def test_filter_multiple_types(self):
        """支持多种过滤类型"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        # 按置信度过滤
        detections = [
            {"id": 1, "confidence": 0.95},
            {"id": 2, "confidence": 0.45},
            {"id": 3, "confidence": 0.85},
        ]

        result = await plugin.execute(
            operation="filter",
            data=detections,
            threshold=0.8,
            filter_type="confidence"
        )

        assert result.get("success") is True
        assert len(result.get("filtered_results")) == 2

    @pytest.mark.asyncio
    async def test_remove_duplicates(self):
        """移除重复结果"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        results = [
            {"id": "obj1", "value": 10},
            {"id": "obj1", "value": 10},  # 重复
            {"id": "obj2", "value": 20},
        ]

        result = await plugin.execute(
            operation="filter",
            data=results,
            filter_type="duplicates"
        )

        assert result.get("success") is True
        assert len(result.get("filtered_results")) == 2


class TestPostprocessorPluginMetadata:
    """Postprocessor 插件元数据"""

    def test_postprocessor_plugin_metadata(self):
        """Postprocessor 插件有正确的元数据"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()

        assert plugin.name == "postprocessor"
        assert plugin.version is not None
        assert plugin.description is not None
        assert len(plugin.description) > 0

    def test_postprocessor_is_plugin_base(self):
        """Postprocessor 继承自 PluginBase"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin
        from agents.extensions.plugin import PluginBase

        assert issubclass(PostprocessorPlugin, PluginBase)


class TestPostprocessorPluginIntegration:
    """Postprocessor 插件与插件框架的集成"""

    @pytest.mark.asyncio
    async def test_postprocessor_with_plugin_registry(self):
        """Postprocessor 插件可以注册到 PluginRegistry"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin
        from agents.extensions.registry import PluginRegistry

        registry = PluginRegistry()
        plugin = PostprocessorPlugin()

        await plugin.initialize()
        registry.register(plugin.name, plugin)

        retrieved = registry.get(plugin.name)
        assert retrieved is plugin

    @pytest.mark.asyncio
    async def test_postprocessor_with_plugin_loader(self):
        """Postprocessor 插件可以通过 PluginLoader 加载"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin
        from agents.extensions.loader import PluginLoader

        loader = PluginLoader()
        plugin = PostprocessorPlugin()

        loader.register_plugin(plugin)

        loaded = loader.get_plugin(plugin.name)
        assert loaded is plugin

    @pytest.mark.asyncio
    async def test_postprocessor_cleanup(self):
        """Postprocessor 插件支持清理资源"""
        from agents.extensions.postprocessor_plugin import PostprocessorPlugin

        plugin = PostprocessorPlugin()
        await plugin.initialize()

        # 执行一些操作
        data = {"value": 10}
        await plugin.execute(operation="format", data=data)

        # 清理资源
        await plugin.cleanup()

        # 验证清理后状态
        assert plugin is not None
