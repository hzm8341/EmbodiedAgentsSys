"""Shared task execution service used by REST and WebSocket entries."""
from __future__ import annotations

import asyncio
from typing import Any

from agents.core.types import RobotObservation
from backend.models.task_protocol import ExecutionEvent, TaskRequest, TaskResult
from backend.services.agent_bridge import agent_bridge
from backend.services.scenarios import SCENARIOS
from backend.services.trace_store import trace_store


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
        trace_id: str | None = None
        for message in collector.raw_events:
            payload = message.get("payload", message.get("data", {}))
            trace_id = trace_id or message.get("trace_id")
            events.append(
                ExecutionEvent(
                    protocol_version=str(message.get("protocol_version", "v1")),
                    type=message.get("type", "unknown"),
                    timestamp=float(message.get("timestamp", 0.0)),
                    status=str(message.get("status", "completed")),
                    trace_id=message.get("trace_id"),
                    step=message.get("step"),
                    payload=payload if isinstance(payload, dict) else {},
                    error_code=message.get("error_code"),
                )
            )
            if trace_id:
                trace_store.append_event(trace_id, message)

        scene_state = self._simulation_service().get_scene()
        task_result = TaskResult(
            task=request.task,
            trace_id=trace_id,
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
        if trace_id:
            trace_store.append_result(
                trace_id,
                task=request.task,
                result=task_result.model_dump(),
                operator=None,
            )
        return task_result

    @staticmethod
    def _simulation_service():
        from backend.services.simulation import simulation_service

        return simulation_service


task_execution_service = TaskExecutionService()
