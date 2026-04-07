from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class MCPScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"


@dataclass
class MCPConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    scope: MCPScope = MCPScope.PROJECT

    @property
    def server_id(self) -> str:
        return self.name

    @classmethod
    def from_dict(cls, data: dict) -> "MCPConfig":
        scope_raw = data.get("scope", "project")
        try:
            scope = MCPScope(scope_raw)
        except ValueError:
            scope = MCPScope.PROJECT
        return cls(
            name=data["name"],
            command=data["command"],
            args=data.get("args", []),
            env=data.get("env", {}),
            timeout=float(data.get("timeout", 30.0)),
            scope=scope,
        )
