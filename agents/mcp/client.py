from __future__ import annotations
import asyncio
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from agents.mcp.config import MCPConfig
from agents.exceptions import HardwareError


class HealthStatus(str, Enum):
    CONNECTED = "connected"
    NEEDS_AUTH = "needs_auth"
    FAILED = "failed"
    DISCONNECTED = "disconnected"


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    content: Any
    is_error: bool = False


@dataclass
class Resource:
    uri: str
    name: str
    description: str = ""


@dataclass
class ResourceContent:
    uri: str
    content: str
    mime_type: str = "text/plain"


class MCPClient:
    def __init__(self, config: MCPConfig) -> None:
        self._config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self.health_status = HealthStatus.DISCONNECTED

    async def connect(self) -> HealthStatus:
        try:
            env = {**os.environ, **self._config.env}
            self._process = await asyncio.create_subprocess_exec(
                self._config.command, *self._config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            result = await self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "embodied-agents", "version": "1.0.0"},
            })
            if result:
                self.health_status = HealthStatus.CONNECTED
            return self.health_status
        except Exception:
            self.health_status = HealthStatus.FAILED
            return self.health_status

    async def disconnect(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except Exception:
                pass
            self._process = None
        self.health_status = HealthStatus.DISCONNECTED

    async def health_check(self) -> HealthStatus:
        return self.health_status

    async def list_tools(self) -> list[MCPTool]:
        if self.health_status != HealthStatus.CONNECTED:
            return []
        result = await self._request("tools/list", {})
        if not result:
            return []
        return [
            MCPTool(name=t["name"], description=t.get("description", ""), input_schema=t.get("inputSchema", {}))
            for t in result.get("tools", [])
        ]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        if self.health_status != HealthStatus.CONNECTED:
            raise HardwareError(f"MCP server '{self._config.name}' is not connected")
        result = await self._request("tools/call", {"name": name, "arguments": arguments})
        if result is None:
            return ToolResult(content=None, is_error=True)
        return ToolResult(content=result.get("content"), is_error=result.get("isError", False))

    async def list_resources(self) -> list[Resource]:
        if self.health_status != HealthStatus.CONNECTED:
            return []
        result = await self._request("resources/list", {})
        if not result:
            return []
        return [Resource(uri=r["uri"], name=r.get("name", ""), description=r.get("description", ""))
                for r in result.get("resources", [])]

    async def read_resource(self, uri: str) -> ResourceContent:
        if self.health_status != HealthStatus.CONNECTED:
            raise HardwareError(f"MCP server '{self._config.name}' not connected")
        result = await self._request("resources/read", {"uri": uri})
        contents = result.get("contents", [{}]) if result else [{}]
        first = contents[0] if contents else {}
        return ResourceContent(uri=uri, content=first.get("text", ""), mime_type=first.get("mimeType", "text/plain"))

    async def _request(self, method: str, params: dict) -> Optional[dict]:
        if not self._process or not self._process.stdin or not self._process.stdout:
            return None
        self._request_id += 1
        payload = json.dumps({"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}) + "\n"
        try:
            self._process.stdin.write(payload.encode())
            await self._process.stdin.drain()
            line = await asyncio.wait_for(self._process.stdout.readline(), timeout=self._config.timeout)
            response = json.loads(line.decode())
            return response.get("result")
        except Exception:
            return None
