"""
agents/feedback/analyzer.py - 反馈分析器

分析反馈数据，识别模式和提取洞察
"""

from typing import List, Dict, Any


class FeedbackAnalyzer:
    """反馈分析器 - 分析执行反馈"""

    async def analyze(self, result) -> Dict[str, Any]:
        """
        分析单个结果

        Args:
            result: SkillResult 对象

        Returns:
            Dict: 分析结果
        """
        return {
            "success": result.success,
            "message": result.message,
            "has_data": result.data is not None,
        }

    async def identify_patterns(self, results: List) -> Dict[str, Any]:
        """
        识别反馈中的模式

        Args:
            results: SkillResult 对象列表

        Returns:
            Dict: 识别的模式
        """
        if not results:
            return {}

        # 计算成功率
        success_count = sum(1 for r in results if r.success)
        success_rate = success_count / len(results)

        # 提取常见的错误信息
        error_messages = []
        for r in results:
            if not r.success and r.message:
                error_messages.append(r.message)

        # 识别重复错误
        error_patterns = {}
        for msg in error_messages:
            # 提取错误关键字
            if "Gripper" in msg or "gripper" in msg:
                error_patterns["gripper_issue"] = error_patterns.get("gripper_issue", 0) + 1
            elif "timeout" in msg.lower():
                error_patterns["timeout"] = error_patterns.get("timeout", 0) + 1

        return {
            "total_attempts": len(results),
            "success_rate": success_rate,
            "error_patterns": error_patterns,
        }

    def get_statistics(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从历史记录计算统计信息

        Args:
            history: 历史记录列表

        Returns:
            Dict: 统计信息
        """
        if not history:
            return {}

        success_count = sum(1 for r in history if r["success"])
        total = len(history)

        return {
            "total_records": total,
            "success_count": success_count,
            "failure_count": total - success_count,
            "success_rate": success_count / total if total > 0 else 0,
        }
