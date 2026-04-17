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

    async def generate_plan(self, task: str, action_sequence: list | None = None) -> dict:
        """
        生成任务计划

        Args:
            task: 任务描述
            action_sequence: 可选的预定义动作序列（来自 Scenario）

        Returns:
            dict: 任务计划（包含步骤、action_sequence 和 current_step）
        """
        seq = action_sequence or []
        return {
            "task": task,
            "steps": [f"step_{i+1}" for i in range(max(len(seq), 3))],
            "description": f"Plan for task: {task}",
            "action_sequence": seq,
            "current_step": 0,
        }


# 保持向后兼容
class PlanningLayer(DefaultPlanningLayer):
    """向后兼容别名"""
    pass
