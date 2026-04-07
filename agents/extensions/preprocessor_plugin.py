"""
agents/extensions/preprocessor_plugin.py - 数据预处理插件

提供数据预处理功能：
- 数据清理（处理缺失值、异常值）
- 数据标准化（归一化）
- 数据验证（范围检查）
- 缓存管理
"""

from typing import Optional, Dict, Any
import hashlib
import json
from .plugin import PluginBase


class PreprocessorPlugin(PluginBase):
    """数据预处理插件"""

    name = "preprocessor"
    version = "1.0.0"
    description = "Data preprocessing plugin for cleaning, normalizing, and validating data"

    def __init__(self):
        """初始化预处理插件"""
        self.cache = {}
        self.initialized = False
        self.data_stats = {}

    async def initialize(self, config: Optional[Dict] = None) -> None:
        """
        初始化插件

        Args:
            config: 配置字典（可选）
        """
        self.initialized = True
        self.cache.clear()
        self.data_stats.clear()

    async def execute(self, operation: Optional[str] = None, **kwargs) -> dict:
        """
        执行预处理操作

        Args:
            operation: 操作类型（'clean', 'normalize', 'validate', 'clear_cache'）
            **kwargs: 操作参数（data, config 等）

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
        if operation == "clean":
            return await self._clean_data(kwargs.get("data"))
        elif operation == "normalize":
            return await self._normalize_data(kwargs.get("data"))
        elif operation == "validate":
            return await self._validate_data(kwargs.get("data"))
        elif operation == "clear_cache":
            return await self._clear_cache()
        else:
            raise ValueError(f"Invalid operation: {operation}")

    async def _clean_data(self, data: Dict) -> dict:
        """清理数据"""
        import math

        cleaned = {}

        for key, value in data.items():
            if isinstance(value, list):
                # 清理列表：移除 None、NaN 等
                cleaned_list = []
                for item in value:
                    if item is not None and not (
                        isinstance(item, float) and math.isnan(item)
                    ):
                        cleaned_list.append(item)
                cleaned[key] = cleaned_list
            elif isinstance(value, str):
                # 清理字符串：移除空字符串
                cleaned[key] = value if value.strip() else None
            elif value is not None:
                cleaned[key] = value

        return {
            "success": True,
            "operation": "clean",
            "cleaned_data": cleaned,
            "message": "Data cleaning completed",
        }

    async def _normalize_data(self, data: Dict) -> dict:
        """标准化数据"""
        # 检查缓存
        cache_key = self._get_cache_key("normalize", data)
        if cache_key in self.cache:
            result = self.cache[cache_key].copy()
            result["from_cache"] = True
            return result

        normalized = {}

        for key, value in data.items():
            if isinstance(value, list) and all(isinstance(x, (int, float)) for x in value):
                # 数值列表的标准化（0-1 范围）
                min_val = min(value) if value else 0
                max_val = max(value) if value else 1
                range_val = max_val - min_val if max_val > min_val else 1

                normalized[key] = [
                    (x - min_val) / range_val for x in value
                ]
            else:
                normalized[key] = value

        result = {
            "success": True,
            "operation": "normalize",
            "normalized_data": normalized,
            "from_cache": False,
            "message": "Data normalization completed",
        }

        # 缓存结果
        self.cache[cache_key] = result.copy()
        result.pop("from_cache", None)
        result["from_cache"] = False

        return result

    async def _validate_data(self, data: Dict) -> dict:
        """验证数据"""
        is_valid = True
        errors = []

        # 定义数据范围约束
        constraints = {
            "temperature": (0.0, 100.0),
            "humidity": (0.0, 100.0),
            "pressure": (0.0, 1000.0),
        }

        for key, value in data.items():
            if key in constraints:
                min_val, max_val = constraints[key]
                if not (min_val <= value <= max_val):
                    is_valid = False
                    errors.append(
                        f"{key} out of range [{min_val}, {max_val}], got {value}"
                    )

        return {
            "success": True,
            "operation": "validate",
            "is_valid": is_valid,
            "errors": errors,
            "message": "Data validation completed",
        }

    async def _clear_cache(self) -> dict:
        """清空缓存"""
        cache_size = len(self.cache)
        self.cache.clear()

        return {
            "success": True,
            "operation": "clear_cache",
            "cleared_entries": cache_size,
            "message": f"Cleared {cache_size} cache entries",
        }

    def _get_cache_key(self, operation: str, data: Dict) -> str:
        """生成缓存键"""
        # 将数据转换为 JSON 字符串并哈希
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{operation}:{hash_obj.hexdigest()}"

    async def cleanup(self) -> None:
        """清理资源"""
        self.cache.clear()
        self.data_stats.clear()
        self.initialized = False
