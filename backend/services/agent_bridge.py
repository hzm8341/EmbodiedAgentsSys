"""Agent bridge: wraps cognition layers with WebSocket telemetry broadcast."""
from __future__ import annotations

import time
from typing import Any, Optional

from agents.cognition.planning import DefaultPlanningLayer
from agents.cognition.reasoning import DefaultReasoningLayer
from agents.cognition.learning import DefaultLearningLayer
from agents.core.types import RobotObservation
from backend.services.websocket_manager import agent_stream_manager


class AgentBridge:
    """Coordinates planning/reasoning/learning layers and streams telemetry.

    Each call to ``run_with_telemetry`` emits WebSocket messages for every
    layer transition (task_start -> planning -> (reasoning, execution,
    learning) x N -> result), enabling the frontend to visualize the
    four-layer reasoning process in real time.
    """

    def __init__(
        self,
        planning: Optional[DefaultPlanningLayer] = None,
        reasoning: Optional[DefaultReasoningLayer] = None,
        learning: Optional[DefaultLearningLayer] = None,
        stream_manager: Optional[Any] = None,
    ):
        """Initialize with optional dependency injection for testing.

        Args:
            planning: Planning layer instance (defaults to DefaultPlanningLayer).
            reasoning: Reasoning layer instance (defaults to DefaultReasoningLayer).
            learning: Learning layer instance (defaults to DefaultLearningLayer).
            stream_manager: Broadcast stream manager (defaults to the module
                singleton ``agent_stream_manager``).
        """
        self.planning = planning or DefaultPlanningLayer()
        self.reasoning = reasoning or DefaultReasoningLayer()
        self.learning = learning or DefaultLearningLayer()
        self.stream_manager = stream_manager or agent_stream_manager

    async def _emit(
        self,
        message_type: str,
        data: dict,
        status: str = "completed",
    ) -> None:
        """Broadcast a telemetry message with timestamp and status."""
        await self.stream_manager.broadcast(
            {
                "type": message_type,
                "timestamp": time.time(),
                "status": status,
                "data": data,
            }
        )

    async def run_with_telemetry(
        self,
        task: str,
        observation: RobotObservation,
        max_steps: int = 3,
    ) -> dict:
        """Execute task through the four-layer pipeline, broadcasting each step.

        Args:
            task: Natural-language task description.
            observation: Initial robot observation.
            max_steps: How many reason-execute-learn iterations to run.

        Returns:
            The final result payload (same data emitted in the ``result`` message).
        """
        await self._emit("task_start", {"task": task})

        plan = await self.planning.generate_plan(task)
        await self._emit("planning", {"plan": plan})

        for step in range(max_steps):
            action = await self.reasoning.generate_action(plan, observation)
            await self._emit("reasoning", {"step": step, "action": action})

            feedback = {"success": True, "step": step}
            await self._emit("execution", {"step": step, "feedback": feedback})

            improved = await self.learning.improve(action, feedback)
            await self._emit(
                "learning", {"step": step, "improved_action": improved}
            )

        result_data = {"task_success": True, "steps_executed": max_steps}
        await self._emit("result", result_data)
        return result_data


agent_bridge = AgentBridge()
