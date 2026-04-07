"""agents/extensions/loader.py - 插件加载器"""

from .registry import PluginRegistry


class PluginLoader:
    """插件加载器 - 加载和管理插件"""

    def __init__(self):
        """初始化加载器"""
        self.registry = PluginRegistry()

    def register_plugin(self, plugin) -> None:
        """
        注册插件

        Args:
            plugin: 插件对象（应有 name 属性）
        """
        plugin_name = getattr(plugin, "name", plugin.__class__.__name__)
        self.registry.register(plugin_name, plugin)

    def get_plugin(self, name: str):
        """
        获取插件

        Args:
            name: 插件名称

        Returns:
            插件对象
        """
        return self.registry.get(name)

    async def initialize_plugin(self, name: str, config=None) -> None:
        """
        初始化插件

        Args:
            name: 插件名称
            config: 配置字典
        """
        plugin = self.registry.get(name)
        if plugin:
            await plugin.initialize(config)

    async def execute_plugin(self, name: str, *args, **kwargs):
        """
        执行插件

        Args:
            name: 插件名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            执行结果
        """
        plugin = self.registry.get(name)
        if plugin:
            return await plugin.execute(*args, **kwargs)
        return None

    def list_plugins(self) -> list:
        """
        列出所有插件

        Returns:
            List: 插件名称列表
        """
        return self.registry.list_plugins()

    def unload_plugin(self, name: str) -> None:
        """
        卸载插件

        Args:
            name: 插件名称
        """
        self.registry.unregister(name)
