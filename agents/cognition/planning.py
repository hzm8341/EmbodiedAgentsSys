"""
agents/cognition/planning.py - 规划层

负责将任务分解为计划（步骤、子任务等）
"""

from abc import ABC, abstractmethod


class PlanningLayerBase(ABC):
    """规划层抽象基类 - 定义接口契约"""

    @abstractmethod
    async def generate_plan(self, task: str) -> dict:
        """
        生成任务计划

        Args:
            task: 任务描述

        Returns:
            dict: 任务计划（包含步骤、目标等）
        """
        pass


class DefaultPlanningLayer(PlanningLayerBase):
    """默认规划层实现"""

    async def generate_plan(self, task: str) -> dict:
        """
        生成任务计划

        Args:
            task: 任务描述

        Returns:
            dict: 任务计划（包含步骤、目标等）
        """
        # 最小实现：返回包含任务的基础计划结构
        return {
            "task": task,
            "steps": ["step_1", "step_2", "step_3"],
            "description": f"Plan for task: {task}",
        }


# 保持向后兼容
class PlanningLayer(DefaultPlanningLayer):
    """向后兼容别名"""
    pass
