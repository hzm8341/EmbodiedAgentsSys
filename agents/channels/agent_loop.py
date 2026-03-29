"""Robot Agent Loop — core control engine for autonomous task execution.

Architecture (from paper §3.1):
  ┌─────────────────────────────────────────────────────────┐
  │  InboundMessage (task command from operator/UI)         │
  │       ↓ MessageBus                                      │
  │  RobotAgentLoop                                         │
  │    1. Parse task from message                           │
  │    2. Decompose task → subtasks (CoTTaskPlanner)        │
  │    3. Build RobotMemoryState m_t                        │
  │    4. CoT decision loop:                                │
  │         - observe env (env_summary tool)                │
  │         - CoT decide → skill | mcp_tool | call_human   │
  │         - execute action                                │
  │         - update memory                                 │
  │         - check process supervisor (SubtaskMonitor)     │
  │         - repeat until SATISFIED or max_iterations      │
  │    5. Send OutboundMessage (result)                     │
  └─────────────────────────────────────────────────────────┘

This loop runs in its own asyncio task. It can be started from ROS2
via asyncio.run_coroutine_threadsafe() in a dedicated thread.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents.channels.bus import MessageBus
from agents.channels.events import InboundMessage, OutboundMessage
from agents.channels.robot_tools import RobotToolRegistry, build_default_robot_tools
from agents.components.cot_planner import CoTTaskPlanner, TaskState
from agents.llm.provider import LLMProvider
from agents.memory.failure_log import FailureLog, FailureRecord
from agents.memory.robot_memory import RobotMemoryState

logger = logging.getLogger(__name__)


class RobotAgentLoop:
    """Autonomous robot task execution loop.

    Receives task commands via MessageBus, runs CoT planning,
    dispatches robot tools/skills, and returns results.

    Args:
        bus: MessageBus for inbound commands and outbound results.
        provider: LLM provider for CoT planning.
        tool_registry: Robot MCP tools (start_policy, env_summary, etc.)
        robot_type: Hardware description string.
        max_iterations: Maximum CoT cycles per subtask before giving up.
        failure_log: Optional persistent failure log.
    """

    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        tool_registry: RobotToolRegistry | None = None,
        robot_type: str = "unknown",
        max_iterations: int = 20,
        failure_log: FailureLog | None = None,
    ):
        self.bus = bus
        self.provider = provider
        self.tool_registry = tool_registry or build_default_robot_tools()
        self.robot_type = robot_type
        self.max_iterations = max_iterations
        self.failure_log = failure_log

        self._planner = CoTTaskPlanner(provider=provider)
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the agent loop. Runs until stopped."""
        self._running = True
        logger.info("RobotAgentLoop started (robot_type=%s)", self.robot_type)
        try:
            while self._running:
                try:
                    msg = await asyncio.wait_for(
                        self.bus.consume_inbound(), timeout=1.0
                    )
                    asyncio.create_task(self._handle_message(msg))
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            logger.info("RobotAgentLoop stopped")

    def stop(self) -> None:
        """Signal the loop to stop after the current message."""
        self._running = False

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _handle_message(self, msg: InboundMessage) -> None:
        """Process a single inbound task command.

        Each invocation uses a local task_id to avoid concurrency races when
        multiple messages are processed simultaneously via asyncio.create_task.
        """
        task_description = msg.content.strip()
        if not task_description:
            return

        # Use local variable (not self._current_task_id) to avoid concurrent-task races
        task_id = msg.task_id or msg.session_key
        logger.info("Task received [%s]: %s", task_id, task_description[:80])

        # Acknowledge receipt
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=f"Starting task: {task_description}",
            task_id=task_id,
            status="in_progress",
        ))

        try:
            result = await self._execute_task(msg, task_description, task_id)
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=result,
                task_id=task_id,
                status="complete",
            ))
        except Exception as e:
            logger.error("Task execution error: %s", e, exc_info=True)
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=f"Task failed with error: {e}",
                task_id=task_id,
                status="error",
            ))

    async def _execute_task(
        self,
        msg: InboundMessage,
        task_description: str,
        task_id: str | None = None,
    ) -> str:
        """Full task execution pipeline."""
        # Step 1: decompose task into subtasks
        available_tools = self.tool_registry.list_tools()
        subtask_descriptions = await self._planner.decompose_task(
            task_description=task_description,
            robot_type=self.robot_type,
            available_skills=available_tools,
        )

        if not subtask_descriptions:
            # Single-step task — treat the whole description as one subtask
            subtask_descriptions = [task_description]

        logger.info(
            "Task decomposed into %d subtasks: %s",
            len(subtask_descriptions),
            subtask_descriptions,
        )

        # Step 2: build structured memory m_t
        memory = RobotMemoryState.create_for_task(
            global_task=task_description,
            subtask_descriptions=subtask_descriptions,
            robot_type=self.robot_type,
            mode="autonomous_task",
            available_tools=available_tools,
        )

        # Step 3: execute subtasks via CoT loop, respecting DAG dependencies.
        # Use get_current_subtask() to honour depends_on relationships — never
        # iterate over subtasks directly, as later subtasks may depend on
        # earlier ones completing successfully.
        completed = 0
        current = memory.task_graph.get_current_subtask()
        while current is not None:
            success = await self._execute_subtask(memory, current.id)
            if success:
                completed += 1
            else:
                # Log the failure
                if self.failure_log:
                    record = FailureRecord.create(
                        task_description=task_description,
                        subtask_id=current.id,
                        subtask_description=current.description,
                        error_type="subtask_failure",
                        error_detail=current.failure_reason or "unknown",
                        skill_id=current.skill_id,
                        robot_type=self.robot_type,
                    )
                    await self.failure_log.append(record)
                # Stop on failure — dependent subtasks cannot run without this one
                logger.warning(
                    "Subtask [%s] failed, stopping task execution (dependencies may be unsatisfied)",
                    current.id,
                )
                break
            # Fetch next subtask (takes into account newly COMPLETED status)
            current = memory.task_graph.get_current_subtask()

        total = len(memory.task_graph.subtasks)
        summary = memory.task_graph.progress_summary()
        return f"Task complete: {summary} ({completed}/{total} subtasks succeeded)"

    async def _execute_subtask(self, memory: RobotMemoryState, subtask_id: str) -> bool:
        """Execute a single subtask via CoT decision loop.

        Returns True if subtask completed successfully.
        """
        subtask = memory.task_graph._find(subtask_id)
        if subtask is None:
            return False

        memory.start_subtask(subtask_id)
        logger.info("Executing subtask [%s]: %s", subtask_id, subtask.description)

        # Initial env observation
        observation = await self._get_env_observation(memory)

        for iteration in range(self.max_iterations):
            # CoT decision
            decision = await self._planner.decide_next_action(
                memory=memory,
                observation=observation,
            )

            logger.debug(
                "CoT [%s] iter=%d state=%s action=%s/%s",
                subtask_id, iteration,
                decision.task_state.value,
                decision.action_type, decision.action_name,
            )

            # Handle task state
            if decision.task_state == TaskState.SATISFIED or decision.action_type == "complete":
                memory.complete_subtask(subtask_id)
                logger.info("Subtask [%s] completed", subtask_id)
                return True

            if decision.task_state == TaskState.STUCK and decision.action_type == "call_human":
                await self._call_human(decision.action_args.get("reason", "stuck"))
                memory.fail_subtask(subtask_id, reason="stuck — human called")
                return False

            # Execute action
            result = await self._dispatch_action(memory, decision)
            memory.working.record_tool_call(
                name=decision.action_name,
                args=decision.action_args,
                result=result.content if result else "no result",
            )

            # Refresh observation after action
            observation = await self._get_env_observation(memory)

        # Max iterations reached
        memory.fail_subtask(subtask_id, reason=f"max_iterations ({self.max_iterations}) reached")
        logger.warning("Subtask [%s] failed: max iterations reached", subtask_id)
        return False

    async def _get_env_observation(self, memory: RobotMemoryState) -> str:
        """Query env_summary tool and update working memory."""
        if self.tool_registry.has_tool("env_summary"):
            result = await self.tool_registry.call("env_summary", {})
            if result.success:
                memory.update_env_summary(result.content)
                return result.content
        return memory.working.env_summary or "No observation available"

    async def _dispatch_action(self, memory: RobotMemoryState, decision: Any) -> Any:
        """Dispatch a CoT decision to the appropriate handler."""
        if decision.action_type in ("skill", "mcp_tool"):
            if self.tool_registry.has_tool(decision.action_name):
                return await self.tool_registry.call(
                    decision.action_name, decision.action_args
                )
            else:
                logger.warning("Unknown tool/skill: %s", decision.action_name)
                return None
        elif decision.action_type == "call_human":
            return await self.tool_registry.call("call_human", decision.action_args)
        return None

    async def _call_human(self, reason: str) -> None:
        """Invoke the call_human MCP tool."""
        await self.tool_registry.call("call_human", {"reason": reason})
