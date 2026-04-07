"""agents/execution/tool_adapter.py - 遗留工具适配器

为遗留工具（使用旧 execute() 接口）提供适配器，
使其与新的 execute_with_feedback() 异步生成器接口兼容。
"""

import asyncio
import warnings
from typing import AsyncGenerator

from agents.execution.execution_feedback import ExecutionFeedback, FeedbackStage
from agents.execution.tools.base import ToolBase


class ToolAdapter(ToolBase):
    """
    将遗留工具包装为新的异步生成器接口。

    - 保留工具的元数据（name, description, category, keywords）
    - 在实例化时发出 DeprecationWarning
    - 委托 validate() 和 cleanup() 给遗留工具
    """

    def __init__(self, legacy_tool: ToolBase):
        """
        初始化适配器。

        Args:
            legacy_tool: 遗留工具实例（使用旧 execute() 接口）

        Warns:
            DeprecationWarning: 提醒用户迁移到新接口
        """
        super().__init__()
        self._legacy_tool = legacy_tool

        # 复制元数据
        self.name = legacy_tool.name
        self.description = legacy_tool.description
        self.category = legacy_tool.category
        self.keywords = legacy_tool.keywords

        # 发出弃用警告
        warnings.warn(
            f"Tool '{self.name}' is using legacy execute() interface. "
            f"Please migrate to execute_with_feedback() for better "
            f"observability and cancellation support.",
            DeprecationWarning,
            stacklevel=2,
        )

    async def execute(self, *args, **kwargs) -> dict:
        """
        委托给遗留工具的 execute() 方法。

        这是为了 ToolAdapter 本身也是 ToolBase 的子类而必需的。
        """
        return await self._legacy_tool.execute(*args, **kwargs)

    async def execute_with_feedback(
        self,
        params: dict,
        current_state: dict,
    ) -> AsyncGenerator[ExecutionFeedback, None]:
        """
        异步生成器接口实现。

        将遗留工具的同步 execute() 调用包装为异步生成器，
        产生执行过程的反馈事件。

        Args:
            params: 工具参数字典
            current_state: 当前状态字典

        Yields:
            ExecutionFeedback: 执行过程中的反馈事件
        """
        # 产生 STARTED 反馈
        yield ExecutionFeedback(
            stage=FeedbackStage.STARTED,
            progress=0.0,
            current_state=current_state,
            message=f"Starting tool '{self.name}'",
        )

        try:
            # 使用 asyncio.wait_for 执行遗留工具，超时时间 60 秒
            result = await asyncio.wait_for(
                self._legacy_tool.execute(**params),
                timeout=60.0,
            )

            # 产生 COMPLETED 反馈
            yield ExecutionFeedback(
                stage=FeedbackStage.COMPLETED,
                progress=1.0,
                current_state=result if isinstance(result, dict) else current_state,
                message=f"Tool '{self.name}' completed successfully",
            )

        except asyncio.TimeoutError:
            # 超时错误
            yield ExecutionFeedback(
                stage=FeedbackStage.FAILED,
                progress=0.0,
                current_state=current_state,
                message=f"Tool '{self.name}' execution timed out after 60.0 seconds",
                has_error=True,
                error_type="TimeoutError",
                error_message="Execution exceeded 60.0 second timeout",
            )

        except Exception as e:
            # 捕获其他异常
            yield ExecutionFeedback(
                stage=FeedbackStage.FAILED,
                progress=0.0,
                current_state=current_state,
                message=f"Tool '{self.name}' failed with error: {str(e)}",
                has_error=True,
                error_type=type(e).__name__,
                error_message=str(e),
            )

    async def validate(self, *args, **kwargs) -> bool:
        """
        委托给遗留工具的 validate() 方法。

        Args:
            *args: 传递给遗留工具的位置参数
            **kwargs: 传递给遗留工具的关键字参数

        Returns:
            bool: 验证结果
        """
        return await self._legacy_tool.validate(*args, **kwargs)

    async def cleanup(self):
        """
        委托给遗留工具的 cleanup() 方法。
        """
        await self._legacy_tool.cleanup()
