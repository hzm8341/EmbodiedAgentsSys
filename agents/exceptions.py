"""Unified error hierarchy for EmbodiedAgentsSys.

Aligned with Claude Code utils/errors.ts:
  - AgentError as base
  - AbortError for cancellation (cascades with AbortController)
  - Domain-specific subclasses for VLA, hardware, planning
  - TelemetrySafeError for errors safe to log without scrubbing
  - Utility functions: is_abort_error, classify_error, short_error_stack
"""
from __future__ import annotations

import asyncio
import traceback
from enum import Enum
from typing import Any


class AgentError(Exception):
    """Base class for all EmbodiedAgentsSys errors."""


class AbortError(AgentError):
    """Raised when an operation is intentionally cancelled."""


class OperationCancelledError(AbortError):
    """Wraps asyncio.CancelledError for typed catching."""


class VLAActionError(AgentError):
    """VLA inference or action execution failed."""


class HardwareError(AgentError):
    """Robotic arm or sensor communication failure."""


class PlanningError(AgentError):
    """CoT task planning failed to produce a valid plan."""


class ConfigParseError(AgentError):
    """Configuration file could not be parsed."""

    def __init__(self, message: str, file_path: str = "") -> None:
        super().__init__(message)
        self.file_path = file_path


class TelemetrySafeError(AgentError):
    """Error whose message is safe to log to telemetry without scrubbing."""


class ErrorKind(str, Enum):
    ABORT = "abort"
    VLA_ACTION = "vla_action"
    HARDWARE = "hardware"
    PLANNING = "planning"
    CONFIG = "config"
    UNKNOWN = "unknown"


def is_abort_error(e: Any) -> bool:
    """Return True if e represents any kind of abort/cancellation."""
    return isinstance(e, (AbortError, asyncio.CancelledError))


def classify_error(e: Exception) -> ErrorKind:
    """Map an exception to its ErrorKind for routing and metrics."""
    if isinstance(e, AbortError):
        return ErrorKind.ABORT
    if isinstance(e, VLAActionError):
        return ErrorKind.VLA_ACTION
    if isinstance(e, HardwareError):
        return ErrorKind.HARDWARE
    if isinstance(e, PlanningError):
        return ErrorKind.PLANNING
    if isinstance(e, ConfigParseError):
        return ErrorKind.CONFIG
    return ErrorKind.UNKNOWN


def short_error_stack(e: Any, max_frames: int = 5) -> str:
    """Return a concise string representation of an error."""
    if not isinstance(e, BaseException):
        return str(e)
    tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
    frame_lines = tb_lines[1:-1]
    if len(frame_lines) > max_frames:
        frame_lines = frame_lines[-max_frames:]
    all_lines = [tb_lines[0]] + frame_lines + [tb_lines[-1]]
    return "".join(ln for ln in all_lines if ln.strip()).strip()
