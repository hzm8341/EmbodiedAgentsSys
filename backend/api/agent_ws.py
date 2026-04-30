"""WebSocket endpoint for agent task execution with telemetry streaming."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.models.task_protocol import TaskRequest
from backend.services.event_bus import EventBus
from backend.services.scenarios import list_scenarios
from backend.services.task_execution_service import task_execution_service
from backend.services.websocket_hub import WebSocketHub
from backend.api.auth import ensure_role, resolve_role
from agents.policy.validation_pipeline import TwoLevelValidationPipeline
from agents.human_oversight.engine import HumanOversightEngine


class ObservationPayload(BaseModel):
    """Payload used to hydrate a RobotObservation from JSON."""
    state: Dict[str, float] = Field(default_factory=dict)
    gripper: Dict[str, float] = Field(default_factory=dict)
    image: Optional[Any] = None


class ExecuteTaskRequest(BaseModel):
    """Frontend -> backend message to kick off a task."""
    type: str = Field(..., description="Must be 'execute_task'")
    task: str
    scenario: Optional[str] = None
    observation: ObservationPayload = Field(default_factory=ObservationPayload)
    max_steps: Optional[int] = None


router = APIRouter(prefix="/api/agent", tags=["agent"])
agent_event_bus = EventBus()
agent_websocket_hub = WebSocketHub(agent_event_bus)
policy_pipeline = TwoLevelValidationPipeline()
oversight_engine = HumanOversightEngine()


@router.get("/scenarios")
async def get_scenarios() -> list:
    """List all predefined debugging scenarios for the frontend catalog."""
    return list_scenarios()


def _simulation_service():
    from backend.services.simulation import simulation_service

    return simulation_service


def _parse_filter_values(raw: str | None) -> set[str] | None:
    if not raw:
        return None

    values = {item.strip() for item in raw.split(",") if item.strip()}
    return values or None


@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for agent task execution and telemetry.

    Clients send ``{"type": "execute_task", "task": ..., "observation": ..., "max_steps": ...}``
    and receive streaming messages (task_start, planning, reasoning, execution,
    learning, result) as the agent processes the task.
    """
    await agent_websocket_hub.connect(
        websocket,
        backend=websocket.query_params.get("backend"),
        event_types=_parse_filter_values(
            websocket.query_params.get("event") or websocket.query_params.get("type")
        ),
        robot_ids=_parse_filter_values(websocket.query_params.get("robot_id")),
        message_format="legacy",
    )
    session_id = f"ws-{id(websocket)}"
    token = websocket.query_params.get("token")
    operator_role = resolve_role(token)
    operator_identity = f"{operator_role or 'anonymous'}:{websocket.client.host if websocket.client else 'unknown'}"
    ws_backend = websocket.query_params.get("backend")
    pending_approval_request: TaskRequest | None = None
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"invalid JSON: {e}"},
                }))
                continue

            msg_type = payload.get("type", "")

            if msg_type == "switch_backend":
                backend_id = payload.get("backend")
                ws_backend = backend_id
                agent_websocket_hub.update_subscription(
                    websocket,
                    backend=backend_id if backend_id else None,
                    event_types=_parse_filter_values(payload.get("event")),
                    robot_ids=_parse_filter_values(payload.get("robot_id")),
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "backend_switched",
                            "data": {"backend": backend_id},
                        }
                    )
                )
                continue

            if msg_type == "subscribe":
                agent_websocket_hub.update_subscription(
                    websocket,
                    backend=payload.get("backend"),
                    event_types=_parse_filter_values(payload.get("event")),
                    robot_ids=_parse_filter_values(payload.get("robot_id")),
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "subscription_updated",
                            "data": {
                                "backend": payload.get("backend"),
                                "event": payload.get("event"),
                                "robot_id": payload.get("robot_id"),
                            },
                        }
                    )
                )
                continue

            if msg_type == "reset_to_home":
                result = _simulation_service().reset_to_home()
                await websocket.send_text(json.dumps({
                    "type": "reset_complete",
                    "data": result,
                }))
                continue

            if msg_type in {"pause_task", "resume_task", "abort_task", "step_task"}:
                command_map = {
                    "pause_task": "pause",
                    "resume_task": "resume",
                    "abort_task": "abort",
                    "step_task": "step",
                }
                result = task_execution_service.control_task(
                    session_id, command_map[msg_type]
                )
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "execution_control",
                            "data": {
                                "command": command_map[msg_type],
                                **result,
                            },
                        }
                    )
                )
                continue

            if msg_type == "task_status":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "execution_status",
                            "data": {
                                "state": task_execution_service.get_task_state(session_id)
                            },
                        }
                    )
                )
                continue

            if msg_type == "approve_task":
                if pending_approval_request is None:
                    await websocket.send_text(
                        json.dumps({"type": "error", "data": {"message": "no pending approval"}})
                    )
                    continue
                oversight_engine.approve()
                await task_execution_service.start_task(
                    session_id=session_id,
                    request=pending_approval_request,
                    downstream_stream_manager=agent_websocket_hub,
                    operator=operator_identity,
                )
                pending_approval_request = None
                await websocket.send_text(json.dumps({"type": "execution_status", "data": {"state": "running"}}))
                continue

            if msg_type == "reject_task":
                oversight_engine.reject()
                pending_approval_request = None
                await websocket.send_text(
                    json.dumps({"type": "approval_rejected", "data": {"state": "paused"}})
                )
                continue

            try:
                request = ExecuteTaskRequest(**payload)
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"invalid request: {e}"},
                }))
                continue

            if request.type != "execute_task":
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"unsupported type: {request.type}"},
                }))
                continue

            # Resolve scenario: try explicit name → task as name → task description match
            unified_request = TaskRequest(
                task=request.task,
                scenario=request.scenario,
                observation_state=dict(request.observation.state),
                observation_gripper=dict(request.observation.gripper),
                observation_image=request.observation.image,
                max_steps=request.max_steps,
            )
            risk_level = policy_pipeline.classify_task_risk(request.task)
            if ws_backend == "real_robot":
                try:
                    ensure_role(token, "operator")
                except Exception as e:
                    await websocket.send_text(
                        json.dumps({"type": "error", "data": {"message": str(e.detail if hasattr(e, 'detail') else e)}})
                    )
                    continue
            if risk_level == "high":
                pending_approval_request = unified_request
                oversight_engine.request_approval()
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "approval_required",
                            "data": {"risk_level": risk_level, "task": request.task},
                        }
                    )
                )
                continue

            try:
                await task_execution_service.start_task(
                    session_id=session_id,
                    request=unified_request,
                    downstream_stream_manager=agent_websocket_hub,
                    operator=operator_identity,
                )
            except RuntimeError as e:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "data": {"message": str(e)},
                        }
                    )
                )
                continue

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "execution_status",
                        "data": {"state": "running"},
                    }
                )
            )
    except WebSocketDisconnect:
        pass
    finally:
        task_execution_service.control_task(session_id, "abort")
        agent_websocket_hub.disconnect(websocket)
