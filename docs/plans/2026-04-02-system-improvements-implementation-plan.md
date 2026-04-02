# System Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 7 improvement items for EmbodiedAgentsSys: error handling system, caching mechanism, plugin system, MCP protocol support, context compression, hierarchical abort, and testing improvements.

**Architecture:** Modular implementation with each subsystem as an independent module under `agents/`. Core dependencies: `agents/exceptions.py`, `agents/cache.py` → mid-level → `agents/plugins/`, `agents/mcp/`, `agents/context/`, `agents/abort.py` → testing improvements.

**Tech Stack:** Python asyncio, functools.lru_cache, pytest, @contextlib, typing.Protocol

---

## Overview: 7 Subsystems

| # | Subsystem | File | Priority | Dependencies |
|---|-----------|------|----------|---------------|
| 1 | Error Handling | `agents/exceptions.py` | ⭐⭐⭐ | None |
| 2 | Cache/Memoization | `agents/cache.py` | ⭐⭐⭐ | None |
| 3 | Plugin System | `agents/plugins/` | ⭐⭐ | exceptions, cache |
| 4 | MCP Protocol | `agents/mcp/` | ⭐⭐ | exceptions |
| 5 | Context Compression | `agents/context/` | ⭐⭐ | exceptions, cache |
| 6 | Hierarchical Abort | `agents/abort.py` | ⭐ | None |
| 7 | Testing Improvements | `tests/fixtures/` | ⭐⭐⭐ | All above |

---

## Phase 1: Foundation (Subsystems 1-2)

### Task 1: Create `agents/exceptions.py`

**Files:**
- Create: `agents/exceptions.py`
- Modify: `agents/__init__.py` (export exceptions)
- Test: `tests/test_exceptions.py`

**Step 1: Write the failing test**

```python
# tests/test_exceptions.py
import pytest
from agents.exceptions import (
    AgentError,
    AbortError,
    VLAActionError,
    HardwareError,
    TelemetrySafeError,
    is_abort_error,
    classify_error,
    short_error_stack,
)

class TestIsAbortError:
    def test_true_for_abort_error(self):
        assert is_abort_error(AbortError("cancelled"))

    def test_true_for_operationCancelledError(self):
        assert is_abort_error(OperationCancelledError())

    def test_false_for generic_error(self):
        assert not is_abort_error(ValueError("bad input"))

    def test_false_for_none(self):
        assert not is_abort_error(None)

class TestClassifyError:
    def test_vla_action_error(self):
        err = VLAActionError("VLA timeout")
        kind = classify_error(err)
        assert kind == ErrorKind.VLA_ACTION

    def test_hardware_error(self):
        err = HardwareError("Arm not responding")
        kind = classify_error(err)
        assert kind == ErrorKind.HARDWARE

class TestShortErrorStack:
    def test_returns_message_for_non_error(self):
        assert short_error_stack("not an error") == "not an error"

    def test_truncates_long_stacks(self):
        long_error = ValueError("test")
        long_error.__traceback__ = None  # Simplified for test
        result = short_error_stack(long_error, max_frames=2)
        assert "ValueError" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL - module 'agents.exceptions' has no attribute 'AgentError'

**Step 3: Write minimal implementation**

```python
# agents/exceptions.py
"""Error handling system for EmbodiedAgentsSys.

Inspired by Claude Code's error hierarchy (utils/errors.ts).
"""
from __future__ import annotations

import sys
import traceback
from enum import Enum, auto
from typing import Optional

# -------------------------------------------------------------------------------
# Error Classes
# -------------------------------------------------------------------------------

class AgentError(Exception):
    """Base exception class for all agent errors."""
    pass

class AbortError(AgentError):
    """Abort signal for cancellable operations."""
    def __init__(self, message: str = "", reason: Optional[str] = None):
        super().__init__(message)
        self.reason = reason

class VLAActionError(AgentError):
    """Raised when VLA action execution fails."""
    pass

class HardwareError(AgentError):
    """Raised when hardware communication fails."""
    pass

class TelemetrySafeError(AgentError):
    """Error safe for telemetry reporting (no sensitive data)."""
    def __init__(self, message: str, telemetry_message: Optional[str] = None):
        super().__init__(message)
        self.telemetry_message = telemetry_message or message

# -------------------------------------------------------------------------------
# ErrorKind Enum
# -------------------------------------------------------------------------------

class ErrorKind(Enum):
    """Classification of error types for handling strategies."""
    UNKNOWN = auto()
    ABORT = auto()
    VLA_ACTION = auto()
    HARDWARE = auto()
    NETWORK = auto()
    TIMEOUT = auto()
    VALIDATION = auto()
    TELEMETRY_SAFE = auto()

# -------------------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------------------

if sys.version_info >= (3, 11):
    _OperationCancelledError = asyncio.CancelledError
else:
    class _OperationCancelledError(CancelledError):
        """CancelledError for Python < 3.11 compatibility."""
        pass

def is_abort_error(e: Optional[object]) -> bool:
    """Check if e is any abort-shaped error."""
    if e is None:
        return False
    if isinstance(e, AbortError):
        return True
    if isinstance(e, _OperationCancelledError):
        return True
    if isinstance(e, KeyboardInterrupt):
        return True
    return False

def classify_error(e: Optional[object]) -> ErrorKind:
    """Classify error into ErrorKind for handling strategy."""
    if e is None:
        return ErrorKind.UNKNOWN
    if isinstance(e, AbortError):
        return ErrorKind.ABORT
    if isinstance(e, VLAActionError):
        return ErrorKind.VLA_ACTION
    if isinstance(e, HardwareError):
        return ErrorKind.HARDWARE
    if isinstance(e, TelemetrySafeError):
        return ErrorKind.TELEMETRY_SAFE
    if isinstance(e, TimeoutError):
        return ErrorKind.TIMEOUT
    if isinstance(e, (ConnectionError, OSError)) and "errno" in str(type(e)):
        return ErrorKind.NETWORK
    return ErrorKind.UNKNOWN

def short_error_stack(e: object, max_frames: int = 5) -> str:
    """Return error message plus top N stack frames.

    Full stacks waste context tokens; this truncates to max_frames.
    """
    if not isinstance(e, BaseException):
        return str(e)

    lines = traceback.format_exception(type(e), e, e.__traceback__)
    header = lines[0].strip() if lines else str(e)

    frames = [l for l in lines[1:] if l.strip().startswith("  ")]
    if len(frames) <= max_frames:
        return "".join(lines)

    return header + "\n" + "".join(frames[:max_frames])

def to_error(e: object) -> Exception:
    """Normalize any value to an Exception instance."""
    if isinstance(e, BaseException):
        return e
    return Exception(str(e))

def error_message(e: object) -> str:
    """Extract string message from any error-like value."""
    if isinstance(e, BaseException):
        return str(e)
    return str(e)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_exceptions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/exceptions.py tests/test_exceptions.py
git commit -m "feat(exceptions): add error handling system with error hierarchy"
```

---

### Task 2: Create `agents/cache.py`

**Files:**
- Create: `agents/cache.py`
- Modify: `agents/__init__.py` (export cache utilities)
- Test: `tests/test_cache.py`

**Step 1: Write the failing test**

```python
# tests/test_cache.py
import pytest
import asyncio
from agents.cache import (
    cached,
    SystemContextCache,
    get_robot_capabilities_cached,
)

class TestCachedDecorator:
    def test_caches_result(self):
        calls = 0

        @cached(ttl=60)
        def expensive(x):
            nonlocal calls
            calls += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert calls == 1  # Second call returns cached

    def test_different_args_miss_cache(self):
        @cached(ttl=60)
        def f(x):
            return x * 2

        assert f(1) == 2
        assert f(2) == 4
        assert f(1) == 2  # Cache miss for different arg

    def test_ttl_expires(self):
        import time

        @cached(ttl=1)
        def f():
            return "computed"

        assert f() == "computed"
        time.sleep(1.1)
        assert f() == "computed"  # Cache expired

class TestSystemContextCache:
    @pytest.fixture
    def cache(self):
        return SystemContextCache()

    def test_caches_git_status(self, cache):
        # First call
        status1 = cache.get_git_status()
        # Second call should be cached
        status2 = cache.get_git_status()
        assert status1 == status2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL - module 'agents.cache' has no attribute 'cached'

**Step 3: Write minimal implementation**

```python
# agents/cache.py
"""Caching and memoization utilities for EmbodiedAgentsSys.

Inspired by Claude Code's memoize pattern (utils/memoize.ts).
"""
from __future__ import annotations

import asyncio
import time
from functools import lru_cache, wraps
from typing import Any, Callable, Optional, TypeVar, Generic
from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

# -------------------------------------------------------------------------------
# Cached Decorator
# -------------------------------------------------------------------------------

def cached(ttl: float = 300, maxsize: int = 128):
    """Decorator that caches results with a TTL.

    Args:
        ttl: Time-to-live in seconds (default 5 minutes)
        maxsize: Maximum cache size (default 128)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        cache: dict[tuple, tuple[Any, float]] = {}
        _lru = lru_cache(maxsize=maxsize)(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl:
                    return result

            result = _lru(*args, **kwargs)
            cache[key] = (result, now)

            # Prune expired entries
            expired = [k for k, (_, t) in cache.items() if now - t >= ttl]
            for k in expired:
                del cache[k]

            return result

        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_info = lambda: {
            "size": len(cache),
            "maxsize": maxsize,
            "ttl": ttl,
        }
        return wrapper
    return decorator

# -------------------------------------------------------------------------------
# Async Cached Decorator
# -------------------------------------------------------------------------------

def async_cached(ttl: float = 300, maxsize: int = 128):
    """Async version of cached decorator."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        cache: dict[tuple, tuple[Any, float]] = {}

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl:
                    return result

            result = await func(*args, **kwargs)
            cache[key] = (result, now)

            expired = [k for k, (_, t) in cache.items() if now - t >= ttl]
            for k in expired:
                del cache[k]

            return result

        wrapper.cache_clear = lambda: cache.clear()
        return wrapper
    return decorator

# -------------------------------------------------------------------------------
# System Context Cache
# -------------------------------------------------------------------------------

class SystemContextCache:
    """Caches system context information for session duration.

    Similar to Claude Code's getSystemContext() memoization.
    """

    def __init__(self, ttl: float = 300):
        self._ttl = ttl
        self._git_status: Optional[tuple[str, float]] = None
        self._ros_topics: Optional[tuple[list[str], float]] = None
        self._env_vars: Optional[tuple[dict, float]] = None

    def get_git_status(self) -> str:
        """Get cached git status."""
        now = time.time()
        if self._git_status is None or now - self._git_status[1] >= self._ttl:
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "status", "--short"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self._git_status = (result.stdout, now)
            except Exception:
                self._git_status = ("", now)
        return self._git_status[0]

    def get_ros_topics(self) -> list[str]:
        """Get cached ROS2 topic list."""
        now = time.time()
        if self._ros_topics is None or now - self._ros_topics[1] >= self._ttl:
            topics = self._fetch_ros_topics()
            self._ros_topics = (topics, now)
        return self._ros_topics[0]

    def _fetch_ros_topics(self) -> list[str]:
        """Fetch ROS2 topics (mock for testing)."""
        # In real implementation, would call rclpy or use ros2cli
        return []

    def get_env_vars(self) -> dict:
        """Get cached environment variables."""
        now = time.time()
        if self._env_vars is None or now - self._env_vars[1] >= self._ttl:
            import os
            self._env_vars = (dict(os.environ), now)
        return self._env_vars[0]

    def invalidate(self) -> None:
        """Clear all caches."""
        self._git_status = None
        self._ros_topics = None
        self._env_vars = None

# -------------------------------------------------------------------------------
# Global Cache Instance
# -------------------------------------------------------------------------------

_global_cache = SystemContextCache()

def get_system_context_cache() -> SystemContextCache:
    """Get the global system context cache."""
    return _global_cache

# -------------------------------------------------------------------------------
# Capability Cache
# -------------------------------------------------------------------------------

@lru_cache(maxsize=32)
def get_robot_capabilities_cached(robot_type: str) -> dict:
    """Get robot capabilities with memoization.

    This is a module-level cached function as the capabilities
    don't change during a session.
    """
    from agents.hardware.capability_registry import RobotCapabilityRegistry
    return RobotCapabilityRegistry.get_capabilities(robot_type)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cache.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/cache.py tests/test_cache.py
git commit -m "feat(cache): add caching and memoization utilities"
```

---

## Phase 2: Mid-Level Subsystems (Subsystems 3-6)

### Task 3: Create `agents/plugins/` Plugin System

**Files:**
- Create: `agents/plugins/__init__.py`
- Create: `agents/plugins/base.py`
- Create: `agents/plugins/registry.py`
- Create: `agents/plugins/builtin/`
- Modify: `agents/__init__.py`
- Test: `tests/test_plugins.py`

**Step 1: Write the failing test**

```python
# tests/test_plugins.py
import pytest
from agents.plugins.base import Plugin, PluginMetadata, Tool, Skill
from agents.plugins.registry import PluginRegistry

class TestPluginBase:
    def test_plugin_metadata(self):
        meta = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="A test plugin",
        )
        assert meta.name == "test_plugin"
        assert meta.version == "1.0.0"

    def test_plugin_virtual_methods(self):
        """Plugins must implement initialize and shutdown."""
        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "1.0.0"

            async def _initialize(self) -> None:
                self.initialized = True

            async def _shutdown(self) -> None:
                self.shutdown = True

        plugin = MyPlugin()
        assert plugin.name == "my_plugin"

class TestPluginRegistry:
    def test_register_and_get(self):
        registry = PluginRegistry()

        class TestPlugin(Plugin):
            name = "test"
            version = "1.0.0"
            async def _initialize(self) -> None: pass
            async def _shutdown(self) -> None: pass

        registry.register(TestPlugin())
        retrieved = registry.get("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_unregister(self):
        registry = PluginRegistry()

        class TestPlugin(Plugin):
            name = "test2"
            version = "1.0.0"
            async def _initialize(self) -> None: pass
            async def _shutdown(self) -> None: pass

        registry.register(TestPlugin())
        registry.unregister("test2")
        assert registry.get("test2") is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_plugins.py -v`
Expected: FAIL - module 'agents.plugins' has no attribute 'Plugin'

**Step 3: Write minimal implementation**

```python
# agents/plugins/__init__.py
"""Plugin system for EmbodiedAgentsSys.

Provides a pluggable architecture for extending agent capabilities.
"""
from agents.plugins.base import (
    Plugin,
    PluginMetadata,
    Tool,
    Skill,
    Hook,
    HookType,
)
from agents.plugins.registry import PluginRegistry

__all__ = [
    "Plugin",
    "PluginMetadata",
    "Tool",
    "Skill",
    "Hook",
    "HookType",
    "PluginRegistry",
]
```

```python
# agents/plugins/base.py
"""Plugin base classes and interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

# -------------------------------------------------------------------------------
# Metadata
# -------------------------------------------------------------------------------

@dataclass(frozen=True)
class PluginMetadata:
    """Plugin metadata for registration and discovery."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: tuple[str, ...] = field(default_factory=tuple)

# -------------------------------------------------------------------------------
# Tool Interface
# -------------------------------------------------------------------------------

@dataclass
class Tool:
    """A tool provided by a plugin."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    execute: Optional[Any] = None  # Callable - set by plugin

# -------------------------------------------------------------------------------
# Skill Interface (extends VLASkill concept)
# -------------------------------------------------------------------------------

@dataclass
class Skill:
    """A skill provided by a plugin."""
    name: str
    description: str
    preconditions: list[str] = field(default_factory=list)
    termination: list[str] = field(default_factory=list)

# -------------------------------------------------------------------------------
# Hook System
# -------------------------------------------------------------------------------

class HookType(Enum):
    """Types of hooks plugins can register."""
    PRE_ACTION = auto()
    POST_ACTION = auto()
    ON_ERROR = auto()
    ON_ABORT = auto()
    PRE_OBSERVATION = auto()
    POST_OBSERVATION = auto()

@dataclass
class Hook:
    """A hook callback registered by a plugin."""
    hook_type: HookType
    callback: Any  # AsyncCallable

# -------------------------------------------------------------------------------
# Plugin Base Class
# -------------------------------------------------------------------------------

class Plugin(ABC):
    """Base class for all plugins.

    Plugins provide tools, skills, and hooks to extend agent capabilities.
    They are loaded at startup and can be enabled/disabled dynamically.
    """

    # Subclasses must set these
    name: str = ""
    version: str = "1.0.0"

    def __init__(self):
        self._initialized = False
        self._tools: list[Tool] = []
        self._skills: list[Skill] = []
        self._hooks: list[Hook] = []

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize plugin resources.

        Called once when plugin is loaded. Override to set up
        connections, load models, etc.
        """
        pass

    @abstractmethod
    async def _shutdown(self) -> None:
        """Clean up plugin resources.

        Called once when plugin is unloaded. Override to close
        connections, save state, etc.
        """
        pass

    async def initialize(self) -> None:
        """Public initialize - calls subclass _initialize."""
        if self._initialized:
            return
        await self._initialize()
        self._initialized = True

    async def shutdown(self) -> None:
        """Public shutdown - calls subclass _shutdown."""
        if not self._initialized:
            return
        await self._shutdown()
        self._initialized = False

    def get_tools(self) -> list[Tool]:
        """Get tools provided by this plugin."""
        return self._tools.copy()

    def get_skills(self) -> list[Skill]:
        """Get skills provided by this plugin."""
        return self._skills.copy()

    def get_hooks(self) -> list[Hook]:
        """Get hooks provided by this plugin."""
        return self._hooks.copy()

    def add_tool(self, tool: Tool) -> None:
        """Add a tool to this plugin."""
        self._tools.append(tool)

    def add_skill(self, skill: Skill) -> None:
        """Add a skill to this plugin."""
        self._skills.append(skill)

    def add_hook(self, hook: Hook) -> None:
        """Add a hook to this plugin."""
        self._hooks.append(hook)

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name=self.name,
            version=self.version,
        )
```

```python
# agents/plugins/registry.py
"""Plugin registry for managing loaded plugins."""
from __future__ import annotations

import logging
from typing import dict[str, Plugin], Optional

from agents.plugins.base import Plugin

logger = logging.getLogger(__name__)

class PluginRegistry:
    """Central registry for all loaded plugins.

    Singleton pattern - use PluginRegistry.get_instance().
    """

    _instance: Optional[PluginRegistry] = None

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._enabled: dict[str, bool] = {}

    @classmethod
    def get_instance(cls) -> PluginRegistry:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = PluginRegistry()
        return cls._instance

    def register(self, plugin: Plugin) -> None:
        """Register a plugin."""
        if plugin.name in self._plugins:
            logger.warning(f"Plugin {plugin.name} already registered, replacing")
        self._plugins[plugin.name] = plugin
        self._enabled[plugin.name] = True
        logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name in self._plugins:
            plugin = self._plugins[name]
            if self._enabled.get(name, False):
                # Disable before unregistering
                import asyncio
                asyncio.create_task(self.disable(name))
            del self._plugins[name]
            del self._enabled[name]
            logger.info(f"Unregistered plugin: {name}")

    def get(self, name: str) -> Optional[Plugin]:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def get_all(self) -> list[Plugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())

    def get_enabled(self) -> list[Plugin]:
        """Get all enabled plugins."""
        return [p for p in self._plugins.values() if self._enabled.get(p.name, False)]

    async def enable(self, name: str) -> bool:
        """Enable a plugin."""
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.error(f"Cannot enable unknown plugin: {name}")
            return False
        if self._enabled.get(name, False):
            logger.debug(f"Plugin {name} already enabled")
            return True

        try:
            await plugin.initialize()
            self._enabled[name] = True
            logger.info(f"Enabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}")
            return False

    async def disable(self, name: str) -> bool:
        """Disable a plugin."""
        plugin = self._plugins.get(name)
        if plugin is None:
            return False
        if not self._enabled.get(name, False):
            return True

        try:
            await plugin.shutdown()
            self._enabled[name] = False
            logger.info(f"Disabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}")
            return False

    def is_enabled(self, name: str) -> bool:
        """Check if plugin is enabled."""
        return self._enabled.get(name, False)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_plugins.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/plugins/ tests/test_plugins.py
git commit -m "feat(plugins): add plugin system architecture"
```

---

### Task 4: Create `agents/mcp/` MCP Protocol Support

**Files:**
- Create: `agents/mcp/__init__.py`
- Create: `agents/mcp/client.py`
- Create: `agents/mcp/protocol.py`
- Create: `agents/mcp/tools.py`
- Modify: `agents/__init__.py`
- Test: `tests/test_mcp.py`

**Step 1: Write the failing test**

```python
# tests/test_mcp.py
import pytest
from agents.mcp.protocol import MCPConfig, MCPTool, MCPResource
from agents.mcp.client import MCPClient

class TestMCPConfig:
    def test_config_creation(self):
        config = MCPConfig(
            name="test_server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        )
        assert config.name == "test_server"
        assert config.command == "npx"

class TestMCPClient:
    @pytest.fixture
    def client(self):
        return MCPClient()

    def test_client_initial_state(self, client):
        assert not client.is_connected

    def test_server_config_storage(self, client):
        config = MCPConfig(
            name="test",
            command="echo",
            args=["test"],
        )
        client.add_server("test", config)
        assert client.get_server_config("test") == config
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp.py -v`
Expected: FAIL - module 'agents.mcp' has no attribute 'client'

**Step 3: Write minimal implementation**

```python
# agents/mcp/__init__.py
"""MCP (Model Context Protocol) client for EmbodiedAgentsSys.

Provides integration with MCP servers for extended tool capabilities.
"""
from agents.mcp.protocol import (
    MCPConfig,
    MCPTool,
    MCPResource,
    MCPResourceTemplate,
    ToolResult,
    ResourceContent,
)
from agents.mcp.client import MCPClient, MCPServerManager

__all__ = [
    "MCPConfig",
    "MCPTool",
    "MCPResource",
    "MCPResourceTemplate",
    "ToolResult",
    "ResourceContent",
    "MCPClient",
    "MCPServerManager",
]
```

```python
# agents/mcp/protocol.py
"""MCP protocol types and schemas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# -------------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------------

@dataclass
class MCPConfig:
    """Configuration for an MCP server connection."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    auto_reconnect: bool = True

# -------------------------------------------------------------------------------
# Tool Types
# -------------------------------------------------------------------------------

@dataclass
class MCPTool:
    """An MCP tool definition."""
    name: str
    description: str
    inputSchema: dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolResult:
    """Result from calling an MCP tool."""
    content: list[ResourceContent]
    isError: bool = False

# -------------------------------------------------------------------------------
# Resource Types
# -------------------------------------------------------------------------------

@dataclass
class ResourceContent:
    """Content from an MCP resource."""
    type: str  # "text" or "image"
    mimeType: str = "text/plain"
    text: Optional[str] = None
    data: Optional[str] = None  # base64 for images

@dataclass
class MCPResource:
    """An MCP resource definition."""
    uri: str
    name: str
    description: str = ""
    mimeType: str = "text/plain"

@dataclass
class MCPResourceTemplate:
    """An MCP resource template for dynamic resources."""
    uriTemplate: str
    name: str
    description: str = ""
    mimeType: str = "text/plain"
```

```python
# agents/mcp/client.py
"""MCP client implementation."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from agents.mcp.protocol import (
    MCPConfig,
    MCPTool,
    MCPResource,
    ToolResult,
    ResourceContent,
)

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for connecting to an MCP server.

    Implements JSON-RPC communication over stdio.
    """

    def __init__(self):
        self._config: Optional[MCPConfig] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._connected: bool = False
        self._request_id: int = 0
        self._pending: dict[int, asyncio.Future] = {}

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self._connected

    async def connect(self, config: MCPConfig) -> None:
        """Connect to an MCP server.

        Args:
            config: Server configuration

        Raises:
            ConnectionError: If connection fails
        """
        if self._connected:
            logger.warning("Already connected, disconnecting first")
            await self.disconnect()

        self._config = config

        try:
            self._process = await asyncio.create_subprocess_exec(
                config.command,
                *config.args,
                env={**config.env} if config.env else None,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._writer = self._process.stdin
            self._reader = self._process.stdout
            self._connected = True
            logger.info(f"Connected to MCP server: {config.name}")

            # Initialize connection
            await self._send_request("initialize", {})

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._connected = False
            raise ConnectionError(f"MCP connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        self._connected = False

        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None

        self._writer = None
        self._reader = None
        self._pending.clear()
        logger.info("Disconnected from MCP server")

    async def list_tools(self) -> list[MCPTool]:
        """List available tools from server."""
        if not self._connected:
            return []

        try:
            result = await self._send_request("tools/list", {})
            tools = result.get("tools", [])
            return [MCPTool(**t) for t in tools]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call a tool on the server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            ToolResult with content
        """
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        try:
            result = await self._send_request("tools/call", {
                "name": name,
                "arguments": arguments,
            })

            content = [
                ResourceContent(
                    type=c.get("type", "text"),
                    mimeType=c.get("mimeType", "text/plain"),
                    text=c.get("text"),
                    data=c.get("data"),
                )
                for c in result.get("content", [])
            ]

            return ToolResult(
                content=content,
                isError=result.get("isError", False),
            )

        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return ToolResult(
                content=[ResourceContent(type="text", text=str(e))],
                isError=True,
            )

    async def list_resources(self) -> list[MCPResource]:
        """List available resources from server."""
        if not self._connected:
            return []

        try:
            result = await self._send_request("resources/list", {})
            resources = result.get("resources", [])
            return [MCPResource(**r) for r in resources]
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return []

    async def read_resource(self, uri: str) -> list[ResourceContent]:
        """Read a resource by URI."""
        if not self._connected:
            raise ConnectionError("Not connected to MCP server")

        try:
            result = await self._send_request("resources/read", {"uri": uri})
            content = [
                ResourceContent(
                    type=c.get("type", "text"),
                    mimeType=c.get("mimeType", "text/plain"),
                    text=c.get("text"),
                    data=c.get("data"),
                )
                for c in result.get("contents", [])
            ]
            return content
        except Exception as e:
            logger.error(f"Failed to read resource: {e}")
            return [ResourceContent(type="text", text=str(e))]

    async def _send_request(self, method: str, params: dict) -> dict:
        """Send JSON-RPC request and wait for response."""
        if not self._writer or not self._reader:
            raise ConnectionError("Not connected")

        self._request_id += 1
        req_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }

        future = asyncio.Future()
        self._pending[req_id] = future

        try:
            self._writer.write(json.dumps(request).encode())
            await self._writer.drain()
            return await asyncio.wait_for(future, timeout=self._config.timeout)
        finally:
            self._pending.pop(req_id, None)

    async def _read_responses(self) -> None:
        """Background task to read responses from server."""
        if not self._reader:
            return

        while self._connected:
            try:
                line = await asyncio.wait_for(
                    self._reader.readline(),
                    timeout=1.0,
                )
                if not line:
                    break

                response = json.loads(line.decode())
                if "id" in response and response["id"] in self._pending:
                    future = self._pending.pop(response["id"])
                    if "result" in response:
                        future.set_result(response["result"])
                    elif "error" in response:
                        future.set_exception(Exception(response["error"]))

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error reading MCP response: {e}")
                break


class MCPServerManager:
    """Manages multiple MCP server connections."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    def add_server(self, name: str, config: MCPConfig) -> MCPClient:
        """Add and return an MCP client for the server."""
        client = MCPClient()
        self._clients[name] = client
        return client

    def remove_server(self, name: str) -> None:
        """Remove a server connection."""
        if name in self._clients:
            client = self._clients[name]
            if client.is_connected:
                asyncio.create_task(client.disconnect())
            del self._clients[name]

    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get client by server name."""
        return self._clients.get(name)

    def get_all_tools(self) -> list[tuple[str, MCPTool]]:
        """Get all tools from all servers.

        Returns:
            List of (server_name, tool) tuples
        """
        tools = []
        for name, client in self._clients.items():
            if client.is_connected:
                for tool in client.list_tools():
                    tools.append((name, tool))
        return tools
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/mcp/ tests/test_mcp.py
git commit -m "feat(mcp): add MCP protocol client implementation"
```

---

### Task 5: Create `agents/context/` Context Compression

**Files:**
- Create: `agents/context/__init__.py`
- Create: `agents/context/budget.py`
- Create: `agents/context/compressor.py`
- Create: `agents/context/manager.py`
- Modify: `agents/__init__.py`
- Test: `tests/test_context.py`

**Step 1: Write the failing test**

```python
# tests/test_context.py
import pytest
from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import MicroCompressor

class TestContextBudget:
    def test_default_limits(self):
        budget = ContextBudget()
        assert budget.MAX_TOKENS == 100_000
        assert budget.WARNING_THRESHOLD == 0.8

    def test_check_within_budget(self):
        budget = ContextBudget()
        # Mock messages with known size
        messages = [{"role": "user", "content": "hi"}]
        status = budget.check_budget(messages)
        assert status.within_limits

    def test_check_warning_threshold(self):
        budget = ContextBudget(max_tokens=100)
        messages = [{"role": "user", "content": "x" * 80}]
        status = budget.check_budget(messages)
        assert status.should_warn

class TestMicroCompressor:
    def test_compress_message(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "Hello world"}
        compressed = compressor.compress_message(msg)
        assert compressed["content"] in ["Hello world", "[compressed]"]

    def test_strip_images(self):
        compressor = MicroCompressor()
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Look at this"},
                {"type": "image", "data": "base64..."},
            ]
        }
        stripped = compressor.strip_images(msg)
        assert len(stripped["content"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py -v`
Expected: FAIL - module 'agents.context' has no attribute 'budget'

**Step 3: Write minimal implementation**

```python
# agents/context/__init__.py
"""Context management with Token budget and compression."""
from agents.context.budget import (
    ContextBudget,
    BudgetStatus,
)
from agents.context.compressor import (
    MicroCompressor,
    CompressionResult,
)
from agents.context.manager import (
    ContextManager,
    MessageHistory,
)

__all__ = [
    "ContextBudget",
    "BudgetStatus",
    "MicroCompressor",
    "CompressionResult",
    "ContextManager",
    "MessageHistory",
]
```

```python
# agents/context/budget.py
"""Context token budget management."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# -------------------------------------------------------------------------------
# Budget Status
# -------------------------------------------------------------------------------

@dataclass
class BudgetStatus:
    """Status of context budget check."""
    current_tokens: int
    max_tokens: int
    within_limits: bool
    should_warn: bool
    should_compress: bool
    usage_ratio: float

# -------------------------------------------------------------------------------
# Context Budget
# -------------------------------------------------------------------------------

class ContextBudget:
    """Manages context token budget and compression triggers.

    Inspired by Claude Code's tokenBudget.ts.
    """

    MAX_TOKENS: int = 100_000
    WARNING_THRESHOLD: float = 0.8
    CRITICAL_THRESHOLD: float = 0.95
    COMPRESS_THRESHOLD: float = 0.9

    def __init__(self, max_tokens: int = MAX_TOKENS):
        self.max_tokens = max_tokens

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count for messages.

        Rough estimate: ~4 chars per token for English.
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total += len(item.get("text", "")) // 4
                    elif isinstance(item, dict) and item.get("type") == "image":
                        total += 1000  # Image tokens estimate
            elif isinstance(content, str):
                total += len(content) // 4
        return total

    def check_budget(self, messages: list[dict[str, Any]]) -> BudgetStatus:
        """Check if messages are within budget."""
        current = self.estimate_tokens(messages)
        ratio = current / self.max_tokens

        return BudgetStatus(
            current_tokens=current,
            max_tokens=self.max_tokens,
            within_limits=ratio <= 1.0,
            should_warn=ratio >= self.WARNING_THRESHOLD,
            should_compress=ratio >= self.COMPRESS_THRESHOLD,
            usage_ratio=ratio,
        )

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """Check if compression should be triggered."""
        status = self.check_budget(messages)
        return status.should_compress
```

```python
# agents/context/compressor.py
"""Message compression utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# -------------------------------------------------------------------------------
# Compression Result
# -------------------------------------------------------------------------------

@dataclass
class CompressionResult:
    """Result of a compression operation."""
    original_count: int
    compressed_count: int
    original_tokens: int
    compressed_tokens: int
    savings_ratio: float

# -------------------------------------------------------------------------------
# Micro Compressor
# -------------------------------------------------------------------------------

class MicroCompressor:
    """Compresses individual messages to reduce token usage.

    Inspired by Claude Code's microCompact.ts.
    """

    MAX_TEXT_LENGTH: int = 2000

    def compress_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Compress a single message.

        - Strips images (replaced with placeholder)
        - Truncates long text
        - Removes redundant whitespace
        """
        compressed = message.copy()

        content = compressed.get("content", "")
        if isinstance(content, list):
            compressed["content"] = [
                self._compress_content_item(item)
                for item in content
            ]
        elif isinstance(content, str):
            compressed["content"] = self._compress_text(content)

        return compressed

    def _compress_content_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Compress a single content item."""
        if not isinstance(item, dict):
            return item

        item_type = item.get("type", "text")

        if item_type == "image":
            # Replace image with placeholder
            return {
                "type": "text",
                "text": "[Image: image content stripped for compression]",
            }

        if item_type == "text":
            return {
                "type": "text",
                "text": self._compress_text(item.get("text", "")),
            }

        return item

    def _compress_text(self, text: str) -> str:
        """Compress text to max length."""
        if not text:
            return text

        # Remove redundant whitespace
        text = " ".join(text.split())

        # Truncate if too long
        if len(text) > self.MAX_TEXT_LENGTH:
            text = text[:self.MAX_TEXT_LENGTH] + "..."

        return text

    def strip_images(self, message: dict[str, Any]) -> dict[str, Any]:
        """Strip all images from a message."""
        compressed = message.copy()
        content = compressed.get("content", "")

        if isinstance(content, list):
            compressed["content"] = [
                item for item in content
                if not (isinstance(item, dict) and item.get("type") == "image")
            ]

            # If list becomes empty, add placeholder
            if not compressed["content"]:
                compressed["content"] = [{"type": "text", "text": "[Images removed]"}]

        return compressed

    def truncate_long_content(
        self,
        message: dict[str, Any],
        max_chars: int,
    ) -> dict[str, Any]:
        """Truncate message content to max characters."""
        compressed = message.copy()
        content = compressed.get("content", "")

        if isinstance(content, str) and len(content) > max_chars:
            compressed["content"] = content[:max_chars] + "..."

        return compressed
```

```python
# agents/context/manager.py
"""Context manager for handling message history and compression."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import MicroCompressor, CompressionResult

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Message History
# -------------------------------------------------------------------------------

class MessageHistory:
    """Manages message history with archiving capabilities.

    Provides audit trail and summarization for old messages.
    """

    def __init__(self):
        self._messages: list[dict[str, Any]] = []
        self._archived: list[dict[str, Any]] = []

    def add(self, message: dict[str, Any]) -> None:
        """Add a message to history."""
        self._messages.append(message)

    def get_all(self) -> list[dict[str, Any]]:
        """Get all messages."""
        return self._messages.copy()

    def archive_old_messages(self, before_index: int) -> None:
        """Archive messages before index."""
        if before_index >= len(self._messages):
            return

        archived = self._messages[:before_index]
        self._archived.extend(archived)
        self._messages = self._messages[before_index:]
        logger.info(f"Archived {len(archived)} messages")

    async def summarize_and_replace(
        self,
        start: int,
        end: int,
        summarizer: Any,  # LLM provider
    ) -> dict[str, Any]:
        """Summarize a range of messages and replace with summary.

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)
            summarizer: LLM provider for summarization

        Returns:
            Summary message
        """
        if start >= end or end > len(self._messages):
            raise ValueError(f"Invalid range [{start}, {end})")

        to_summarize = self._messages[start:end]

        # Generate summary via LLM
        summary_text = await summarizer.summarize(to_summarize)

        summary_msg = {
            "role": "system",
            "content": f"[Summary of {end - start} messages]: {summary_text}",
        }

        # Replace range with summary
        self._messages = (
            self._messages[:start] +
            [summary_msg] +
            self._messages[end:]
        )

        return summary_msg

# -------------------------------------------------------------------------------
# Context Manager
# -------------------------------------------------------------------------------

class ContextManager:
    """Manages context with automatic compression.

    Coordinates budget tracking, compression, and message history.
    """

    def __init__(
        self,
        budget: Optional[ContextBudget] = None,
        compressor: Optional[MicroCompressor] = None,
    ):
        self.budget = budget or ContextBudget()
        self.compressor = compressor or MicroCompressor()
        self.history = MessageHistory()

    def get_status(self) -> BudgetStatus:
        """Get current budget status."""
        return self.budget.check_budget(self.history.get_all())

    async def compact_if_needed(self) -> Optional[CompressionResult]:
        """Compress messages if budget requires it.

        Returns CompressionResult if compression happened, None otherwise.
        """
        messages = self.history.get_all()
        if not self.budget.should_compress(messages):
            return None

        original_count = len(messages)
        original_tokens = self.budget.estimate_tokens(messages)

        # Archive oldest 50% of messages
        archive_idx = original_count // 2
        self.history.archive_old_messages(archive_idx)

        compressed_count = len(self.history.get_all())
        compressed_tokens = self.budget.estimate_tokens(self.history.get_all())

        return CompressionResult(
            original_count=original_count,
            compressed_count=compressed_count,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            savings_ratio=1 - (compressed_tokens / original_tokens),
        )

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message and check compression."""
        self.history.add(message)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/context/ tests/test_context.py
git commit -m "feat(context): add context budget and compression system"
```

---

### Task 6: Create `agents/abort.py` Hierarchical Abort

**Files:**
- Create: `agents/abort.py`
- Modify: `agents/__init__.py`
- Test: `tests/test_abort.py`

**Step 1: Write the failing test**

```python
# tests/test_abort.py
import pytest
import asyncio
from agents.abort import AbortController, AbortScope, AbortError

class TestAbortController:
    def test_initial_state(self):
        controller = AbortController()
        assert not controller.is_aborted
        assert controller.abort_reason is None

    def test_abort_sets_flag(self):
        controller = AbortController()
        controller.abort("test reason")
        assert controller.is_aborted
        assert controller.abort_reason == "test reason"

    def test_create_child(self):
        parent = AbortController()
        child = parent.create_child()
        assert child.parent is parent

    def test_child_abort_propagates_to_parent(self):
        parent = AbortController()
        child = parent.create_child()
        child.abort("child reason")
        assert child.is_aborted
        assert parent.is_aborted  # Parent should also be aborted

    def test_parent_abort_propagates_to_children(self):
        parent = AbortController()
        child = parent.create_child()
        parent.abort("parent reason")
        assert parent.is_aborted
        assert child.is_aborted  # Child should also be aborted

class TestAbortScope:
    @pytest.mark.asyncio
    async def test_scope_enters_and_exits(self):
        controller = AbortController()
        async with AbortScope(controller):
            assert not controller.is_aborted
        # Scope exits cleanly

    @pytest.mark.asyncio
    async def test_abort_in_scope(self):
        controller = AbortController()
        async with AbortScope(controller):
            controller.abort("test")
        assert controller.is_aborted
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_abort.py -v`
Expected: FAIL - module 'agents.abort' has no attribute 'AbortController'

**Step 3: Write minimal implementation**

```python
# agents/abort.py
"""Hierarchical abort controller system.

Inspired by Claude Code's abort signal tree pattern.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Any

from agents.exceptions import AbortError as AgentAbortError

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Abort Controller
# -------------------------------------------------------------------------------

class AbortController:
    """Hierarchical abort controller with parent-child relationships.

    Supports cascading abort: aborting a parent aborts all children,
    and aborting any child aborts the parent (for error propagation).
    """

    def __init__(
        self,
        parent: Optional[AbortController] = None,
        reason: str = "",
    ):
        self._parent = parent
        self._reason: Optional[str] = reason
        self._is_aborted = False
        self._children: list[AbortController] = []
        self._done_callbacks: list[Callable] = []

        if parent is not None:
            parent._children.append(self)

    @property
    def parent(self) -> Optional[AbortController]:
        """Parent controller."""
        return self._parent

    @property
    def is_aborted(self) -> bool:
        """Check if this controller or any ancestor is aborted."""
        if self._is_aborted:
            return True
        if self._parent is not None:
            return self._parent.is_aborted
        return False

    @property
    def abort_reason(self) -> Optional[str]:
        """Get the reason for abort, from self or nearest ancestor."""
        if self._reason is not None:
            return self._reason
        if self._parent is not None:
            return self._parent.abort_reason
        return None

    @property
    def depth(self) -> int:
        """Get depth in abort tree."""
        depth = 0
        current = self._parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    def abort(self, reason: str = "", exc: Optional[BaseException] = None) -> None:
        """Abort this controller and propagate to parent.

        Args:
            reason: Human-readable reason for abort
            exc: Exception to raise (default: AbortError)
        """
        if self._is_aborted:
            return  # Already aborted

        self._reason = reason
        self._is_aborted = True

        # Propagate to parent (for error escalation)
        if self._parent is not None and not self._parent._is_aborted:
            self._parent.abort(reason, exc)

        # Notify callbacks
        for cb in self._done_callbacks:
            try:
                cb(reason)
            except Exception as e:
                logger.warning(f"Abort callback error: {e}")

        logger.debug(f"AbortController aborted: {reason} (depth={self.depth})")

    def create_child(self) -> AbortController:
        """Create a child controller.

        Child inherits parent reference; aborting child propagates to parent.
        """
        return AbortController(parent=self)

    def add_done_callback(self, cb: Callable[[str], None]) -> None:
        """Add a callback called when aborted."""
        self._done_callbacks.append(cb)

    def check_abort(self) -> None:
        """Check if aborted and raise AbortError if so.

        Call this in async operations to check for abort.
        """
        if self.is_aborted:
            raise AgentAbortError(
                message=self.abort_reason or "Operation aborted",
                reason=self.abort_reason,
            )

    def __repr__(self) -> str:
        status = "ABORTED" if self._is_aborted else "active"
        return f"AbortController({status}, reason={self._reason!r}, depth={self.depth})"

# -------------------------------------------------------------------------------
# Abort Scope
# -------------------------------------------------------------------------------

class AbortScope:
    """Context manager for AbortController with automatic checking.

    Use with `async with AbortScope(controller)` to automatically
    check for abort on each await.
    """

    def __init__(self, controller: AbortController):
        self._controller = controller

    async def __aenter__(self) -> AbortController:
        return self._controller

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # Check if we should abort on exception
        if exc_type is not None and exc_val is not None:
            if not isinstance(exc_val, (asyncio.CancelledError, AgentAbortError)):
                # Propagate exception as abort
                self._controller.abort(str(exc_val), exc_val)
        return None

# -------------------------------------------------------------------------------
# Convenience Functions
# -------------------------------------------------------------------------------

async def run_with_abort(
    controller: AbortController,
    coro: Any,
) -> Any:
    """Run a coroutine with abort checking.

    Args:
        controller: AbortController to use
        coro: Coroutine to run

    Returns:
        Result of coroutine

    Raises:
        AbortError: If controller is aborted
    """
    async with AbortScope(controller):
        return await coro

def create_root_controller() -> AbortController:
    """Create a root (top-level) abort controller."""
    return AbortController()

def create_linked_controllers(
    count: int,
) -> tuple[AbortController, ...]:
    """Create a chain of linked controllers.

    Returns tuple of (root, child1, child2, ..., childN).
    """
    controllers = [AbortController()]
    for _ in range(count):
        controllers.append(controllers[-1].create_child())
    return tuple(controllers)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_abort.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/abort.py tests/test_abort.py
git commit -m "feat(abort): add hierarchical abort controller system"
```

---

## Phase 3: Testing Improvements (Subsystem 7)

### Task 7: Improve Test Infrastructure

**Files:**
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/mock_vla.py`
- Create: `tests/fixtures/mock_arm.py`
- Create: `tests/fixtures/mock_llm.py`
- Create: `tests/fixtures/mock_events.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_fixtures.py`

**Step 1: Write the failing test**

```python
# tests/test_fixtures.py
import pytest
from tests.fixtures.mock_vla import MockVLAAdapterFactory
from tests.fixtures.mock_arm import MockArmAdapterFactory
from tests.fixtures.mock_llm import MockLLMProvider

class TestMockVLAAdapterFactory:
    def test_creates_adapter(self):
        factory = MockVLAAdapterFactory()
        adapter = factory.create()
        assert adapter is not None
        assert hasattr(adapter, 'act')
        assert hasattr(adapter, 'execute')

    def test_adapter_config(self):
        factory = MockVLAAdapterFactory()
        adapter = factory.create(action_dim=14)
        assert adapter.action_dim == 14

    @pytest.mark.asyncio
    async def test_adapter_act(self):
        factory = MockVLAAdapterFactory()
        adapter = factory.create()
        observation = {"image": "test"}
        result = await adapter.act(observation, "grasp")
        assert result is not None

class TestMockLLMProvider:
    def test_creates_provider(self):
        provider = MockLLMProvider()
        assert provider is not None

    @pytest.mark.asyncio
    async def test_generate(self):
        provider = MockLLMProvider()
        result = await provider.generate([{"role": "user", "content": "hi"}])
        assert result is not None
        assert "content" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_fixtures.py -v`
Expected: FAIL - module 'tests.fixtures' has no attribute 'mock_vla'

**Step 3: Write minimal implementation**

```python
# tests/fixtures/__init__.py
"""Test fixtures for EmbodiedAgentsSys."""
from tests.fixtures.mock_vla import MockVLAAdapterFactory, MockVLAAdapter
from tests.fixtures.mock_arm import MockArmAdapterFactory, MockArmAdapter
from tests.fixtures.mock_llm import MockLLMProvider, MockLLMConfig
from tests.fixtures.mock_events import MockEventBusFactory, MockMessageBus

__all__ = [
    "MockVLAAdapterFactory",
    "MockVLAAdapter",
    "MockArmAdapterFactory",
    "MockArmAdapter",
    "MockLLMProvider",
    "MockLLMConfig",
    "MockEventBusFactory",
    "MockMessageBus",
]
```

```python
# tests/fixtures/mock_vla.py
"""Mock VLA adapters for testing."""
from __future__ import annotations

import asyncio
from typing import Any, Optional
from dataclasses import dataclass

# Try to import base class, provide fallback
try:
    from agents.clients.vla_adapters.base import VLAAdapterBase
    from agents.components.data_structures import Observation, Action
except ImportError:
    # Fallback for testing without full imports
    VLAAdapterBase = object
    Observation = dict
    Action = dict

@dataclass
class MockVLAAdapterConfig:
    """Configuration for MockVLAAdapter."""
    action_dim: int = 7
    observation_types: list[str] = None
    action_history_size: int = 100

class MockVLAAdapter(VLAAdapterBase if VLAAdapterBase != object else object):
    """Mock VLA adapter for testing.

    Simulates VLA behavior without requiring actual model.
    """

    def __init__(self, **config):
        self._config = MockVLAAdapterConfig(**config)
        self.action_history = []
        self.reset_called = False
        self.act_called_count = 0
        self.execute_called_count = 0

    @property
    def action_dim(self) -> int:
        return self._config.action_dim

    async def reset(self) -> None:
        """Reset the VLA adapter state."""
        self.reset_called = True
        self.action_history.clear()

    async def act(
        self,
        observation: Observation,
        skill_token: str = "",
    ) -> Action:
        """Generate an action from observation."""
        self.act_called_count += 1

        # Generate mock action
        action = Action(
            position=[0.0, 0.0, 0.0],
            rotation=[0.0, 0.0, 0.0, 1.0],
            gripper=0.0,
        )

        self.action_history.append(action)
        return action

    async def execute(self, action: Action) -> None:
        """Execute an action (simulated)."""
        self.execute_called_count += 1
        # Simulate execution delay
        await asyncio.sleep(0.001)

    def get_last_action(self) -> Optional[Action]:
        """Get the last executed action."""
        if self.action_history:
            return self.action_history[-1]
        return None


class MockVLAAdapterFactory:
    """Factory for creating MockVLAAdapter instances.

    Provides convenient test setup with common configurations.
    """

    def __init__(self):
        self._default_config = MockVLAAdapterConfig()

    def create(self, **overrides) -> MockVLAAdapter:
        """Create a new MockVLAAdapter with optional config overrides.

        Args:
            **overrides: Config values to override defaults

        Returns:
            MockVLAAdapter instance
        """
        config = MockVLAAdapterConfig(
            **{k: v for k, v in self._default_config.__dict__.items()
               if not k.startswith('_')}
        )
        for k, v in overrides.items():
            setattr(config, k, v)

        return MockVLAAdapter(**config.__dict__)

    def create_with_observation_types(
        self,
        observation_types: list[str],
    ) -> MockVLAAdapter:
        """Create adapter that accepts specific observation types.

        Args:
            observation_types: List of accepted observation type keys

        Returns:
            Configured MockVLAAdapter
        """
        return self.create(observation_types=observation_types)

    @staticmethod
    def create_default() -> MockVLAAdapter:
        """Create adapter with default configuration.

        Returns:
            MockVLAAdapter with default settings
        """
        return MockVLAAdapterFactory().create()
```

```python
# tests/fixtures/mock_arm.py
"""Mock arm adapters for testing."""
from __future__ import annotations

import asyncio
from typing import Any, Optional
from dataclasses import dataclass

try:
    from agents.hardware.arm_adapter import ArmAdapter
except ImportError:
    ArmAdapter = object

@dataclass
class Pose:
    """Mock pose representation."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

class MockArmAdapter(ArmAdapter if ArmAdapter != object else object):
    """Mock arm adapter for testing.

    Simulates arm behavior without requiring hardware.
    """

    def __init__(self):
        self._current_pose = Pose()
        self._gripper_open = True
        self._movement_history = []
        self._is_connected = True

    @property
    def is_connected(self) -> bool:
        """Check if arm is connected."""
        return self._is_connected

    async def connect(self) -> bool:
        """Simulate connection."""
        self._is_connected = True
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._is_connected = False

    async def move_to(
        self,
        position: list[float],
        rotation: Optional[list[float]] = None,
        duration: float = 1.0,
    ) -> bool:
        """Simulate move to position."""
        if not self._is_connected:
            return False

        self._current_pose = Pose(
            x=position[0],
            y=position[1],
            z=position[2],
            roll=rotation[0] if rotation else 0.0,
            pitch=rotation[1] if rotation else 0.0,
            yaw=rotation[2] if rotation else 0.0,
        )
        self._movement_history.append(("move_to", position))
        await asyncio.sleep(duration * 0.01)  # Simulate movement
        return True

    async def open_gripper(self) -> bool:
        """Open the gripper."""
        if not self._is_connected:
            return False
        self._gripper_open = True
        self._movement_history.append(("open_gripper", None))
        return True

    async def close_gripper(self) -> bool:
        """Close the gripper."""
        if not self._is_connected:
            return False
        self._gripper_open = False
        self._movement_history.append(("close_gripper", None))
        return True

    async def get_current_pose(self) -> dict[str, float]:
        """Get current end-effector pose."""
        return {
            "x": self._current_pose.x,
            "y": self._current_pose.y,
            "z": self._current_pose.z,
            "roll": self._current_pose.roll,
            "pitch": self._current_pose.pitch,
            "yaw": self._current_pose.yaw,
        }


class MockArmAdapterFactory:
    """Factory for creating MockArmAdapter instances."""

    def create(self, **config) -> MockArmAdapter:
        """Create a new MockArmAdapter."""
        return MockArmAdapter()

    @staticmethod
    def create_connected() -> MockArmAdapter:
        """Create a connected MockArmAdapter."""
        adapter = MockArmAdapter()
        # Don't auto-connect in factory
        return adapter

    @staticmethod
    def create_default() -> MockArmAdapter:
        """Create adapter with default configuration."""
        return MockArmAdapterFactory().create()
```

```python
# tests/fixtures/mock_llm.py
"""Mock LLM providers for testing."""
from __future__ import annotations

import asyncio
from typing import Any, Optional
from dataclasses import dataclass

try:
    from agents.llm.provider import LLMProvider
except ImportError:
    LLMProvider = object

@dataclass
class MockLLMConfig:
    """Configuration for MockLLMProvider."""
    model: str = "mock-llm"
    response_delay: float = 0.01
    should_fail: bool = False
    failure_message: str = "Mock LLM failure"

class MockLLMProvider(LLMProvider if LLMProvider != object else object):
    """Mock LLM provider for testing.

    Returns predefined responses or generates simple responses.
    """

    def __init__(self, **config):
        self._config = MockLLMConfig(**config)
        self._call_history = []
        self._responses = []

    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a mock response.

        Args:
            messages: Input messages

        Returns:
            Mock response dict
        """
        self._call_history.append(messages)

        if self._config.should_fail:
            raise Exception(self._config.failure_message)

        await asyncio.sleep(self._config.response_delay)

        # Check if we have predefined responses
        if self._responses:
            response = self._responses.pop(0)
        else:
            # Generate simple response
            last_message = messages[-1]["content"] if messages else ""
            response = {
                "role": "assistant",
                "content": f"Mock response to: {last_message[:50]}...",
            }

        return response

    def add_response(self, response: dict[str, Any]) -> None:
        """Add a predefined response to return."""
        self._responses.append(response)

    def get_call_history(self) -> list[list[dict[str, Any]]]:
        """Get all calls made to this provider."""
        return self._call_history.copy()

    def reset_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()


class MockLLMFactory:
    """Factory for creating MockLLMProvider instances."""

    def __init__(self):
        self._responses = []

    def create(self, **config) -> MockLLMProvider:
        """Create a new MockLLMProvider."""
        provider = MockLLMProvider(**config)
        for response in self._responses:
            provider.add_response(response)
        return provider

    def add_predefined_response(self, response: dict[str, Any]) -> None:
        """Add a predefined response to all created providers."""
        self._responses.append(response)

    @staticmethod
    def create_default() -> MockLLMProvider:
        """Create provider with default settings."""
        return MockLLMProvider()
```

```python
# tests/fixtures/mock_events.py
"""Mock event buses and message buses for testing."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable
from dataclasses import dataclass

try:
    from agents.events import EventBus
    from agents.channels import MessageBus
except ImportError:
    EventBus = object
    MessageBus = object

@dataclass
class MockEvent:
    """Mock event for testing."""
    event_type: str
    data: dict[str, Any] = None
    priority: int = 0

class MockEventBusFactory:
    """Factory for creating mock event bus implementations."""

    def create(self) -> MockEventBus:
        """Create a MockEventBus."""
        return MockEventBus()

    @staticmethod
    def create_default() -> MockEventBus:
        """Create event bus with default settings."""
        return MockEventBusFactory().create()


class MockEventBus:
    """Mock event bus for testing.

    Simple in-memory pub/sub implementation.
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._published_events: list[MockEvent] = []

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event: MockEvent) -> None:
        """Publish an event to all subscribers."""
        self._published_events.append(event)
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)

    def get_published_events(self, event_type: str = None) -> list[MockEvent]:
        """Get all published events, optionally filtered by type."""
        if event_type is None:
            return self._published_events.copy()
        return [e for e in self._published_events if e.event_type == event_type]

    def clear(self) -> None:
        """Clear all events and subscribers."""
        self._published_events.clear()
        self._subscribers.clear()


@dataclass
class MockInboundMessage:
    """Mock inbound message for testing."""
    channel: str
    content: Any
    metadata: dict[str, Any] = None

@dataclass
class MockOutboundMessage:
    """Mock outbound message for testing."""
    channel: str
    content: Any
    metadata: dict[str, Any] = None

class MockMessageBus:
    """Mock message bus for testing.

    Simulates MessageBus without actual queue implementation.
    """

    def __init__(self):
        self.inbound_messages: list[MockInboundMessage] = []
        self.outbound_messages: list[MockOutboundMessage] = []
        self._handlers: list[Callable] = []

    async def publish_inbound(self, msg: MockInboundMessage) -> None:
        """Publish an inbound message."""
        self.inbound_messages.append(msg)

    async def publish_outbound(self, msg: MockOutboundMessage) -> None:
        """Publish an outbound message."""
        self.outbound_messages.append(msg)
        for handler in self._handlers:
            await handler(msg)

    def register_outbound_handler(
        self,
        handler: Callable[[MockOutboundMessage], Awaitable[None]],
    ) -> None:
        """Register an outbound handler."""
        self._handlers.append(handler)

    def get_inbound_count(self) -> int:
        """Get count of inbound messages."""
        return len(self.inbound_messages)

    def get_outbound_count(self) -> int:
        """Get count of outbound messages."""
        return len(self.outbound_messages)

    def clear(self) -> None:
        """Clear all messages."""
        self.inbound_messages.clear()
        self.outbound_messages.clear()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_fixtures.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/ tests/test_fixtures.py
git commit -m "test(fixtures): add comprehensive test fixtures"
```

---

## Final Integration

### Task 8: Update `agents/__init__.py` Exports

**Files:**
- Modify: `agents/__init__.py`

**Step 1: Read current exports**

Run: `cat agents/__init__.py`

**Step 2: Update exports**

```python
# agents/__init__.py

# Exceptions
from agents.exceptions import (
    AgentError,
    AbortError,
    VLAActionError,
    HardwareError,
    TelemetrySafeError,
    ErrorKind,
    is_abort_error,
    classify_error,
    short_error_stack,
)

# Cache
from agents.cache import (
    cached,
    async_cached,
    SystemContextCache,
    get_system_context_cache,
    get_robot_capabilities_cached,
)

# Abort
from agents.abort import (
    AbortController,
    AbortScope,
    AbortError as AgentAbortError,
    run_with_abort,
    create_root_controller,
)

# Plugins
from agents.plugins import (
    Plugin,
    PluginMetadata,
    PluginRegistry,
    Tool,
    Skill,
    Hook,
    HookType,
)

# MCP
from agents.mcp import (
    MCPConfig,
    MCPClient,
    MCPServerManager,
    MCPTool,
)

# Context
from agents.context import (
    ContextBudget,
    ContextManager,
    MicroCompressor,
    MessageHistory,
)

__all__ = [
    # Exceptions
    "AgentError",
    "AbortError",
    "VLAActionError",
    "HardwareError",
    "TelemetrySafeError",
    "ErrorKind",
    "is_abort_error",
    "classify_error",
    "short_error_stack",
    # Cache
    "cached",
    "async_cached",
    "SystemContextCache",
    "get_system_context_cache",
    "get_robot_capabilities_cached",
    # Abort
    "AbortController",
    "AbortScope",
    "run_with_abort",
    "create_root_controller",
    # Plugins
    "Plugin",
    "PluginMetadata",
    "PluginRegistry",
    "Tool",
    "Skill",
    "Hook",
    "HookType",
    # MCP
    "MCPConfig",
    "MCPClient",
    "MCPServerManager",
    "MCPTool",
    # Context
    "ContextBudget",
    "ContextManager",
    "MicroCompressor",
    "MessageHistory",
]
```

**Step 3: Commit**

```bash
git add agents/__init__.py
git commit -m "feat: export new subsystem modules from agents package"
```

---

## Summary

**Total Tasks: 8**
**Estimated Time: 3-4 weeks (Phase 1: 1 week, Phase 2: 2 weeks, Phase 3: 1 week)**

| Phase | Tasks | Subsystems |
|-------|-------|------------|
| 1 | 1-2 | exceptions, cache |
| 2 | 3-6 | plugins, mcp, context, abort |
| 3 | 7-8 | fixtures, integration |

---

*Plan generated: 2026-04-02*
