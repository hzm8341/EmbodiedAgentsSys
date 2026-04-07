from __future__ import annotations
import asyncio
from typing import Optional
from agents.mcp.client import MCPClient, HealthStatus
from agents.mcp.config import MCPConfig


class MCPServerManager:
    def __init__(self) -> None:
        self._servers: dict[str, MCPClient] = {}

    def add_server(self, config: MCPConfig) -> str:
        client = MCPClient(config)
        self._servers[config.server_id] = client
        return config.server_id

    def remove_server(self, server_id: str) -> None:
        self._servers.pop(server_id, None)

    def get_server(self, server_id: str) -> Optional[MCPClient]:
        return self._servers.get(server_id)

    def list_servers(self) -> list[dict]:
        return [{"name": sid, "health": client.health_status.value}
                for sid, client in self._servers.items()]

    async def check_all_health(self) -> dict[str, HealthStatus]:
        results = await asyncio.gather(
            *(client.health_check() for client in self._servers.values()),
            return_exceptions=True,
        )
        return {
            sid: (r if isinstance(r, HealthStatus) else HealthStatus.FAILED)
            for sid, r in zip(self._servers.keys(), results)
        }
