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
            await task_execution_service.execute_task(
                unified_request,
                downstream_stream_manager=agent_websocket_hub,
            )
    except WebSocketDisconnect:
        pass
    finally:
        agent_websocket_hub.disconnect(websocket)
