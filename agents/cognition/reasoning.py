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
        return {"action": "move_arm_to", "params": {"arm": "left", "x": 0.04, "y": 0.36, "z": 0.83}}

    async def adapt_after_feedback(self, action: dict, feedback: dict) -> dict:
        """Return a minimally adapted action when last execution failed."""
        if feedback.get("success", False):
            return action
        adapted = dict(action)
        params = dict(adapted.get("params", {}))
        if "z" in params and isinstance(params["z"], (int, float)):
            params["z"] = float(params["z"]) + 0.02
        adapted["params"] = params
        return adapted


# 保持向后兼容
class ReasoningLayer(DefaultReasoningLayer):
    """向后兼容别名"""
    pass
