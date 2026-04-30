"""Shared task execution service used by REST and WebSocket entries."""
from __future__ import annotations

import asyncio
from typing import Any

from agents.core.types import RobotObservation
from agents.core.task_state_machine import TaskStateMachine
from agents.cognition.planning import DefaultPlanningLayer
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
        self._controls: dict[str, "_ExecutionController"] = {}
        self._tasks: dict[str, asyncio.Task[TaskResult]] = {}

    async def start_task(
        self,
        *,
        session_id: str,
        request: TaskRequest,
        downstream_stream_manager: Any | None = None,
        operator: str | None = None,
    ) -> None:
        if session_id in self._tasks and not self._tasks[session_id].done():
            raise RuntimeError("task already running in this session")
        controller = _ExecutionController()
        self._controls[session_id] = controller
        self._tasks[session_id] = asyncio.create_task(
            self.execute_task(
                request,
                downstream_stream_manager=downstream_stream_manager,
                controller=controller,
                operator=operator,
            )
        )

    def control_task(self, session_id: str, command: str) -> dict[str, Any]:
        controller = self._controls.get(session_id)
        if controller is None:
            return {"ok": False, "message": "no active task"}
        if command == "pause":
            controller.pause()
        elif command == "resume":
            controller.resume()
        elif command == "abort":
            controller.abort()
        elif command == "step":
            controller.step_once()
        else:
            return {"ok": False, "message": f"unsupported control: {command}"}
        return {"ok": True, "state": controller.state}

    def get_task_state(self, session_id: str) -> str:
        controller = self._controls.get(session_id)
        if controller is None:
            return "idle"
        return controller.state

    async def await_session_task(self, session_id: str) -> TaskResult | None:
        task = self._tasks.get(session_id)
        if task is None:
            return None
        try:
            return await task
        finally:
            self._tasks.pop(session_id, None)
            self._controls.pop(session_id, None)

    async def execute_task(
        self,
        request: TaskRequest,
        downstream_stream_manager: Any | None = None,
        controller: "_ExecutionController | None" = None,
        operator: str | None = None,
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
        planner = DefaultPlanningLayer()
        machine = TaskStateMachine(max_replans=1)
        aggregated_result_data = {"task_success": False, "steps_executed": 0}

        async with self._bridge_lock:
            previous_stream_manager = agent_bridge.stream_manager
            agent_bridge.stream_manager = collector
            try:
                current_task = request.task
                current_sequence = action_sequence
                while not machine.terminal:
                    machine.on_execute_started()
                    result_data = await agent_bridge.run_with_telemetry(
                        task=current_task,
                        observation=observation,
                        action_sequence=current_sequence,
                        max_steps=request.max_steps,
                        controller=controller,
                    )
                    machine.on_execute_finished()
                    machine.on_verified(bool(result_data.get("task_success", False)))
                    aggregated_result_data["steps_executed"] += int(
                        result_data.get("steps_executed", 0)
                    )
                    if machine.state == "done":
                        aggregated_result_data["task_success"] = True
                    if machine.state == "replanning":
                        replan = await planner.replan(
                            current_task,
                            reason="verification_failed",
                            attempt=machine.replan_attempts,
                        )
                        current_task = replan.get("task", current_task)
                        current_sequence = replan.get("action_sequence", [])
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
                trace_store.append_event(trace_id, message, operator=operator)

        scene_state = self._simulation_service().get_scene()
        task_result = TaskResult(
            task=request.task,
            trace_id=trace_id,
            success=bool(aggregated_result_data.get("task_success", False)),
            steps_executed=int(aggregated_result_data.get("steps_executed", 0)),
            message=(
                "task executed successfully"
                if aggregated_result_data.get("task_success", False)
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
                operator=operator,
            )
        if controller is not None and controller.state != "aborted":
            controller.complete()
        return task_result

    @staticmethod
    def _simulation_service():
        from backend.services.simulation import simulation_service

        return simulation_service


task_execution_service = TaskExecutionService()


class _ExecutionController:
    def __init__(self) -> None:
        self.state = "running"
        self.should_abort = False
        self._resume_event = asyncio.Event()
        self._resume_event.set()
        self._single_step_budget = 0

    async def wait_for_turn(self, step: int) -> None:
        while True:
            if self.should_abort:
                return
            await self._resume_event.wait()
            if self._single_step_budget > 0:
                self._single_step_budget -= 1
                if self._single_step_budget == 0 and self.state == "stepping":
                    self.pause()
                return
            if self.state in ("running", "completed"):
                return
            await asyncio.sleep(0.01)

    def pause(self) -> None:
        if self.state in ("running", "stepping"):
            self.state = "paused"
            self._resume_event.clear()

    def resume(self) -> None:
        if self.state in ("paused", "stepping"):
            self.state = "running"
            self._single_step_budget = 0
            self._resume_event.set()

    def step_once(self) -> None:
        if self.state == "paused":
            self.state = "stepping"
            self._single_step_budget = 1
            self._resume_event.set()

    def abort(self) -> None:
        self.should_abort = True
        self.state = "aborted"
        self._resume_event.set()

    def mark_step_completed(self) -> None:
        if self.state == "stepping" and self._single_step_budget == 0:
            self.pause()

    def complete(self) -> None:
        self.state = "completed"
