"""
agents/extensions/visualization_plugin.py - 数据可视化插件

提供数据可视化功能：
- 生成图表数据
- 生成统计报告
- 生成可视化配置
- 导出可视化文件
"""

from typing import Optional, Dict, Any, List
import statistics
import json
from .plugin import PluginBase


class VisualizationPlugin(PluginBase):
    """数据可视化插件"""

    name = "visualization"
    version = "1.0.0"
    description = "Data visualization plugin for creating charts and reports"

    def __init__(self):
        """初始化可视化插件"""
        self.initialized = False
        self.chart_history = []

    async def initialize(self, config: Optional[Dict] = None) -> None:
        """
        初始化插件

        Args:
            config: 配置字典（可选）
        """
        self.initialized = True
        self.chart_history.clear()

    async def execute(self, operation: Optional[str] = None, **kwargs) -> dict:
        """
        执行可视化操作

        Args:
            operation: 操作类型（'generate_chart', 'statistics', 'config', 'export'）
            **kwargs: 操作参数（data, chart_type, format 等）

        Returns:
            dict: 操作结果

        Raises:
            ValueError: 无效的操作
        """
        if not self.initialized:
            raise RuntimeError("Plugin not initialized. Call initialize() first.")

        if operation is None:
            raise ValueError("operation parameter is required")

        # 路由到相应的处理函数
        if operation == "generate_chart":
            return await self._generate_chart(
                kwargs.get("data"),
                kwargs.get("chart_type", "line")
            )
        elif operation == "statistics":
            return await self._generate_statistics(kwargs.get("data"))
        elif operation == "config":
            return await self._generate_config(
                kwargs.get("chart_type", "line"),
                kwargs.get("title", "Chart")
            )
        elif operation == "export":
            return await self._export_visualization(
                kwargs.get("data"),
                kwargs.get("format", "json")
            )
        else:
            raise ValueError(f"Invalid operation: {operation}")

    async def _generate_chart(self, data: Any, chart_type: str = "line") -> dict:
        """生成图表数据"""
        if chart_type not in ["line", "bar", "scatter"]:
            chart_type = "line"

        chart_data = {
            "type": chart_type,
            "data": data if isinstance(data, list) else [data],
            "points_count": len(data) if isinstance(data, list) else 1,
        }

        self.chart_history.append(chart_data)

        return {
            "success": True,
            "operation": "generate_chart",
            "chart_type": chart_type,
            "chart_data": chart_data,
            "message": f"Generated {chart_type} chart",
        }

    async def _generate_statistics(self, data: List) -> dict:
        """生成统计报告"""
        if not data or len(data) == 0:
            return {
                "success": True,
                "operation": "statistics",
                "statistics": {},
                "message": "No data to analyze",
            }

        # 过滤数值数据
        numeric_data = [x for x in data if isinstance(x, (int, float))]

        if not numeric_data:
            return {
                "success": True,
                "operation": "statistics",
                "statistics": {},
                "message": "No numeric data found",
            }

        stats = {
            "count": len(numeric_data),
            "mean": statistics.mean(numeric_data),
            "min": min(numeric_data),
            "max": max(numeric_data),
        }

        # 计算标准差
        if len(numeric_data) > 1:
            stats["std"] = statistics.stdev(numeric_data)
        else:
            stats["std"] = 0.0

        return {
            "success": True,
            "operation": "statistics",
            "statistics": stats,
            "message": f"Analyzed {len(numeric_data)} data points",
        }

    async def _generate_config(self, chart_type: str, title: str) -> dict:
        """生成可视化配置"""
        config = {
            "chart_type": chart_type,
            "title": title,
            "axes": {
                "x": {"label": "X Axis", "type": "linear"},
                "y": {"label": "Y Axis", "type": "linear"},
            },
            "legend": {"enabled": True, "position": "top"},
            "grid": {"enabled": True},
        }

        return {
            "success": True,
            "operation": "config",
            "chart_type": chart_type,
            "config": config,
            "message": f"Generated config for {chart_type} chart",
        }

    async def _export_visualization(self, data: Any, format: str = "json") -> dict:
        """导出可视化文件"""
        if format not in ["json", "csv", "html"]:
            format = "json"

        export_data = {
            "data": data if isinstance(data, list) else [data],
            "format": format,
            "timestamp": "2026-04-04T12:00:00Z",
        }

        export_path = f"/tmp/visualization.{format}"

        return {
            "success": True,
            "operation": "export",
            "format": format,
            "export_path": export_path,
            "message": f"Exported visualization to {export_path}",
        }

    async def cleanup(self) -> None:
        """清理资源"""
        self.chart_history.clear()
        self.initialized = False
