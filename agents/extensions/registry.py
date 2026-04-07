"""agents/extensions/registry.py - 插件注册表"""

from typing import Dict, List


class PluginRegistry:
    """插件注册表 - 管理注册的插件"""

    def __init__(self):
        """初始化注册表"""
        self._plugins: Dict[str, object] = {}

    def register(self, name: str, plugin: object) -> None:
        """
        注册插件

        Args:
            name: 插件名称
            plugin: 插件对象
        """
        self._plugins[name] = plugin

    def get(self, name: str):
        """
        获取插件

        Args:
            name: 插件名称

        Returns:
            插件对象
        """
        return self._plugins.get(name)

    def unregister(self, name: str) -> None:
        """
        注销插件

        Args:
            name: 插件名称
        """
        if name in self._plugins:
            del self._plugins[name]

    def list_plugins(self) -> List[str]:
        """
        列出所有插件名称

        Returns:
            List: 插件名称列表
        """
        return list(self._plugins.keys())

    def has_plugin(self, name: str) -> bool:
        """
        检查插件是否存在

        Args:
            name: 插件名称

        Returns:
            bool: 插件是否存在
        """
        return name in self._plugins
