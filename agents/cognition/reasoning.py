"""
agents/cognition/reasoning.py - 推理层

负责根据计划和观察生成具体的动作或代码
"""

from abc import ABC, abstractmethod


class ReasoningLayerBase(ABC):
    """推理层抽象基类 - 定义接口契约"""

    @abstractmethod
    async def generate_action(self, plan: dict, observation) -> dict:
        """
        生成动作

        Args:
            plan: 任务计划（包含 action_sequence 和 current_step）
            observation: 当前观察

        Returns:
            dict: 动作字典，如 {"action": "move_arm_to", "params": {...}}
        """
        pass


class DefaultReasoningLayer(ReasoningLayerBase):
    """默认推理层实现"""

    async def generate_action(self, plan: dict, observation) -> dict:
        """
        从 plan["action_sequence"] 中取当前步骤的动作。

        Args:
            plan: 任务计划（包含 action_sequence 和 current_step）
            observation: 当前观察

        Returns:
            dict: 动作字典，如 {"action": "move_arm_to", "params": {...}}
        """
        action_sequence: list = plan.get("action_sequence", [])
        step: int = plan.get("current_step", 0)

        if action_sequence and step < len(action_sequence):
            action_dict = action_sequence[step]
            # Advance the step counter in the plan dict for the next call
            plan["current_step"] = step + 1
            return action_dict

        # Fallback: no-op move when sequence is exhausted or absent
        return {"action": "move_arm_to", "params": {"arm": "left", "x": 0.3, "y": 0.0, "z": 0.5}}


# 保持向后兼容
class ReasoningLayer(DefaultReasoningLayer):
    """向后兼容别名"""
    pass
