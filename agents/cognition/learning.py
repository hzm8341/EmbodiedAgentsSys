"""
agents/cognition/learning.py - 学习层

负责根据反馈改进动作和策略
"""

from abc import ABC, abstractmethod


class LearningLayerBase(ABC):
    """学习层抽象基类 - 定义接口契约"""

    @abstractmethod
    async def improve(self, action: str, feedback: dict) -> str:
        """
        根据反馈改进动作

        Args:
            action: 原始动作代码
            feedback: 执行反馈（包含成功/失败、错误信息等）

        Returns:
            str: 改进后的动作代码
        """
        pass


class DefaultLearningLayer(LearningLayerBase):
    """默认学习层实现"""

    def __init__(self):
        """初始化学习层"""
        self.improvement_history = []

    async def improve(self, action: str, feedback: dict) -> str:
        """
        根据反馈改进动作

        Args:
            action: 原始动作代码
            feedback: 执行反馈（包含成功/失败、错误信息等）

        Returns:
            str: 改进后的动作代码
        """
        # 记录改进历史
        self.improvement_history.append(
            {
                "original_action": action,
                "feedback": feedback,
            }
        )

        # 最小实现：如果失败，添加注释说明改进
        if not feedback.get("success", True):
            error_msg = feedback.get("error", "unknown error")
            improved_action = (
                f"# Improved based on: {error_msg}\n"
                f"# Original: {action}\n"
                f"{action}"
            )
            return improved_action
        else:
            # 成功反馈：返回相同的动作，标记为验证
            verified_action = f"# Verified successful\n{action}"
            return verified_action


# 保持向后兼容
class LearningLayer(DefaultLearningLayer):
    """向后兼容别名"""
    pass
