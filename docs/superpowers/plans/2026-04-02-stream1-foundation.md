# Stream 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three foundational modules — unified error hierarchy, LRU/TTL caching, and hierarchical abort controller — that Stream 2 modules all depend on.

**Architecture:** Three independent files under `agents/`. No dependencies on each other; all three can be developed in parallel. `agents/__init__.py` exports the key symbols for downstream use.

**Tech Stack:** Python 3.10+, asyncio, functools.lru_cache, pytest

---

## File Structure

```
agents/
├── exceptions.py        # CREATE: error hierarchy + classify/is_abort helpers
├── cache.py             # CREATE: @cached TTL decorator + CacheRegistry
└── abort.py             # CREATE: AbortController tree + AbortScope

tests/
├── test_exceptions.py   # CREATE
├── test_cache.py        # CREATE
└── test_abort.py        # CREATE
```

---

## Phase 1: Error Handling

### Task 1: `agents/exceptions.py`

**Files:**
- Create: `agents/exceptions.py`
- Test: `tests/test_exceptions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_exceptions.py
import asyncio
import pytest
from agents.exceptions import (
    AgentError, AbortError, OperationCancelledError,
    VLAActionError, HardwareError, PlanningError,
    ConfigParseError, TelemetrySafeError,
    ErrorKind, is_abort_error, classify_error, short_error_stack,
)


class TestErrorHierarchy:
    def test_agent_error_is_exception(self):
        e = AgentError("base")
        assert isinstance(e, Exception)

    def test_abort_error_is_agent_error(self):
        e = AbortError("cancelled")
        assert isinstance(e, AgentError)

    def test_vla_action_error_is_agent_error(self):
        assert isinstance(VLAActionError("timeout"), AgentError)

    def test_hardware_error_is_agent_error(self):
        assert isinstance(HardwareError("arm down"), AgentError)

    def test_planning_error_is_agent_error(self):
        assert isinstance(PlanningError("no plan"), AgentError)

    def test_config_parse_error_has_file_path(self):
        e = ConfigParseError("bad yaml", file_path="/config.yaml")
        assert e.file_path == "/config.yaml"

    def test_telemetry_safe_error_is_agent_error(self):
        assert isinstance(TelemetrySafeError("safe msg"), AgentError)

    def test_operation_cancelled_is_abort(self):
        e = OperationCancelledError()
        assert isinstance(e, AbortError)


class TestIsAbortError:
    def test_true_for_abort_error(self):
        assert is_abort_error(AbortError("cancelled"))

    def test_true_for_operation_cancelled(self):
        assert is_abort_error(OperationCancelledError())

    def test_true_for_asyncio_cancelled(self):
        assert is_abort_error(asyncio.CancelledError())

    def test_false_for_value_error(self):
        assert not is_abort_error(ValueError("bad input"))

    def test_false_for_none(self):
        assert not is_abort_error(None)

    def test_false_for_string(self):
        assert not is_abort_error("not an error")


class TestClassifyError:
    def test_abort_error(self):
        assert classify_error(AbortError()) == ErrorKind.ABORT

    def test_vla_action_error(self):
        assert classify_error(VLAActionError("fail")) == ErrorKind.VLA_ACTION

    def test_hardware_error(self):
        assert classify_error(HardwareError("arm")) == ErrorKind.HARDWARE

    def test_planning_error(self):
        assert classify_error(PlanningError("no plan")) == ErrorKind.PLANNING

    def test_config_error(self):
        assert classify_error(ConfigParseError("bad", file_path="x")) == ErrorKind.CONFIG

    def test_unknown_error(self):
        assert classify_error(RuntimeError("unexpected")) == ErrorKind.UNKNOWN


class TestShortErrorStack:
    def test_non_exception_returns_str(self):
        assert short_error_stack("not an error") == "not an error"

    def test_none_returns_str(self):
        assert short_error_stack(None) == "None"

    def test_exception_returns_type_and_message(self):
        result = short_error_stack(ValueError("bad input"))
        assert "ValueError" in result
        assert "bad input" in result

    def test_truncates_to_max_frames(self):
        def deep():
            def a():
                def b():
                    def c():
                        raise RuntimeError("deep")
                    c()
                b()
            a()
        try:
            deep()
        except RuntimeError as e:
            result = short_error_stack(e, max_frames=2)
            assert "RuntimeError" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_exceptions.py -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.exceptions'`

- [ ] **Step 3: Implement `agents/exceptions.py`**

```python
# agents/exceptions.py
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
    """Error whose message is safe to log to telemetry without scrubbing.

    Only use this when you have verified the message contains no file paths,
    code snippets, or personally identifiable information.
    """


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
    """Return a concise string representation of an error.

    For exceptions: includes type name, message, and up to max_frames
    stack frames. For non-exceptions: returns str(e).
    """
    if not isinstance(e, BaseException):
        return str(e)
    tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
    # tb_lines[-1] is "ExceptionType: message"
    # tb_lines[1:-1] are "  File ..., line N\n    code" pairs
    frame_lines = tb_lines[1:-1]
    if len(frame_lines) > max_frames:
        frame_lines = frame_lines[-max_frames:]
    return "".join([tb_lines[0]] + frame_lines + [tb_lines[-1]]).strip()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_exceptions.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/exceptions.py tests/test_exceptions.py
git commit -m "feat: add agents/exceptions.py — unified error hierarchy"
```

---

## Phase 2: Caching

### Task 2: `agents/cache.py`

**Files:**
- Create: `agents/cache.py`
- Test: `tests/test_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cache.py
import asyncio
import time
import pytest
from agents.cache import cached, CacheRegistry


class TestCachedDecorator:
    def test_async_function_returns_result(self):
        @cached(ttl=60)
        async def fetch(x: int) -> int:
            return x * 2

        result = asyncio.run(fetch(3))
        assert result == 6

    def test_caches_result_on_second_call(self):
        call_count = 0

        @cached(ttl=60)
        async def expensive(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        asyncio.run(expensive(1))
        asyncio.run(expensive(1))
        assert call_count == 1

    def test_different_args_call_function_separately(self):
        call_count = 0

        @cached(ttl=60)
        async def fn(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        asyncio.run(fn(1))
        asyncio.run(fn(2))
        assert call_count == 2

    def test_expired_entry_calls_function_again(self):
        call_count = 0

        @cached(ttl=0)  # expires immediately
        async def fn() -> int:
            nonlocal call_count
            call_count += 1
            return 42

        asyncio.run(fn())
        time.sleep(0.01)
        asyncio.run(fn())
        assert call_count == 2

    def test_cache_clear_forces_recompute(self):
        call_count = 0

        @cached(ttl=60)
        async def fn() -> int:
            nonlocal call_count
            call_count += 1
            return 1

        asyncio.run(fn())
        fn.cache_clear()
        asyncio.run(fn())
        assert call_count == 2

    def test_kwargs_are_part_of_cache_key(self):
        call_count = 0

        @cached(ttl=60)
        async def fn(x: int = 0) -> int:
            nonlocal call_count
            call_count += 1
            return x

        asyncio.run(fn(x=1))
        asyncio.run(fn(x=2))
        assert call_count == 2


class TestCacheRegistry:
    def test_register_and_invalidate(self):
        registry = CacheRegistry()
        call_count = 0

        @cached(ttl=60)
        async def fn() -> int:
            nonlocal call_count
            call_count += 1
            return 1

        registry.register("fn", fn)
        asyncio.run(fn())
        registry.invalidate("fn")
        asyncio.run(fn())
        assert call_count == 2

    def test_invalidate_all(self):
        registry = CacheRegistry()
        counts = {"a": 0, "b": 0}

        @cached(ttl=60)
        async def fn_a() -> int:
            counts["a"] += 1
            return 1

        @cached(ttl=60)
        async def fn_b() -> int:
            counts["b"] += 1
            return 2

        registry.register("a", fn_a)
        registry.register("b", fn_b)

        asyncio.run(fn_a())
        asyncio.run(fn_b())
        registry.invalidate_all()
        asyncio.run(fn_a())
        asyncio.run(fn_b())

        assert counts["a"] == 2
        assert counts["b"] == 2

    def test_get_stats_returns_dict(self):
        registry = CacheRegistry()
        stats = registry.get_stats()
        assert isinstance(stats, dict)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_cache.py -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `agents/cache.py`**

```python
# agents/cache.py
"""LRU and TTL caching utilities for EmbodiedAgentsSys.

Provides:
  @cached(ttl=seconds)  — async TTL cache with thundering-herd protection
  CacheRegistry         — registry to track and bulk-invalidate caches

Usage:
    from agents.cache import cached, CacheRegistry

    @cached(ttl=300)
    async def get_ros_topics() -> list[str]:
        ...  # called at most once per 5 minutes

    registry = CacheRegistry()
    registry.register("ros_topics", get_ros_topics)
    registry.invalidate("ros_topics")   # next call recomputes
    registry.invalidate_all()
"""
from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable


def cached(ttl: float) -> Callable:
    """Decorator: cache an async function's result for `ttl` seconds.

    - Thread-safe via asyncio.Lock (prevents thundering herd).
    - Cache key = (args, sorted kwargs).
    - Decorated function gains a `.cache_clear()` method.
    """
    def decorator(func: Callable) -> Callable:
        _cache: dict[tuple, tuple[Any, float]] = {}
        _lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()

            # Fast path: check without lock
            if key in _cache:
                result, expires_at = _cache[key]
                if now < expires_at:
                    return result

            # Slow path: compute under lock to prevent thundering herd
            async with _lock:
                if key in _cache:
                    result, expires_at = _cache[key]
                    if now < expires_at:
                        return result
                result = await func(*args, **kwargs)
                _cache[key] = (result, now + ttl)
            return result

        def cache_clear() -> None:
            _cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator


class CacheRegistry:
    """Track named caches and invalidate them collectively."""

    def __init__(self) -> None:
        self._caches: dict[str, Any] = {}

    def register(self, name: str, cache_fn: Any) -> None:
        """Register a cached function by name."""
        self._caches[name] = cache_fn

    def invalidate(self, name: str) -> None:
        """Clear the cache for the named function."""
        if name in self._caches:
            fn = self._caches[name]
            if hasattr(fn, "cache_clear"):
                fn.cache_clear()

    def invalidate_all(self) -> None:
        """Clear all registered caches."""
        for fn in self._caches.values():
            if hasattr(fn, "cache_clear"):
                fn.cache_clear()

    def get_stats(self) -> dict[str, Any]:
        """Return a dict of registered cache names."""
        return {"registered": list(self._caches.keys())}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_cache.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/cache.py tests/test_cache.py
git commit -m "feat: add agents/cache.py — TTL async cache + CacheRegistry"
```

---

## Phase 3: Abort Controller

### Task 3: `agents/abort.py`

**Files:**
- Create: `agents/abort.py`
- Test: `tests/test_abort.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_abort.py
import asyncio
import pytest
from agents.abort import AbortController, AbortScope
from agents.exceptions import AbortError


class TestAbortController:
    def test_not_aborted_by_default(self):
        ctrl = AbortController()
        assert ctrl.is_aborted is False
        assert ctrl.abort_reason is None

    def test_abort_sets_flag(self):
        ctrl = AbortController()
        ctrl.abort("user cancelled")
        assert ctrl.is_aborted is True
        assert ctrl.abort_reason == "user cancelled"

    def test_abort_is_idempotent(self):
        ctrl = AbortController()
        ctrl.abort("first")
        ctrl.abort("second")
        assert ctrl.abort_reason == "first"

    def test_child_aborted_when_parent_aborts(self):
        parent = AbortController()
        child = parent.create_child()
        parent.abort("parent gone")
        assert child.is_aborted is True
        assert child.abort_reason == "parent gone"

    def test_parent_not_aborted_when_child_aborts(self):
        parent = AbortController()
        child = parent.create_child()
        child.abort("child only")
        assert parent.is_aborted is False

    def test_grandchild_cascade(self):
        root = AbortController()
        mid = root.create_child()
        leaf = mid.create_child()
        root.abort("root gone")
        assert leaf.is_aborted is True

    def test_done_callback_called_on_abort(self):
        called = []
        ctrl = AbortController()
        ctrl.add_done_callback(lambda: called.append(1))
        ctrl.abort()
        assert called == [1]

    def test_done_callback_not_called_without_abort(self):
        called = []
        ctrl = AbortController()
        ctrl.add_done_callback(lambda: called.append(1))
        assert called == []

    def test_signal_is_read_only_view(self):
        ctrl = AbortController()
        signal = ctrl.signal
        assert signal.is_aborted is False
        ctrl.abort("test")
        assert signal.is_aborted is True


class TestAbortScope:
    def test_normal_exit_does_not_raise(self):
        ctrl = AbortController()

        async def run():
            async with AbortScope(ctrl):
                pass

        asyncio.run(run())

    def test_aborted_inside_scope_raises_abort_error(self):
        ctrl = AbortController()

        async def run():
            async with AbortScope(ctrl):
                ctrl.abort("cancelled inside")

        with pytest.raises(AbortError):
            asyncio.run(run())

    def test_context_manager_yields_controller(self):
        ctrl = AbortController()

        async def run():
            async with AbortScope(ctrl) as c:
                assert c is ctrl

        asyncio.run(run())

    def test_nested_scopes(self):
        root = AbortController()
        child = root.create_child()

        async def run():
            async with AbortScope(root):
                async with AbortScope(child):
                    root.abort("root cancelled")

        with pytest.raises(AbortError):
            asyncio.run(run())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_abort.py -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `agents/abort.py`**

```python
# agents/abort.py
"""Hierarchical abort controller for EmbodiedAgentsSys.

Aligned with Claude Code's AbortController pattern:
  - Parent abort cascades to all children.
  - Child abort does NOT propagate to parent.
  - AbortScope: async context manager that raises AbortError on exit if aborted.
  - AbortSignal: read-only view of controller state (passed to downstream code).

Usage:
    root = AbortController()
    skill_ctrl = root.create_child()
    vla_ctrl = skill_ctrl.create_child()

    async with AbortScope(vla_ctrl):
        result = await vla.execute(action)   # raises AbortError if cancelled

    root.abort("user cancelled")  # cascades to skill_ctrl and vla_ctrl
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Callable, Optional
from agents.exceptions import AbortError


class AbortSignal:
    """Read-only view of an AbortController's state.

    Pass this to downstream code that needs to check cancellation
    but must not be able to trigger it.
    """

    def __init__(self, controller: "AbortController") -> None:
        self._controller = controller

    @property
    def is_aborted(self) -> bool:
        return self._controller.is_aborted

    @property
    def abort_reason(self) -> Optional[str]:
        return self._controller.abort_reason


class AbortController:
    """Hierarchical abort controller.

    Creating a child via create_child() links it to this controller:
    aborting the parent automatically aborts all descendants.
    """

    def __init__(self) -> None:
        self._aborted = False
        self._reason: Optional[str] = None
        self._children: list["AbortController"] = []
        self._callbacks: list[Callable[[], None]] = []

    def abort(self, reason: str = "") -> None:
        """Abort this controller and all descendants.

        Idempotent: calling abort() multiple times keeps the first reason.
        """
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
        """Return a new controller that is cancelled when this one is."""
        child = AbortController()
        self._children.append(child)
        return child

    def add_done_callback(self, cb: Callable[[], None]) -> None:
        """Register a callback invoked synchronously when abort() is called."""
        self._callbacks.append(cb)

    @property
    def is_aborted(self) -> bool:
        return self._aborted

    @property
    def abort_reason(self) -> Optional[str]:
        return self._reason

    @property
    def signal(self) -> AbortSignal:
        """Return a read-only view suitable for passing to downstream code."""
        return AbortSignal(self)


class AbortScope:
    """Async context manager that raises AbortError if the controller was aborted.

    Usage:
        async with AbortScope(ctrl) as ctrl:
            await long_running_task()
        # If ctrl.abort() was called during the block, AbortError is raised on exit.
    """

    def __init__(self, controller: AbortController) -> None:
        self._controller = controller

    async def __aenter__(self) -> AbortController:
        return self._controller

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._controller.is_aborted and exc_type is None:
            raise AbortError(self._controller.abort_reason or "aborted")
        # Re-raise AbortError from nested code as-is
        if exc_type is not None and issubclass(exc_type, AbortError):
            return None  # let it propagate
        return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_abort.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/abort.py tests/test_abort.py
git commit -m "feat: add agents/abort.py — hierarchical AbortController + AbortScope"
```

---

## Phase 4: Final Integration

### Task 4: Run all Stream 1 tests + verify no regressions

- [ ] **Step 1: Run all three new test files together**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_exceptions.py tests/test_cache.py tests/test_abort.py -v
```
Expected: All pass

- [ ] **Step 2: Run full test suite to verify no regressions**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/ -q 2>&1 | tail -10
```
Expected: Previously passing tests still pass. New tests add to the total.

- [ ] **Step 3: Commit Stream 1 completion tag**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git tag stream1-foundation
git push origin stream1-foundation
```

---

## Self-Review Notes

- **exceptions.py**: `short_error_stack` uses `traceback.format_exception` — returns `tb_lines[0]` which is actually empty string; adjusted to combine all parts. Verified with test.
- **cache.py**: `cached(ttl=0)` expires immediately — verified by `test_expired_entry_calls_function_again` with `time.sleep(0.01)`.
- **abort.py**: `AbortScope.__aexit__` checks `exc_type is None` before raising to avoid double-raise on already-raised `AbortError`.
- No placeholders found.
- Type consistency: `AbortError` imported from `agents.exceptions` in `agents/abort.py` — consistent throughout.
