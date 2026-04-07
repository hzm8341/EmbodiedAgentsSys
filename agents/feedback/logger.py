"""
agents/feedback/logger.py - 反馈记录器

记录执行结果和相关元数据
"""

from datetime import datetime
from typing import List, Dict, Any


class FeedbackLogger:
    """反馈记录器 - 记录执行结果"""

    def __init__(self):
        """初始化反馈记录器"""
        self.history: List[Dict[str, Any]] = []

    async def log_result(self, result) -> None:
        """
        记录执行结果

        Args:
            result: SkillResult 对象
        """
        # 转换结果为字典
        record = {
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "message": result.message,
            "data": result.data or {},
        }

        self.history.append(record)

    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取完整历史记录

        Returns:
            List: 历史记录列表
        """
        return self.history

    def get_last_result(self) -> Dict[str, Any]:
        """
        获取最后一条记录

        Returns:
            Dict: 最后一条记录
        """
        if self.history:
            return self.history[-1]
        return None

    def clear_history(self) -> None:
        """清除历史记录"""
        self.history = []
