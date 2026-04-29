from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


def _freeze_metadata(value: Any) -> Any:
    if isinstance(value, MappingABC):
        return MappingProxyType(
            {key: _freeze_metadata(nested_value) for key, nested_value in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_metadata(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_metadata(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class BackendDescriptor:
    backend_id: str
    display_name: str
    kind: str
    available: bool = True
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    extensions: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(self, "extensions", _freeze_metadata(dict(self.extensions)))


class SimulationBackend(ABC):
    @property
    @abstractmethod
    def descriptor(self) -> BackendDescriptor:
        raise NotImplementedError

    @property
    def backend_id(self) -> str:
        return self.descriptor.backend_id

    def execute_command(self, action: str, params: Mapping[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"Backend {self.backend_id} does not support command execution")
