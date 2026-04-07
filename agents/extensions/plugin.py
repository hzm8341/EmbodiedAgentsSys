"""agents/extensions/plugin.py - 插件基类"""

from abc import ABC, abstractmethod


class PluginBase(ABC):
    """插件基类 - 所有插件必须继承"""

    name: str
    version: str
    description: str = ""

    @abstractmethod
    async def initialize(self, config=None):
        """初始化插件"""
        pass

    @abstractmethod
    async def execute(self, *args, **kwargs):
        """执行插件逻辑"""
        pass

    async def cleanup(self):
        """清理资源（可选）"""
        pass
