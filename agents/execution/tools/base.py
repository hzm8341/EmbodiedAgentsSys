"""agents/execution/tools/base.py - 工具基类"""

from abc import ABC, abstractmethod


class ToolBase(ABC):
    """工具基类 - 所有工具必须继承"""

    name: str
    description: str = ""
    category: str = "general"
    keywords: list = []

    @abstractmethod
    async def execute(self, *args, **kwargs) -> dict:
        """执行工具逻辑"""
        pass

    async def validate(self, *args, **kwargs) -> bool:
        """验证输入（可选）"""
        return True

    async def cleanup(self):
        """清理资源（可选）"""
        pass
