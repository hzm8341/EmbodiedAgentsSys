"""attach_harness — zero-invasive interceptor for RobotAgentLoop."""
from __future__ import annotations
import time
from typing import Any, TYPE_CHECKING

from agents.channels.robot_tools import RobotToolRegistry, ToolResult
from agents.harness.core.config import HarnessConfig
from agents.harness.core.tracer import HarnessTracer

if TYPE_CHECKING:
    from agents.channels.agent_loop import RobotAgentLoop


class TracingToolRegistry(RobotToolRegistry):
    """Wraps a real ToolRegistry and records all calls to HarnessTracer."""

    def __init__(self, wrapped: RobotToolRegistry, tracer: HarnessTracer):
        super().__init__()
        self._wrapped = wrapped
        self._tracer = tracer
        # Mirror the wrapped registry's tools
        self._tools = wrapped._tools  # type: ignore[attr-defined]

    async def call(self, name: str, args: dict[str, Any]) -> ToolResult:
        start = time.monotonic()
        result = await self._wrapped.call(name, args)
        duration_ms = int((time.monotonic() - start) * 1000)
        self._tracer.record_tool_call(
            name=name,
            args=args,
            result=result.content if result else "no result",
            duration_ms=duration_ms,
        )
        return result

    def has_tool(self, name: str) -> bool:
        return self._wrapped.has_tool(name)

    def list_tools(self) -> list[str]:
        return self._wrapped.list_tools()

    def register(self, name: str, fn: Any) -> None:
        self._wrapped.register(name, fn)


def attach_harness(
    loop: "RobotAgentLoop",
    config: HarnessConfig,
) -> tuple["RobotAgentLoop", HarnessTracer]:
    """Attach a HarnessTracer to a RobotAgentLoop without modifying its source."""
    tracer = HarnessTracer(config)
    loop.tool_registry = TracingToolRegistry(loop.tool_registry, tracer)
    return loop, tracer
