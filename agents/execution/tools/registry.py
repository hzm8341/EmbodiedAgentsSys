"""agents/execution/tools/registry.py - 工具注册表"""

from typing import Dict, List


class ToolRegistry:
    """工具注册表 - 管理工具"""

    def __init__(self):
        """初始化注册表"""
        self._tools: Dict[str, object] = {}

    def register(self, name: str, tool: object) -> None:
        """注册工具"""
        self._tools[name] = tool

    def get(self, name: str):
        """获取工具"""
        return self._tools.get(name)

    def unregister(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]

    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools
