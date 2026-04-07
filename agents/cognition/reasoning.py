"""
agents/cognition/reasoning.py - 推理层

负责根据计划和观察生成具体的动作或代码
"""

from abc import ABC, abstractmethod


class ReasoningLayerBase(ABC):
    """推理层抽象基类 - 定义接口契约"""

    @abstractmethod
    async def generate_action(self, plan: dict, observation) -> str:
        """
        生成动作（代码或技能调用）

        Args:
            plan: 任务计划
            observation: 当前观察

        Returns:
            str: 生成的动作代码或技能调用
        """
        pass


class DefaultReasoningLayer(ReasoningLayerBase):
    """默认推理层实现"""

    async def generate_action(self, plan: dict, observation) -> str:
        """
        生成动作（代码或技能调用）

        Args:
            plan: 任务计划
            observation: 当前观察

        Returns:
            str: 生成的动作代码或技能调用
        """
        # 最小实现：根据观察状态生成简单的动作代码
        gripper_state = observation.state.get("gripper_open", True)

        if gripper_state:
            action = "gripper.open()"
        else:
            action = "gripper.close()"

        # 返回可执行的代码
        return f"# Generated action for: {plan.get('task', 'unknown')}\n{action}"


# 保持向后兼容
class ReasoningLayer(DefaultReasoningLayer):
    """向后兼容别名"""
    pass
