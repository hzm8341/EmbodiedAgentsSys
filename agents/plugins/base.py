from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class HookEvent(str, Enum):
    TASK_START = "task_start"
    TASK_END = "task_end"
    SKILL_START = "skill_start"
    SKILL_END = "skill_end"


@dataclass
class Hook:
    event: HookEvent
    handler: Any
    description: str = ""


class Plugin(ABC):
    name: str = ""
    version: str = "0.0.0"
    description: str = ""

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...

    def get_tools(self) -> list[Any]:
        return []

    def get_skills(self) -> list[Any]:
        return []

    def get_hooks(self) -> list[Hook]:
        return []
