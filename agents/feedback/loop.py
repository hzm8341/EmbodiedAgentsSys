"""
agents/feedback/loop.py - 反馈循环

整合日志记录和分析，形成完整的反馈处理系统
"""

from typing import Callable, List, Dict, Any
from .logger import FeedbackLogger
from .analyzer import FeedbackAnalyzer


class FeedbackLoop:
    """反馈循环 - 整合日志记录和分析"""

    def __init__(self):
        """初始化反馈循环"""
        self.logger = FeedbackLogger()
        self.analyzer = FeedbackAnalyzer()
        self.callbacks: List[Callable] = []

    async def receive_feedback(self, result) -> None:
        """
        接收反馈

        Args:
            result: SkillResult 对象
        """
        # 记录结果
        await self.logger.log_result(result)

        # 调用注册的回调
        for callback in self.callbacks:
            await callback(result)

    def register_callback(self, callback: Callable) -> None:
        """
        注册反馈回调函数

        Args:
            callback: 异步回调函数
        """
        self.callbacks.append(callback)

    def unregister_callback(self, callback: Callable) -> None:
        """
        注销回调函数

        Args:
            callback: 要注销的回调函数
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def get_feedback_count(self) -> int:
        """
        获取反馈总数

        Returns:
            int: 反馈记录数
        """
        return len(self.logger.history)

    def get_insights(self) -> Dict[str, Any]:
        """
        获取反馈洞察

        Returns:
            Dict: 洞察信息（包含统计和模式识别）
        """
        history = self.logger.get_history()

        # 获取统计信息
        statistics = self.analyzer.get_statistics(history)

        # 如果有足够的数据，识别模式
        patterns = {}
        if len(history) > 1:
            # 从历史重构结果对象（简化版）
            class SimpleResult:
                def __init__(self, record):
                    self.success = record["success"]
                    self.message = record["message"]
                    self.data = record.get("data")

            results = [SimpleResult(r) for r in history]
            patterns = self.analyzer.identify_patterns(results)

        return {
            **statistics,
            "patterns": patterns,
        }

    def clear_history(self) -> None:
        """清除所有反馈记录"""
        self.logger.clear_history()

    def get_last_feedback(self) -> Dict[str, Any]:
        """
        获取最后一条反馈

        Returns:
            Dict: 最后一条反馈记录
        """
        return self.logger.get_last_result()
