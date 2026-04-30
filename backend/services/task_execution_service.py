"""Shared task execution service used by REST and WebSocket entries."""
from __future__ import annotations

import asyncio
from typing import Any

from agents.core.types import RobotObservation
from backend.models.task_protocol import ExecutionEvent, TaskRequest, TaskResult
from backend.services.agent_bridge import agent_bridge
from backend.services.scenarios import SCENARIOS


class _NoopStreamManager:
    async def broadcast(self, message: dict[str, Any]) -> None:
        return None


class _CollectingStreamManager:
    """Collect emitted events while optionally forwarding to downstream manager."""

    def __init__(self, downstream: Any | None = None) -> None:
        self.downstream = downstream
        self.raw_events: list[dict[str, Any]] = []

    async def broadcast(self, message: dict[str, Any]) -> None:
        self.raw_events.append(message)
        if self.downstream is not None:
            await self.downstream.broadcast(message)


class TaskExecutionService:
    def __init__(self) -> None:
        self._bridge_lock = asyncio.Lock()

    async def execute_task(
        self,
        request: TaskRequest,
        downstream_stream_manager: Any | None = None,
    ) -> TaskResult:
        """Execute a task through the single authoritative path."""
        scenario = (
            SCENARIOS.get(request.scenario)
            or SCENARIOS.get(request.task)
            or next((s for s in SCENARIOS.values() if s.task == request.task), None)
        )
        action_sequence = scenario.action_sequence if scenario else None

        if scenario and not any(request.observation_state):
            observation = scenario.build_observation()
        else:
            observation = RobotObservation(
                state=dict(request.observation_state),
                gripper=dict(request.observation_gripper),
                image=request.observation_image,
            )

        collector = _CollectingStreamManager(
            downstream_stream_manager or _NoopStreamManager()
        )

        async with self._bridge_lock:
            previous_stream_manager = agent_bridge.stream_manager
            agent_bridge.stream_manager = collector
            try:
                result_data = await agent_bridge.run_with_telemetry(
                    task=request.task,
                    observation=observation,
                    action_sequence=action_sequence,
                    max_steps=request.max_steps,
                )
            finally:
                agent_bridge.stream_manager = previous_stream_manager

        events: list[ExecutionEvent] = []
        for message in collector.raw_events:
            data = message.get("data", {})
            events.append(
                ExecutionEvent(
                    type=message.get("type", "unknown"),
                    timestamp=float(message.get("timestamp", 0.0)),
                    status=str(message.get("status", "completed")),
                    step=data.get("step"),
                    payload=data if isinstance(data, dict) else {},
                )
            )

        scene_state = self._simulation_service().get_scene()
        return TaskResult(
            task=request.task,
            success=bool(result_data.get("task_success", False)),
            steps_executed=int(result_data.get("steps_executed", 0)),
            message=(
                "task executed successfully"
                if result_data.get("task_success", False)
                else "task execution failed"
            ),
            events=events,
            scene_state=scene_state,
        )

    @staticmethod
    def _simulation_service():
        from backend.services.simulation import simulation_service

        return simulation_service


task_execution_service = TaskExecutionService()

