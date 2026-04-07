"""Hierarchical abort controller for EmbodiedAgentsSys."""
from __future__ import annotations
from typing import Callable, Optional
from agents.exceptions import AbortError


class AbortSignal:
    """Read-only view of an AbortController's state."""
    def __init__(self, controller: "AbortController") -> None:
        self._controller = controller

    @property
    def is_aborted(self) -> bool:
        return self._controller.is_aborted

    @property
    def abort_reason(self) -> Optional[str]:
        return self._controller.abort_reason


class AbortController:
    """Hierarchical abort controller — parent abort cascades to children."""

    def __init__(self) -> None:
        self._aborted = False
        self._reason: Optional[str] = None
        self._children: list["AbortController"] = []
        self._callbacks: list[Callable[[], None]] = []

    def abort(self, reason: str = "") -> None:
        """Abort this controller and all descendants. Idempotent."""
        if self._aborted:
            return
        self._aborted = True
        self._reason = reason
        for child in self._children:
            child.abort(reason)
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass

    def create_child(self) -> "AbortController":
        """Return a new controller cancelled when this one is."""
        child = AbortController()
        self._children.append(child)
        return child

    def add_done_callback(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked when abort() is called."""
        self._callbacks.append(cb)

    @property
    def is_aborted(self) -> bool:
        return self._aborted

    @property
    def abort_reason(self) -> Optional[str]:
        return self._reason

    @property
    def signal(self) -> AbortSignal:
        return AbortSignal(self)


class AbortScope:
    """Async context manager that raises AbortError if controller was aborted."""

    def __init__(self, controller: AbortController) -> None:
        self._controller = controller

    async def __aenter__(self) -> AbortController:
        return self._controller

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._controller.is_aborted and exc_type is None:
            raise AbortError(self._controller.abort_reason or "aborted")
        if exc_type is not None and issubclass(exc_type, AbortError):
            return None
        return None
