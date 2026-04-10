"""Robot state API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.services.websocket_manager import manager

router = APIRouter(prefix="/api/state", tags=["state"])


class JointState(BaseModel):
    joint_name: str
    position: float
    velocity: Optional[float] = None


class RobotState(BaseModel):
    robot_id: str
    joints: List[JointState]
    timestamp: float


_current_states: dict = {}


@router.get("/{robot_id}", response_model=RobotState)
async def get_robot_state(robot_id: str):
    """Get current state of a robot."""
    if robot_id not in _current_states:
        return RobotState(
            robot_id=robot_id,
            joints=[],
            timestamp=0.0
        )
    return _current_states[robot_id]


@router.post("/{robot_id}")
async def update_robot_state(robot_id: str, state: RobotState):
    """Update robot state (called by simulation process)."""
    _current_states[robot_id] = state
    await manager.send_state(robot_id, state.dict())
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
