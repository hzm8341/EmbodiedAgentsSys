"""Agent bridge: wraps cognition layers with WebSocket telemetry broadcast."""
from __future__ import annotations

import asyncio
import time
import uuid
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
        trace_id: str,
        message_type: str,
        payload: dict,
        status: str = "completed",
        step: int | None = None,
        error_code: str | None = None,
    ) -> None:
        """Broadcast a v1 telemetry message while keeping legacy compatibility."""
        ts = time.time()
        await self.stream_manager.broadcast(
            {
                "protocol_version": "v1",
                "type": message_type,
                "trace_id": trace_id,
                "step": step,
                "timestamp": ts,
                "status": status,
                "error_code": error_code,
                "payload": payload,
                # legacy field kept for existing clients/tests
                "data": payload,
            }
        )

    async def run_with_telemetry(
        self,
        task: str,
        observation: RobotObservation,
        action_sequence: list | None = None,
        max_steps: int | None = None,
        controller: Any | None = None,
    ) -> dict:
        """Execute task through the four-layer pipeline, broadcasting each step.

        Args:
            task: Natural-language task description.
            observation: Initial robot observation.
            action_sequence: Optional pre-defined action sequence from a Scenario.
            max_steps: Override the number of reasoning loops (default: len of
                action_sequence, or 3 if no sequence is provided).

        Returns:
            The final result payload (same data emitted in the ``result`` message).
        """
        from backend.services.simulation import simulation_service

        trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        await self._emit(trace_id, "task_start", {"task": task})

        plan = await self.planning.generate_plan(task, action_sequence=action_sequence)
        await self._emit(trace_id, "planning", {"plan": plan})

        max_steps = max_steps if max_steps is not None else (len(plan.get("action_sequence", [])) or 3)
        feedbacks = []

        for step in range(max_steps):
            if controller is not None:
                await controller.wait_for_turn(step)
                if controller.should_abort:
                    await self._emit(
                        trace_id,
                        "error",
                        {"message": "execution aborted by operator"},
                        status="aborted",
                        step=step,
                        error_code="ABORTED",
                    )
                    break

            action = await self.reasoning.generate_action(plan, observation)
            await self._emit(
                trace_id, "reasoning", {"step": step, "action": action}, step=step
            )

            # MuJoCo actions are short animations in this debugger path. Keep
            # execution inline so telemetry cannot hang on executor scheduling.
            try:
                receipt = simulation_service.execute_action(
                    action.get("action", ""),
                    action.get("params", {}),
                )
                feedback = {
                    "success": receipt.status.value == "success",
                    "step": step,
                    "action": action.get("action"),
                    "params": action.get("params", {}),
                    "result": receipt.result_message,
                    "result_data": receipt.result_data or {},
                }
            except Exception as e:
                feedback = {"success": False, "step": step, "result": str(e)}

            feedbacks.append(feedback)
            await self._emit(
                trace_id, "execution", {"step": step, "feedback": feedback}, step=step
            )

            # Refresh observation after every action so the next reasoning step
            # uses the latest world state (closed-loop control).
            try:
                observation = simulation_service.get_observation()
            except Exception:
                observation = observation

            improved = await self.learning.improve(action, feedback)
            await self._emit(
                trace_id,
                "learning",
                {"step": step, "improved_action": improved},
                step=step,
            )

            if controller is not None:
                controller.mark_step_completed()

        result_data = {
            "task_success": bool(feedbacks) and all(f.get("success", False) for f in feedbacks),
            "steps_executed": len(feedbacks),
        }
        await self._emit(trace_id, "result", result_data)
        return result_data


agent_bridge = AgentBridge()
