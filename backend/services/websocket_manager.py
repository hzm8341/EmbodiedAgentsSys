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


class AgentStreamManager:
    """Broadcast-style WebSocket manager for agent task telemetry.

    All connected clients receive every message. Not tied to robot_id.
    """

    def __init__(self):
        self.active_connections: set = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket. Safe to call on unknown websocket."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connections. Failed connections are dropped."""
        if not self.active_connections:
            return

        payload = json.dumps(message)
        failed = []
        for ws in list(self.active_connections):
            try:
                await ws.send_text(payload)
            except Exception:
                failed.append(ws)

        for ws in failed:
            self.disconnect(ws)


agent_stream_manager = AgentStreamManager()
