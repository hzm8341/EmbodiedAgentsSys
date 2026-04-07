"""
agents/extensions/postprocessor_plugin.py - 结果后处理插件

提供结果后处理功能：
- 结果格式化
- 结果聚合
- 置信度过滤
- 结果转换
"""

from typing import Optional, Dict, Any, List
from .plugin import PluginBase


class PostprocessorPlugin(PluginBase):
    """结果后处理插件"""

    name = "postprocessor"
    version = "1.0.0"
    description = "Result postprocessing plugin for formatting, aggregating, and filtering results"

    def __init__(self):
        """初始化后处理插件"""
        self.initialized = False
        self.processing_stats = {}

    async def initialize(self, config: Optional[Dict] = None) -> None:
        """
        初始化插件

        Args:
            config: 配置字典（可选）
        """
        self.initialized = True
        self.processing_stats.clear()

    async def execute(self, operation: Optional[str] = None, **kwargs) -> dict:
        """
        执行后处理操作

        Args:
            operation: 操作类型（'format', 'aggregate', 'filter', 'transform'）
            **kwargs: 操作参数（data, threshold, scale, filter_type 等）

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
        if operation == "format":
            return await self._format_results(kwargs.get("data"))
        elif operation == "aggregate":
            return await self._aggregate_results(kwargs.get("data"))
        elif operation == "filter":
            return await self._filter_results(
                kwargs.get("data"),
                kwargs.get("threshold"),
                kwargs.get("filter_type", "confidence")
            )
        elif operation == "transform":
            return await self._transform_results(
                kwargs.get("data"),
                kwargs.get("scale", 1.0)
            )
        else:
            raise ValueError(f"Invalid operation: {operation}")

    async def _format_results(self, data: Dict) -> dict:
        """格式化结果"""
        formatted = {}

        for key, value in data.items():
            if isinstance(value, list):
                # 格式化列表结果
                formatted[key] = [
                    self._format_item(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                formatted[key] = value

        return {
            "success": True,
            "operation": "format",
            "formatted_data": formatted,
            "message": "Result formatting completed",
        }

    def _format_item(self, item: Dict) -> Dict:
        """格式化单个项"""
        formatted_item = {}
        for key, value in item.items():
            if isinstance(value, float):
                # 四舍五入到 2 位小数
                formatted_item[key] = round(value, 2)
            else:
                formatted_item[key] = value
        return formatted_item

    async def _aggregate_results(self, data: List[Dict]) -> dict:
        """聚合结果"""
        if not data or len(data) == 0:
            return {
                "success": True,
                "operation": "aggregate",
                "aggregated_result": {},
                "message": "No data to aggregate",
            }

        # 计算加权平均
        total_value = 0.0
        total_weight = 0.0

        for item in data:
            value = item.get("value", 0)
            weight = item.get("weight", 1.0)
            total_value += value * weight
            total_weight += weight

        mean = total_value / total_weight if total_weight > 0 else 0

        return {
            "success": True,
            "operation": "aggregate",
            "aggregated_result": {
                "mean": mean,
                "count": len(data),
                "total_weight": total_weight,
            },
            "message": f"Aggregated {len(data)} results",
        }

    async def _filter_results(
        self,
        data: List[Dict],
        threshold: Optional[float] = None,
        filter_type: str = "confidence"
    ) -> dict:
        """过滤结果"""
        if not data:
            return {
                "success": True,
                "operation": "filter",
                "filtered_results": [],
                "message": "No data to filter",
            }

        filtered = []

        if filter_type == "confidence" and threshold is not None:
            # 按置信度过滤
            for item in data:
                if item.get("confidence", 0) >= threshold:
                    filtered.append(item)

        elif filter_type == "duplicates":
            # 移除重复项
            seen = set()
            for item in data:
                item_id = item.get("id")
                if item_id not in seen:
                    filtered.append(item)
                    seen.add(item_id)

        else:
            filtered = data

        return {
            "success": True,
            "operation": "filter",
            "filtered_results": filtered,
            "filtered_count": len(filtered),
            "message": f"Filtered {len(data)} items to {len(filtered)}",
        }

    async def _transform_results(self, data: Dict, scale: float = 1.0) -> dict:
        """转换结果"""
        transformed = {}

        for key, value in data.items():
            if isinstance(value, (int, float)):
                # 缩放数值
                transformed[key] = value * scale
            else:
                transformed[key] = value

        return {
            "success": True,
            "operation": "transform",
            "transformed_data": transformed,
            "scale_factor": scale,
            "message": f"Transformed results with scale {scale}",
        }

    async def cleanup(self) -> None:
        """清理资源"""
        self.processing_stats.clear()
        self.initialized = False
