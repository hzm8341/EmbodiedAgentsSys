"""
agents/cognition/engine.py - 认知引擎

整合 Planning、Reasoning、Learning 三层的认知处理引擎
"""

from .planning import DefaultPlanningLayer
from .reasoning import DefaultReasoningLayer
from .learning import DefaultLearningLayer


class CognitionEngine:
    """认知引擎 - 整合三个子层的认知处理"""

    def __init__(self, config):
        """
        初始化认知引擎

        Args:
            config: 代理配置对象
        """
        self.config = config

        # 初始化三个子层
        self.planning = DefaultPlanningLayer()
        self.reasoning = DefaultReasoningLayer()
        self.learning = DefaultLearningLayer()

        # 记录最后一个动作用于反馈
        self._last_action = None
        self._last_plan = None

    async def think(self, task: str, observation=None) -> dict:
        """
        执行认知思考步骤（Planning -> Reasoning）

        Args:
            task: 任务描述
            observation: 当前观察（可选）

        Returns:
            dict: 认知结果（包含计划、动作等）
        """
        # 步骤 1：生成计划
        plan = await self.planning.generate_plan(task)
        self._last_plan = plan

        # 步骤 2：生成动作
        if observation is None:
            # 创建默认观察
            from ..core.types import RobotObservation

            observation = RobotObservation()

        action = await self.reasoning.generate_action(plan, observation)
        self._last_action = action

        # 返回认知结果
        return {
            "plan": plan,
            "action": action,
            "task": task,
        }

    async def provide_feedback(self, feedback) -> str:
        """
        提供反馈以改进学习

        Args:
            feedback: SkillResult 对象或字典

        Returns:
            str: 改进后的动作
        """
        if self._last_action is None:
            return None

        # 转换反馈为字典格式
        if hasattr(feedback, "success"):
            feedback_dict = {
                "success": feedback.success,
                "message": feedback.message,
            }
        else:
            feedback_dict = feedback

        # 步骤 3：学习和改进
        improved_action = await self.learning.improve(self._last_action, feedback_dict)
        self._last_action = improved_action

        return improved_action
