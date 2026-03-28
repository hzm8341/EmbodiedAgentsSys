"""Robot MCP tools — callable by the CoT planner as action decisions.

These are the robot-specific tools from the paper §3.1 that the agent can
invoke during task execution:
  - start_policy:      activate a VLA skill policy
  - terminate_policy:  stop the currently active policy
  - change_policy:     switch to a different skill policy
  - env_summary:       query current environment state
  - fetch_robot_stats: query robot joint/gripper health
  - call_human:        escalate to human operator

Tools are registered in the ToolRegistry and dispatched by RobotAgentLoop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a robot MCP tool call."""
    tool_name: str
    success: bool
    content: str
    data: dict[str, Any] | None = None


# Type alias for async tool handler functions
ToolHandler = Callable[..., Awaitable[ToolResult]]


class RobotToolRegistry:
    """Registry of robot MCP tools.

    Tools are registered by name; the agent loop dispatches calls to them.
    """

    def __init__(self):
        self._tools: dict[str, ToolHandler] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: ToolHandler,
        schema: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool handler.

        Args:
            name: Tool name (must match action_name from CoT decisions).
            handler: Async function that takes **kwargs and returns ToolResult.
            schema: Optional JSON schema for the tool's arguments.
        """
        self._tools[name] = handler
        if schema:
            self._schemas[name] = schema

    async def call(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Invoke a registered tool by name."""
        handler = self._tools.get(name)
        if handler is None:
            return ToolResult(
                tool_name=name,
                success=False,
                content=f"Unknown tool: {name}",
            )
        try:
            return await handler(**args)
        except Exception as e:
            logger.error("Tool %s raised exception: %s", name, e)
            return ToolResult(
                tool_name=name,
                success=False,
                content=f"Tool error: {e}",
            )

    def list_tools(self) -> list[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tools


def build_default_robot_tools(
    skill_executor: Any | None = None,
    human_notifier: Callable[[str], Awaitable[None]] | None = None,
) -> RobotToolRegistry:
    """Build a RobotToolRegistry with default robot MCP tool stubs.

    In production, replace the stub implementations by passing:
      skill_executor: object with start_skill(skill_id, **kwargs) etc.
      human_notifier: async function to notify a human operator.
    """
    registry = RobotToolRegistry()

    async def _start_policy(skill_id: str = "", **kwargs: Any) -> ToolResult:
        if skill_executor is None:
            return ToolResult("start_policy", True, f"[stub] Started policy: {skill_id}")
        try:
            result = await skill_executor.start_skill(skill_id, **kwargs)
            return ToolResult("start_policy", True, str(result))
        except Exception as e:
            return ToolResult("start_policy", False, str(e))

    async def _terminate_policy(**kwargs: Any) -> ToolResult:
        if skill_executor is None:
            return ToolResult("terminate_policy", True, "[stub] Policy terminated")
        try:
            await skill_executor.stop_current_skill()
            return ToolResult("terminate_policy", True, "Policy terminated")
        except Exception as e:
            return ToolResult("terminate_policy", False, str(e))

    async def _change_policy(skill_id: str = "", **kwargs: Any) -> ToolResult:
        if skill_executor is None:
            return ToolResult("change_policy", True, f"[stub] Changed to policy: {skill_id}")
        try:
            await skill_executor.stop_current_skill()
            result = await skill_executor.start_skill(skill_id, **kwargs)
            return ToolResult("change_policy", True, str(result))
        except Exception as e:
            return ToolResult("change_policy", False, str(e))

    async def _env_summary(**kwargs: Any) -> ToolResult:
        if skill_executor is None:
            return ToolResult(
                "env_summary", True,
                "[stub] Environment: robot arm idle, workspace clear",
                data={"objects": [], "robot_state": "idle"},
            )
        try:
            summary = await skill_executor.get_env_summary()
            return ToolResult("env_summary", True, str(summary), data={"summary": summary})
        except Exception as e:
            return ToolResult("env_summary", False, str(e))

    async def _fetch_robot_stats(**kwargs: Any) -> ToolResult:
        if skill_executor is None:
            return ToolResult(
                "fetch_robot_stats", True,
                "[stub] Robot stats: all joints nominal",
                data={"joint_errors": [], "gripper_force": 0.0, "battery": 100},
            )
        try:
            stats = await skill_executor.get_robot_stats()
            return ToolResult("fetch_robot_stats", True, str(stats), data=stats)
        except Exception as e:
            return ToolResult("fetch_robot_stats", False, str(e))

    async def _call_human(reason: str = "", **kwargs: Any) -> ToolResult:
        msg = f"[Human intervention requested] Reason: {reason}"
        logger.warning(msg)
        if human_notifier is not None:
            try:
                await human_notifier(msg)
            except Exception as e:
                logger.error("Human notifier error: %s", e)
        return ToolResult("call_human", True, msg)

    registry.register("start_policy", _start_policy)
    registry.register("terminate_policy", _terminate_policy)
    registry.register("change_policy", _change_policy)
    registry.register("env_summary", _env_summary)
    registry.register("fetch_robot_stats", _fetch_robot_stats)
    registry.register("call_human", _call_human)

    return registry
