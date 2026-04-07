"""agents/execution/tools/base.py - 工具基类"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage


class ToolBase(ABC):
    """工具基类 - 所有工具必须继承"""

    name: str
    description: str = ""
    category: str = "general"
    keywords: list = []

    def __init__(self):
        """初始化工具基类"""
        self._cancelled: bool = False

    # ── 旧接口（保持向后兼容）──
    @abstractmethod
    async def execute(self, *args, **kwargs) -> dict:
        """执行工具逻辑（旧接口，推荐使用 execute_with_feedback）"""
        pass

    # ── 新接口（推荐，异步生成器）────
    async def execute_with_feedback(
        self,
        params: dict,
        current_state: dict,
    ) -> AsyncGenerator[ExecutionFeedback, None]:
        """
        异步生成器接口，执行期间产生 ExecutionFeedback。
        新工具应直接覆盖此方法；旧工具应使用 ToolAdapter 包装。

        Args:
            params: 工具参数字典
            current_state: 当前状态字典

        Yields:
            ExecutionFeedback: 执行过程中的反馈事件
        """
        raise NotImplementedError(
            f"Tool '{getattr(self, 'name', type(self).__name__)}' should implement "
            f"execute_with_feedback() directly, or be wrapped with ToolAdapter."
        )

    # ── 取消机制 ──
    def cancel(self) -> None:
        """请求取消当前执行（在人工接管时调用）"""
        self._cancelled = True

    def reset_cancel(self) -> None:
        """清除取消标志（为重新执行做准备）"""
        self._cancelled = False

    def is_cancelled(self) -> bool:
        """检查是否已请求取消"""
        return self._cancelled

    # ── 可选的生命周期钩子 ──
    async def validate(self, *args, **kwargs) -> bool:
        """验证输入（可选）"""
        return True

    async def cleanup(self):
        """清理资源（可选）"""
        pass
