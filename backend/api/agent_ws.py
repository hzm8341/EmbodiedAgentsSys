"""WebSocket endpoint for agent task execution with telemetry streaming."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from agents.core.types import RobotObservation
from backend.services.agent_bridge import agent_bridge
from backend.services.websocket_manager import agent_stream_manager


class ObservationPayload(BaseModel):
    """Payload used to hydrate a RobotObservation from JSON."""
    state: Dict[str, float] = Field(default_factory=dict)
    gripper: Dict[str, float] = Field(default_factory=dict)
    image: Optional[Any] = None


class ExecuteTaskRequest(BaseModel):
    """Frontend -> backend message to kick off a task."""
    type: str = Field(..., description="Must be 'execute_task'")
    task: str
    observation: ObservationPayload = Field(default_factory=ObservationPayload)
    max_steps: int = 3


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for agent task execution and telemetry.

    Clients send ``{"type": "execute_task", "task": ..., "observation": ..., "max_steps": ...}``
    and receive streaming messages (task_start, planning, reasoning, execution,
    learning, result) as the agent processes the task.
    """
    await agent_stream_manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
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

            observation = RobotObservation(
                state=dict(request.observation.state),
                gripper=dict(request.observation.gripper),
                image=request.observation.image,
            )
            await agent_bridge.run_with_telemetry(
                task=request.task,
                observation=observation,
                max_steps=request.max_steps,
            )
    except WebSocketDisconnect:
        pass
    finally:
        agent_stream_manager.disconnect(websocket)
