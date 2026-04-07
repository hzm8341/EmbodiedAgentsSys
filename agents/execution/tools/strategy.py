"""agents/execution/tools/strategy.py - 策略选择器"""

from typing import List, Optional
from .registry import ToolRegistry


class StrategySelector:
    """策略选择器 - 为任务选择合适的工具"""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """初始化选择器"""
        self.registry = registry or ToolRegistry()

    def select_tool(self, name: str):
        """选择指定的工具"""
        return self.registry.get(name)

    def find_tool_by_keyword(self, keyword: str):
        """通过关键词找工具"""
        tools = self.registry.list_tools()
        for tool_name in tools:
            tool = self.registry.get(tool_name)
            keywords = getattr(tool, "keywords", [])
            if keyword in keywords or keyword.lower() in str(keywords).lower():
                return tool
        return None

    def rank_tools_for_task(self, task_description: str) -> List:
        """为任务排名工具"""
        tools = self.registry.list_tools()
        ranked = []

        for tool_name in tools:
            tool = self.registry.get(tool_name)

            # 简单的评分：基于名称和描述的匹配
            score = 0
            description = getattr(tool, "description", "").lower()
            keywords = getattr(tool, "keywords", [])

            if tool_name.lower() in task_description.lower():
                score += 10
            if any(kw.lower() in task_description.lower() for kw in keywords):
                score += 5
            if description and any(word in description for word in task_description.lower().split()):
                score += 1

            ranked.append((tool_name, tool, score))

        # 按评分排序
        ranked.sort(key=lambda x: x[2], reverse=True)
        return [tool for _, tool, _ in ranked]

    def find_best_tool(self, task_description: str):
        """为任务找最佳工具"""
        ranked = self.rank_tools_for_task(task_description)
        if ranked:
            return ranked[0]
        return None
