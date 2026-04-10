"""WebSocket connection manager."""
from typing import Dict, List, Set
from fastapi import WebSocket
import asyncio
import json


class WebSocketManager:
    """Manages WebSocket connections for robot state updates."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, robot_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if robot_id not in self.active_connections:
            self.active_connections[robot_id] = set()
        self.active_connections[robot_id].add(websocket)

    def disconnect(self, websocket: WebSocket, robot_id: str):
        """Remove a WebSocket connection."""
        if robot_id in self.active_connections:
            self.active_connections[robot_id].discard(websocket)
            if not self.active_connections[robot_id]:
                del self.active_connections[robot_id]

    async def send_state(self, robot_id: str, state: dict):
        """Broadcast state to all connections for a robot."""
        if robot_id not in self.active_connections:
            return

        message = json.dumps(state)
        disconnected = []

        for websocket in self.active_connections[robot_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws, robot_id)

    async def broadcast(self, message: str):
        """Broadcast message to all connections."""
        for robot_id in self.active_connections:
            await self.send_state(robot_id, {"type": "broadcast", "data": message})


manager = WebSocketManager()
