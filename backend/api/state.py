"""Robot state API endpoints."""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.models.state import JointState, RobotRuntimeState
from backend.services.state_store import state_store
from backend.services.websocket_manager import manager

router = APIRouter(prefix="/api/state", tags=["state"])

RobotState = RobotRuntimeState


def _resolve_backend(robot_id: str, state: RobotState) -> str:
    if state.backend != "unknown":
        return state.backend

    existing_state = state_store.get_robot_state(robot_id)
    if existing_state is not None:
        return existing_state.backend

    return "unknown"


@router.get("/{robot_id}", response_model=RobotState)
async def get_robot_state(robot_id: str):
    """Get current state of a robot."""
    state = state_store.get_robot_state(robot_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Robot state not found: {robot_id}")
    return state


@router.post("/{robot_id}")
async def update_robot_state(robot_id: str, state: RobotState):
    """Update robot state (called by simulation process)."""
    normalized_state = state.model_copy(
        update={"robot_id": robot_id, "backend": _resolve_backend(robot_id, state)}
    )
    state_store.put_robot_state(normalized_state)
    await manager.send_state(robot_id, normalized_state.model_dump(by_alias=True))
    return {"status": "updated"}


@router.websocket("/ws/{robot_id}")
async def websocket_state(websocket: WebSocket, robot_id: str):
    """WebSocket endpoint for real-time state updates."""
    await manager.connect(websocket, robot_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_state(robot_id, {"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, robot_id)
