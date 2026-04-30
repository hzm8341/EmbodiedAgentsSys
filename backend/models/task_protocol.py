"""Unified task execution protocol models (v1)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActionCommand(BaseModel):
    """Structured action command in unified protocol."""

    protocol_version: str = "v1"
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


class TaskRequest(BaseModel):
    """Task request shared by REST and WebSocket entries."""

    protocol_version: str = "v1"
    task: str
    scenario: str | None = None
    observation_state: dict[str, float] = Field(default_factory=dict)
    observation_gripper: dict[str, float] = Field(default_factory=dict)
    observation_image: Any | None = None
    max_steps: int | None = None


class ExecutionEvent(BaseModel):
    """Execution event shared by all emitters."""

    protocol_version: str = "v1"
    type: str
    timestamp: float
    status: str = "completed"
    step: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None


class TaskResult(BaseModel):
    """Task result shared by REST and WebSocket entries."""

    protocol_version: str = "v1"
    task: str
    success: bool
    steps_executed: int
    message: str = ""
    events: list[ExecutionEvent] = Field(default_factory=list)
    scene_state: dict[str, Any] | None = None

