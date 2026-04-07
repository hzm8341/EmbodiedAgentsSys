"""
Week 9 Task 3.3：Visualization 插件测试

验证数据可视化插件的功能：
- 生成图表数据
- 生成统计报告
- 生成可视化配置
- 导出可视化文件
"""

import pytest


class TestVisualizationPluginBasics:
    """Visualization 插件基本功能"""

    @pytest.mark.asyncio
    async def test_visualization_initialization(self):
        """VisualizationPlugin 可以初始化"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        assert plugin is not None
        assert plugin.name == "visualization"

    @pytest.mark.asyncio
    async def test_generate_chart_data(self):
        """生成图表数据"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(operation="generate_chart", data=data)

        assert result.get("success") is True
        assert "chart_data" in result
        assert result.get("chart_type") is not None

    @pytest.mark.asyncio
    async def test_generate_statistics(self):
        """生成统计报告"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(operation="statistics", data=data)

        assert result.get("success") is True
        assert "statistics" in result
        assert "mean" in result["statistics"]
        assert "std" in result["statistics"]

    @pytest.mark.asyncio
    async def test_generate_config(self):
        """生成可视化配置"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        result = await plugin.execute(
            operation="config",
            chart_type="line",
            title="Sample Chart"
        )

        assert result.get("success") is True
        assert "config" in result
        assert result.get("chart_type") == "line"

    @pytest.mark.asyncio
    async def test_export_visualization(self):
        """导出可视化文件"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(
            operation="export",
            data=data,
            format="json"
        )

        assert result.get("success") is True
        assert "export_path" in result
        assert result.get("format") == "json"


class TestVisualizationChartTypes:
    """Visualization 插件支持多种图表类型"""

    @pytest.mark.asyncio
    async def test_line_chart(self):
        """支持折线图"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(
            operation="generate_chart",
            data=data,
            chart_type="line"
        )

        assert result.get("success") is True
        assert result.get("chart_type") == "line"

    @pytest.mark.asyncio
    async def test_bar_chart(self):
        """支持柱状图"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(
            operation="generate_chart",
            data=data,
            chart_type="bar"
        )

        assert result.get("success") is True
        assert result.get("chart_type") == "bar"

    @pytest.mark.asyncio
    async def test_scatter_plot(self):
        """支持散点图"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [[1, 2], [2, 4], [3, 6], [4, 8]]
        result = await plugin.execute(
            operation="generate_chart",
            data=data,
            chart_type="scatter"
        )

        assert result.get("success") is True
        assert result.get("chart_type") == "scatter"


class TestVisualizationStatistics:
    """Visualization 插件统计功能"""

    @pytest.mark.asyncio
    async def test_calculate_mean(self):
        """计算平均值"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(operation="statistics", data=data)

        stats = result.get("statistics")
        assert stats.get("mean") == 30.0

    @pytest.mark.asyncio
    async def test_calculate_std(self):
        """计算标准差"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        data = [10, 20, 30, 40, 50]
        result = await plugin.execute(operation="statistics", data=data)

        stats = result.get("statistics")
        assert "std" in stats
        assert stats["std"] > 0


class TestVisualizationPluginMetadata:
    """Visualization 插件元数据"""

    def test_visualization_plugin_metadata(self):
        """Visualization 插件有正确的元数据"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()

        assert plugin.name == "visualization"
        assert plugin.version is not None
        assert plugin.description is not None
        assert len(plugin.description) > 0

    def test_visualization_is_plugin_base(self):
        """Visualization 继承自 PluginBase"""
        from agents.extensions.visualization_plugin import VisualizationPlugin
        from agents.extensions.plugin import PluginBase

        assert issubclass(VisualizationPlugin, PluginBase)


class TestVisualizationPluginIntegration:
    """Visualization 插件与插件框架的集成"""

    @pytest.mark.asyncio
    async def test_visualization_with_plugin_registry(self):
        """Visualization 插件可以注册到 PluginRegistry"""
        from agents.extensions.visualization_plugin import VisualizationPlugin
        from agents.extensions.registry import PluginRegistry

        registry = PluginRegistry()
        plugin = VisualizationPlugin()

        await plugin.initialize()
        registry.register(plugin.name, plugin)

        retrieved = registry.get(plugin.name)
        assert retrieved is plugin

    @pytest.mark.asyncio
    async def test_visualization_with_plugin_loader(self):
        """Visualization 插件可以通过 PluginLoader 加载"""
        from agents.extensions.visualization_plugin import VisualizationPlugin
        from agents.extensions.loader import PluginLoader

        loader = PluginLoader()
        plugin = VisualizationPlugin()

        loader.register_plugin(plugin)

        loaded = loader.get_plugin(plugin.name)
        assert loaded is plugin

    @pytest.mark.asyncio
    async def test_visualization_cleanup(self):
        """Visualization 插件支持清理资源"""
        from agents.extensions.visualization_plugin import VisualizationPlugin

        plugin = VisualizationPlugin()
        await plugin.initialize()

        # 执行一些操作
        data = [10, 20, 30]
        await plugin.execute(operation="generate_chart", data=data)

        # 清理资源
        await plugin.cleanup()

        # 验证清理后状态
        assert plugin is not None
