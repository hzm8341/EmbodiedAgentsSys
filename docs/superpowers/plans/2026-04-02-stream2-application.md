# Stream 2 Application Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement five application-layer modules — long-term memory, plugin system, MCP protocol, context compression, and test infrastructure reorganization — on top of the Stream 1 foundation.

**Architecture:** All five modules depend on `agents/exceptions.py` and `agents/cache.py` from Stream 1. They are independent of each other and can be developed in parallel after Stream 1 completes. Tests restructure is last, touching all modules.

**Prerequisites:** Stream 1 (`agents/exceptions.py`, `agents/cache.py`, `agents/abort.py`) must be complete.

**Tech Stack:** Python 3.10+, asyncio, PyYAML, pytest, importlib, subprocess, json

---

## File Structure

```
agents/
├── memory/
│   └── longterm/              # TASKS 1-2: Long-term cross-session memory
│       ├── __init__.py
│       ├── types.py
│       ├── store.py
│       ├── retrieval.py
│       └── manager.py
├── plugins/                   # TASKS 3-4: Plugin system
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   └── builtin/
│       ├── __init__.py
│       ├── vla_plugin.py
│       ├── llm_plugin.py
│       └── sensor_plugin.py
├── mcp/                       # TASKS 5-7: MCP protocol
│   ├── __init__.py
│   ├── config.py
│   ├── auth.py
│   ├── protocol.py
│   ├── client.py
│   └── server_manager.py
└── context/                   # TASKS 8-9: Context compression
    ├── __init__.py
    ├── budget.py
    ├── compressor.py
    └── manager.py

tests/
├── fixtures/                  # TASK 10: Shared mock factories
│   ├── __init__.py
│   ├── mock_vla.py
│   ├── mock_arm.py
│   ├── mock_llm.py
│   └── mock_events.py
├── helpers/                   # TASK 11: Async + assertion utilities
│   ├── __init__.py
│   ├── async_helpers.py
│   └── assertion_helpers.py
├── unit/                      # TASK 12: Migrated unit tests
│   └── (existing test_*.py files moved here by domain)
└── integration/               # TASK 12: Integration tests
    ├── test_harness_full.py   (moved from tests/)
    └── test_agent_loop.py     (moved from tests/)
```

---

## Module 1: Long-Term Memory

### Task 1: `agents/memory/longterm/types.py` + `store.py`

**Files:**
- Create: `agents/memory/longterm/__init__.py`
- Create: `agents/memory/longterm/types.py`
- Create: `agents/memory/longterm/store.py`
- Test: `tests/test_longterm_memory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_longterm_memory.py
import json
import pytest
from pathlib import Path
from agents.memory.longterm.types import MemoryType, MemoryHeader, parse_frontmatter
from agents.memory.longterm.store import MemoryStore, truncate_entrypoint


class TestParseFromatter:
    def test_parses_valid_frontmatter(self):
        content = "---\nname: test\ndescription: desc\ntype: feedback\n---\nbody"
        result = parse_frontmatter(content)
        assert result["name"] == "test"
        assert result["type"] == "feedback"

    def test_returns_empty_dict_if_no_frontmatter(self):
        assert parse_frontmatter("just body text") == {}

    def test_returns_empty_dict_if_unclosed(self):
        assert parse_frontmatter("---\nname: test\nbody") == {}


class TestMemoryType:
    def test_all_four_types_exist(self):
        assert MemoryType.ROBOT_CONFIG.value == "robot_config"
        assert MemoryType.FEEDBACK.value == "feedback"
        assert MemoryType.MISSION.value == "mission"
        assert MemoryType.REFERENCE.value == "reference"


class TestMemoryStore:
    def test_save_creates_md_file(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("arm-type", MemoryType.ROBOT_CONFIG, "ARM type preference", "Use AGX arm.")
        files = list(tmp_path.glob("*.md"))
        assert any("arm" in f.name for f in files if f.name != "MEMORY.md")

    def test_save_updates_memory_index(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("vla-fail", MemoryType.FEEDBACK, "VLA failure pattern", "Body text.")
        index = (tmp_path / "MEMORY.md").read_text()
        assert "vla-fail" in index

    def test_load_returns_content(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("ros-topics", MemoryType.REFERENCE, "ROS topics list", "Topics here.")
        content = store.load("ros-topics")
        assert content is not None
        assert "Topics here." in content

    def test_load_returns_none_for_missing(self, tmp_path):
        store = MemoryStore(tmp_path)
        assert store.load("nonexistent") is None

    def test_delete_removes_file_and_index_entry(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("to-delete", MemoryType.MISSION, "Delete me", "Body.")
        store.delete("to-delete")
        assert store.load("to-delete") is None
        index = (tmp_path / "MEMORY.md").read_text()
        assert "to-delete" not in index

    def test_scan_files_returns_headers(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("a", MemoryType.FEEDBACK, "desc a", "body a")
        store.save("b", MemoryType.REFERENCE, "desc b", "body b")
        headers = store.scan_files()
        assert len(headers) == 2
        names = {h.name for h in headers}
        assert "a" in names and "b" in names

    def test_scan_excludes_memory_md(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("x", MemoryType.MISSION, "desc", "body")
        headers = store.scan_files()
        assert all(h.filename != "MEMORY.md" for h in headers)

    def test_get_index_returns_memory_md_content(self, tmp_path):
        store = MemoryStore(tmp_path)
        store.save("ref", MemoryType.REFERENCE, "ref desc", "ref body")
        index = store.get_index()
        assert "ref" in index


class TestTruncateEntrypoint:
    def test_short_content_unchanged(self):
        raw = "line1\nline2\nline3"
        assert truncate_entrypoint(raw) == raw

    def test_truncates_at_200_lines(self):
        raw = "\n".join(f"line{i}" for i in range(250))
        result = truncate_entrypoint(raw)
        assert "truncated" in result
        assert result.count("\n") < 250
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_longterm_memory.py -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `types.py` and `store.py`**

```python
# agents/memory/longterm/__init__.py
from agents.memory.longterm.types import MemoryType, MemoryHeader
from agents.memory.longterm.store import MemoryStore
from agents.memory.longterm.manager import LongTermMemoryManager

__all__ = ["MemoryType", "MemoryHeader", "MemoryStore", "LongTermMemoryManager"]
```

```python
# agents/memory/longterm/types.py
"""Memory type taxonomy for EmbodiedAgentsSys long-term memory.

Aligned with Claude Code memdir/memoryTypes.ts, adapted for robotics:
  robot_config  ≈ user       — robot preferences and configuration
  feedback      ≈ feedback   — what worked/failed in past operations
  mission       ≈ project    — current mission context and goals
  reference     ≈ reference  — pointers to external resources (ROS topics, files)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yaml


class MemoryType(str, Enum):
    ROBOT_CONFIG = "robot_config"
    FEEDBACK = "feedback"
    MISSION = "mission"
    REFERENCE = "reference"


@dataclass
class MemoryHeader:
    filename: str
    file_path: str
    mtime_ms: float
    description: Optional[str]
    type: Optional[MemoryType]
    name: Optional[str]


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content.

    Returns empty dict if no valid frontmatter block found.
    """
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except yaml.YAMLError:
        return {}
```

```python
# agents/memory/longterm/store.py
"""File-based memory storage aligned with Claude Code memdir/memoryScan.ts."""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from agents.memory.longterm.types import MemoryType, MemoryHeader, parse_frontmatter

MAX_MEMORY_FILES = 200
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000
ENTRYPOINT_NAME = "MEMORY.md"


class MemoryStore:
    """Manages memory files in a single directory."""

    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, type: MemoryType,
             description: str, body: str) -> Path:
        """Write a memory file and update MEMORY.md index."""
        safe_name = name.replace(" ", "_").replace("/", "-")
        filename = f"{type.value}_{safe_name}.md"
        path = self.memory_dir / filename
        content = (
            f"---\nname: {name}\ndescription: {description}\ntype: {type.value}\n---\n\n{body}\n"
        )
        path.write_text(content, encoding="utf-8")
        self._update_index(name, description, filename)
        return path

    def delete(self, name: str) -> None:
        """Remove a memory file and rebuild index."""
        for path in self.memory_dir.glob("*.md"):
            if path.name == ENTRYPOINT_NAME:
                continue
            fm = parse_frontmatter(path.read_text(encoding="utf-8"))
            if fm.get("name") == name:
                path.unlink()
                self._rebuild_index()
                return

    def load(self, name: str) -> Optional[str]:
        """Return full content of the named memory file, or None."""
        for path in self.memory_dir.glob("*.md"):
            if path.name == ENTRYPOINT_NAME:
                continue
            content = path.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm.get("name") == name:
                return content
        return None

    def scan_files(self) -> list[MemoryHeader]:
        """Scan directory for .md files, return headers sorted newest-first."""
        headers: list[MemoryHeader] = []
        paths = sorted(
            (p for p in self.memory_dir.glob("*.md") if p.name != ENTRYPOINT_NAME),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in paths[:MAX_MEMORY_FILES]:
            try:
                # Read only first 30 lines for frontmatter (avoids loading large files)
                lines = []
                with open(path, encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if i >= 30:
                            break
                        lines.append(line)
                content = "".join(lines)
                fm = parse_frontmatter(content)
                raw_type = fm.get("type")
                try:
                    mem_type = MemoryType(raw_type) if raw_type else None
                except ValueError:
                    mem_type = None
                headers.append(MemoryHeader(
                    filename=path.name,
                    file_path=str(path),
                    mtime_ms=path.stat().st_mtime * 1000,
                    description=fm.get("description"),
                    type=mem_type,
                    name=fm.get("name"),
                ))
            except Exception:
                continue
        return headers

    def get_index(self) -> str:
        """Return MEMORY.md content (truncated to caps)."""
        index_path = self.memory_dir / ENTRYPOINT_NAME
        if not index_path.exists():
            return ""
        return truncate_entrypoint(index_path.read_text(encoding="utf-8"))

    def _update_index(self, name: str, description: str, filename: str) -> None:
        index_path = self.memory_dir / ENTRYPOINT_NAME
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
        lines = [ln for ln in existing.splitlines() if f"[{name}]" not in ln]
        lines.append(f"- [{name}]({filename}) — {description}")
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _rebuild_index(self) -> None:
        headers = self.scan_files()
        lines = ["# Memory Index", ""]
        for h in headers:
            lines.append(f"- [{h.name or h.filename}]({h.filename}) — {h.description or ''}")
        (self.memory_dir / ENTRYPOINT_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def truncate_entrypoint(raw: str) -> str:
    """Truncate MEMORY.md at line or byte cap, appending a warning."""
    lines = raw.splitlines()
    was_line_truncated = False
    if len(lines) > MAX_ENTRYPOINT_LINES:
        lines = lines[:MAX_ENTRYPOINT_LINES]
        was_line_truncated = True

    result = "\n".join(lines)
    if len(result.encode("utf-8")) > MAX_ENTRYPOINT_BYTES:
        encoded = result.encode("utf-8")[:MAX_ENTRYPOINT_BYTES]
        result = encoded.decode("utf-8", errors="ignore")
        result += f"\n[truncated at {MAX_ENTRYPOINT_BYTES // 1000}KB]"
    elif was_line_truncated:
        result += f"\n[truncated at {MAX_ENTRYPOINT_LINES} lines]"
    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_longterm_memory.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/memory/longterm/ tests/test_longterm_memory.py
git commit -m "feat(memory): add longterm memory types + file store"
```

---

### Task 2: `agents/memory/longterm/retrieval.py` + `manager.py`

**Files:**
- Create: `agents/memory/longterm/retrieval.py`
- Create: `agents/memory/longterm/manager.py`
- Test: add to `tests/test_longterm_memory.py`

- [ ] **Step 1: Add retrieval + manager tests**

Append to `tests/test_longterm_memory.py`:

```python
# Append these classes to tests/test_longterm_memory.py

import asyncio
from unittest.mock import AsyncMock, MagicMock


class TestFindRelevantMemories:
    def test_returns_empty_if_no_files(self, tmp_path):
        from agents.memory.longterm.retrieval import find_relevant_memories
        from agents.memory.longterm.store import MemoryStore

        store = MemoryStore(tmp_path)
        mock_provider = MagicMock()
        result = asyncio.run(find_relevant_memories("grasp task", store, mock_provider))
        assert result == []

    def test_calls_llm_and_returns_relevant(self, tmp_path):
        from agents.memory.longterm.retrieval import find_relevant_memories
        from agents.memory.longterm.store import MemoryStore

        store = MemoryStore(tmp_path)
        store.save("vla-fail", MemoryType.FEEDBACK, "VLA failure", "Use force control.")
        store.save("ros-ref", MemoryType.REFERENCE, "ROS topics", "Topics list here.")

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=MagicMock(
            content='["feedback_vla-fail.md"]'
        ))

        results = asyncio.run(find_relevant_memories("grasp task", store, mock_provider))
        assert len(results) == 1
        assert "force control" in results[0].content

    def test_already_surfaced_are_excluded(self, tmp_path):
        from agents.memory.longterm.retrieval import find_relevant_memories
        from agents.memory.longterm.store import MemoryStore

        store = MemoryStore(tmp_path)
        store.save("mem-a", MemoryType.FEEDBACK, "desc a", "body a")

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=MagicMock(content='[]'))

        results = asyncio.run(find_relevant_memories(
            "query", store, mock_provider,
            already_surfaced={"feedback_mem-a.md"}
        ))
        assert results == []


class TestLongTermMemoryManager:
    def test_remember_and_recall(self, tmp_path):
        from agents.memory.longterm.manager import LongTermMemoryManager

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=MagicMock(
            content='["feedback_vla-grasp.md"]'
        ))

        mgr = LongTermMemoryManager(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
            provider=mock_provider,
        )
        mgr.remember("vla-grasp", MemoryType.FEEDBACK, "VLA grasp issue", "body", scope="project")
        results = asyncio.run(mgr.recall("grasp task"))
        assert any("body" in r for r in results)

    def test_forget_removes_memory(self, tmp_path):
        from agents.memory.longterm.manager import LongTermMemoryManager

        mock_provider = MagicMock()
        mgr = LongTermMemoryManager(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
            provider=mock_provider,
        )
        mgr.remember("temp", MemoryType.MISSION, "temp mission", "body", scope="project")
        mgr.forget("temp", scope="project")
        project_store_path = tmp_path / "project"
        from agents.memory.longterm.store import MemoryStore
        assert MemoryStore(project_store_path).load("temp") is None

    def test_get_index_both(self, tmp_path):
        from agents.memory.longterm.manager import LongTermMemoryManager

        mock_provider = MagicMock()
        mgr = LongTermMemoryManager(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
            provider=mock_provider,
        )
        mgr.remember("global-ref", MemoryType.REFERENCE, "global", "body", scope="global")
        mgr.remember("proj-ref", MemoryType.REFERENCE, "project", "body", scope="project")
        index = mgr.get_index("both")
        assert "global-ref" in index
        assert "proj-ref" in index
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_longterm_memory.py::TestFindRelevantMemories tests/test_longterm_memory.py::TestLongTermMemoryManager -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `retrieval.py` and `manager.py`**

```python
# agents/memory/longterm/retrieval.py
"""Semantic memory retrieval — aligned with Claude Code findRelevantMemories.ts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from agents.memory.longterm.store import MemoryStore
from agents.memory.longterm.types import MemoryHeader

if TYPE_CHECKING:
    from agents.llm.provider import LLMProvider

_SELECT_SYSTEM_PROMPT = (
    "You are selecting memories relevant to a robot task. "
    "Given the task description and available memory files (filename: description), "
    "return a JSON array of filenames for memories that will clearly help (up to 5). "
    "Only include memories you are certain will be useful. "
    "If none are clearly useful, return: []\n"
    "Return ONLY the JSON array, no other text."
)


@dataclass
class RelevantMemory:
    path: str
    mtime_ms: float
    content: str


async def find_relevant_memories(
    query: str,
    store: MemoryStore,
    provider: "LLMProvider",
    recent_tools: list[str] = [],
    already_surfaced: set[str] = set(),
    max_results: int = 5,
) -> list[RelevantMemory]:
    """Return up to max_results memories relevant to query.

    - Reads only frontmatter (first 30 lines) per file.
    - Skips files in already_surfaced set.
    - Uses provider.chat() to select relevant filenames.
    """
    headers = [h for h in store.scan_files() if h.filename not in already_surfaced]
    if not headers:
        return []

    manifest_lines = [
        f"- {h.filename}: {h.description or 'no description'} (type: {h.type})"
        for h in headers
    ]
    manifest = "\n".join(manifest_lines)

    response = await provider.chat(
        messages=[
            {"role": "system", "content": _SELECT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {query}\n\nAvailable memories:\n{manifest}"},
        ],
        max_tokens=256,
        temperature=0.0,
    )

    try:
        selected: list[str] = json.loads(response.content)
        if not isinstance(selected, list):
            return []
    except (json.JSONDecodeError, ValueError, AttributeError):
        return []

    by_filename = {h.filename: h for h in headers}
    results: list[RelevantMemory] = []
    for filename in selected[:max_results]:
        h = by_filename.get(filename)
        if h is None:
            continue
        content = store.load(h.name or filename) or ""
        results.append(RelevantMemory(
            path=h.file_path,
            mtime_ms=h.mtime_ms,
            content=content,
        ))
    return results
```

```python
# agents/memory/longterm/manager.py
"""Unified entry point for long-term memory operations."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agents.memory.longterm.store import MemoryStore
from agents.memory.longterm.types import MemoryType
from agents.memory.longterm.retrieval import find_relevant_memories

if TYPE_CHECKING:
    from agents.llm.provider import LLMProvider


class LongTermMemoryManager:
    """Manages global and project-scoped long-term memories.

    Usage:
        mgr = LongTermMemoryManager(
            global_dir=Path.home() / ".embodied_agents/memory",
            project_dir=Path(".embodied_agents/memory"),
            provider=llm_provider,
        )
        # At task start — inject into system prompt
        memories = await mgr.recall("grasp transparent object")

        # After task — save a new observation
        mgr.remember("vla-transparency", MemoryType.FEEDBACK,
                      "VLA fails on transparent objects", "Use force-control policy.")
    """

    def __init__(
        self,
        global_dir: Path,
        project_dir: Path,
        provider: "LLMProvider",
    ) -> None:
        self._global = MemoryStore(global_dir)
        self._project = MemoryStore(project_dir)
        self._provider = provider

    async def recall(
        self,
        query: str,
        recent_tools: list[str] = [],
    ) -> list[str]:
        """Return relevant memory contents for injection into system prompt."""
        already_surfaced: set[str] = set()

        project_mems = await find_relevant_memories(
            query, self._project, self._provider, recent_tools, already_surfaced
        )
        already_surfaced.update(m.path for m in project_mems)

        global_mems = await find_relevant_memories(
            query, self._global, self._provider, recent_tools, already_surfaced
        )
        return [m.content for m in project_mems + global_mems]

    def remember(
        self,
        name: str,
        type: MemoryType,
        description: str,
        body: str,
        scope: str = "project",
    ) -> None:
        """Save a memory to the given scope (project or global)."""
        store = self._project if scope == "project" else self._global
        store.save(name, type, description, body)

    def forget(self, name: str, scope: str = "project") -> None:
        """Delete a memory from the given scope."""
        store = self._project if scope == "project" else self._global
        store.delete(name)

    def get_index(self, scope: str = "both") -> str:
        """Return MEMORY.md contents for system prompt injection."""
        if scope == "global":
            return self._global.get_index()
        if scope == "project":
            return self._project.get_index()
        parts = []
        g = self._global.get_index()
        p = self._project.get_index()
        if g:
            parts.append(f"## Global Memory\n{g}")
        if p:
            parts.append(f"## Project Memory\n{p}")
        return "\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_longterm_memory.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/memory/longterm/retrieval.py agents/memory/longterm/manager.py tests/test_longterm_memory.py
git commit -m "feat(memory): add longterm retrieval + LongTermMemoryManager"
```

---

## Module 2: Plugin System

### Task 3: `agents/plugins/base.py` + `registry.py`

**Files:**
- Create: `agents/plugins/__init__.py`
- Create: `agents/plugins/base.py`
- Create: `agents/plugins/registry.py`
- Test: `tests/test_plugins.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plugins.py
import asyncio
import pytest
from agents.plugins.base import Plugin, Hook, HookEvent
from agents.plugins.registry import PluginRegistry


class ConcretePlugin(Plugin):
    name = "test-plugin"
    version = "1.0.0"
    description = "A test plugin"

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.initialized = False

    def get_tools(self):
        return []

    def get_skills(self):
        return []

    def get_hooks(self):
        return []


class TestPlugin:
    def test_plugin_initialize(self):
        p = ConcretePlugin()
        asyncio.run(p.initialize())
        assert p.initialized is True

    def test_plugin_shutdown(self):
        p = ConcretePlugin()
        asyncio.run(p.initialize())
        asyncio.run(p.shutdown())
        assert p.initialized is False


class TestPluginRegistry:
    def test_register_and_list(self):
        reg = PluginRegistry()
        p = ConcretePlugin()
        reg.register(p)
        assert "test-plugin" in [pl.name for pl in reg.get_all()]

    def test_enable_persists_state(self, tmp_path):
        reg = PluginRegistry(config_path=tmp_path / "plugins.yaml")
        p = ConcretePlugin()
        reg.register(p)
        reg.enable("test-plugin")
        assert "test-plugin" in [pl.name for pl in reg.get_enabled()]

    def test_disable_removes_from_enabled(self, tmp_path):
        reg = PluginRegistry(config_path=tmp_path / "plugins.yaml")
        p = ConcretePlugin()
        reg.register(p)
        reg.enable("test-plugin")
        reg.disable("test-plugin")
        assert "test-plugin" not in [pl.name for pl in reg.get_enabled()]

    def test_initialize_all_calls_enabled_plugins(self, tmp_path):
        reg = PluginRegistry(config_path=tmp_path / "plugins.yaml")
        p = ConcretePlugin()
        reg.register(p)
        reg.enable("test-plugin")
        asyncio.run(reg.initialize_all())
        assert p.initialized is True

    def test_get_plugin_by_name(self):
        reg = PluginRegistry()
        p = ConcretePlugin()
        reg.register(p)
        found = reg.get("test-plugin")
        assert found is p

    def test_get_unknown_returns_none(self):
        reg = PluginRegistry()
        assert reg.get("unknown") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_plugins.py -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `base.py` and `registry.py`**

```python
# agents/plugins/__init__.py
from agents.plugins.base import Plugin, Hook, HookEvent
from agents.plugins.registry import PluginRegistry

__all__ = ["Plugin", "Hook", "HookEvent", "PluginRegistry"]
```

```python
# agents/plugins/base.py
"""Plugin ABC and type definitions.

A plugin packages related tools, skills, and lifecycle hooks into a
single installable unit. Built-in plugins live in agents/plugins/builtin/.
External plugins declare an 'embodied_agents.plugins' entry point.
"""
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
    handler: Any  # Callable[[dict], None]
    description: str = ""


class Plugin(ABC):
    """Base class for all EmbodiedAgentsSys plugins."""

    name: str = ""
    version: str = "0.0.0"
    description: str = ""

    @abstractmethod
    async def initialize(self) -> None:
        """Called once when the plugin is activated."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Called once when the plugin is deactivated."""

    def get_tools(self) -> list[Any]:
        """Return tool definitions to register in RobotToolRegistry."""
        return []

    def get_skills(self) -> list[Any]:
        """Return skill configs to register in SkillRegistry."""
        return []

    def get_hooks(self) -> list[Hook]:
        """Return lifecycle hooks to subscribe to events."""
        return []
```

```python
# agents/plugins/registry.py
"""Plugin registry with enable/disable persistence."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import yaml

from agents.plugins.base import Plugin


class PluginRegistry:
    """Manages plugin registration, enable/disable state, and initialization."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._enabled: set[str] = set()
        self._config_path = config_path
        if config_path and Path(config_path).exists():
            self._load_config()

    def register(self, plugin: Plugin) -> None:
        """Register a plugin. Does not enable it."""
        self._plugins[plugin.name] = plugin

    def enable(self, name: str) -> None:
        """Enable a plugin and persist the state."""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not registered")
        self._enabled.add(name)
        self._save_config()

    def disable(self, name: str) -> None:
        """Disable a plugin and persist the state."""
        self._enabled.discard(name)
        self._save_config()

    def get_all(self) -> list[Plugin]:
        return list(self._plugins.values())

    def get_enabled(self) -> list[Plugin]:
        return [self._plugins[n] for n in self._enabled if n in self._plugins]

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    async def initialize_all(self) -> None:
        """Concurrently initialize all enabled plugins."""
        await asyncio.gather(*(p.initialize() for p in self.get_enabled()))

    async def shutdown_all(self) -> None:
        """Concurrently shut down all enabled plugins."""
        await asyncio.gather(*(p.shutdown() for p in self.get_enabled()))

    def _save_config(self) -> None:
        if not self._config_path:
            return
        Path(self._config_path).write_text(
            yaml.dump({"enabled_plugins": sorted(self._enabled)}),
            encoding="utf-8",
        )

    def _load_config(self) -> None:
        data = yaml.safe_load(Path(self._config_path).read_text(encoding="utf-8")) or {}
        self._enabled = set(data.get("enabled_plugins", []))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_plugins.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/plugins/ tests/test_plugins.py
git commit -m "feat(plugins): add Plugin ABC + PluginRegistry with enable/disable persistence"
```

---

### Task 4: `agents/plugins/builtin/`

**Files:**
- Create: `agents/plugins/builtin/__init__.py`
- Create: `agents/plugins/builtin/vla_plugin.py`
- Create: `agents/plugins/builtin/llm_plugin.py`
- Create: `agents/plugins/builtin/sensor_plugin.py`
- Test: add to `tests/test_plugins.py`

- [ ] **Step 1: Add builtin plugin tests**

Append to `tests/test_plugins.py`:

```python
# Append to tests/test_plugins.py

class TestBuiltinPlugins:
    def test_vla_plugin_has_correct_name(self):
        from agents.plugins.builtin.vla_plugin import VLAPlugin
        p = VLAPlugin()
        assert p.name == "vla"
        assert p.version != ""

    def test_llm_plugin_has_correct_name(self):
        from agents.plugins.builtin.llm_plugin import LLMPlugin
        p = LLMPlugin()
        assert p.name == "llm"

    def test_sensor_plugin_has_correct_name(self):
        from agents.plugins.builtin.sensor_plugin import SensorPlugin
        p = SensorPlugin()
        assert p.name == "sensor"

    def test_vla_plugin_provides_tools(self):
        from agents.plugins.builtin.vla_plugin import VLAPlugin
        p = VLAPlugin()
        tools = p.get_tools()
        names = [t["name"] for t in tools]
        assert "start_policy" in names
        assert "change_policy" in names

    def test_llm_plugin_provides_tools(self):
        from agents.plugins.builtin.llm_plugin import LLMPlugin
        p = LLMPlugin()
        tools = p.get_tools()
        assert any(t["name"] == "llm_query" for t in tools)

    def test_sensor_plugin_provides_tools(self):
        from agents.plugins.builtin.sensor_plugin import SensorPlugin
        p = SensorPlugin()
        tools = p.get_tools()
        assert any(t["name"] == "env_summary" for t in tools)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_plugins.py::TestBuiltinPlugins -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement builtin plugins**

```python
# agents/plugins/builtin/__init__.py
from agents.plugins.builtin.vla_plugin import VLAPlugin
from agents.plugins.builtin.llm_plugin import LLMPlugin
from agents.plugins.builtin.sensor_plugin import SensorPlugin

__all__ = ["VLAPlugin", "LLMPlugin", "SensorPlugin"]
```

```python
# agents/plugins/builtin/vla_plugin.py
"""VLA Plugin — wraps VLAAdapterBase as a plugin providing start/change_policy tools."""
from agents.plugins.base import Plugin


class VLAPlugin(Plugin):
    name = "vla"
    version = "1.0.0"
    description = "VLA (Vision-Language-Action) policy execution plugin"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "start_policy",
                "description": "Start a VLA policy skill by ID",
                "parameters": {"skill_id": "str", "kwargs": "dict"},
            },
            {
                "name": "change_policy",
                "description": "Switch to a different VLA policy mid-task",
                "parameters": {"skill_id": "str"},
            },
        ]
```

```python
# agents/plugins/builtin/llm_plugin.py
"""LLM Plugin — wraps LLMProvider as a plugin providing llm_query tool."""
from agents.plugins.base import Plugin


class LLMPlugin(Plugin):
    name = "llm"
    version = "1.0.0"
    description = "LLM inference plugin for CoT planning and query answering"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "llm_query",
                "description": "Send a direct query to the LLM provider",
                "parameters": {"prompt": "str", "system": "str"},
            }
        ]
```

```python
# agents/plugins/builtin/sensor_plugin.py
"""Sensor Plugin — wraps hardware adapters providing env_summary tool."""
from agents.plugins.base import Plugin


class SensorPlugin(Plugin):
    name = "sensor"
    version = "1.0.0"
    description = "Sensor and environment summary plugin"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "env_summary",
                "description": "Query current environment state from sensors",
                "parameters": {},
            }
        ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_plugins.py -v
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/plugins/builtin/ tests/test_plugins.py
git commit -m "feat(plugins): add builtin VLA, LLM, Sensor plugins"
```

---

## Module 3: MCP Protocol

### Task 5: `agents/mcp/config.py` + `auth.py`

**Files:**
- Create: `agents/mcp/__init__.py`
- Create: `agents/mcp/config.py`
- Create: `agents/mcp/auth.py`
- Test: `tests/test_mcp.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp.py
import json
import pytest
from pathlib import Path
from agents.mcp.config import MCPConfig, MCPScope
from agents.mcp.auth import MCPAuthStore


class TestMCPConfig:
    def test_default_scope_is_project(self):
        cfg = MCPConfig(name="test", command="python", args=["-m", "server"])
        assert cfg.scope == MCPScope.PROJECT

    def test_server_id_is_name(self):
        cfg = MCPConfig(name="my-server", command="npx", args=["server"])
        assert cfg.server_id == "my-server"

    def test_from_dict(self):
        data = {
            "name": "vision",
            "command": "python",
            "args": ["-m", "vision_server"],
            "env": {"MODEL_PATH": "/models"},
            "timeout": 60.0,
            "scope": "global",
        }
        cfg = MCPConfig.from_dict(data)
        assert cfg.name == "vision"
        assert cfg.env["MODEL_PATH"] == "/models"
        assert cfg.scope == MCPScope.GLOBAL
        assert cfg.timeout == 60.0


class TestMCPAuthStore:
    def test_save_and_read_token(self, tmp_path):
        store = MCPAuthStore(tmp_path / "tokens.json")
        store.save_token("server1", "abc123")
        assert store.read_token("server1") == "abc123"

    def test_missing_token_returns_none(self, tmp_path):
        store = MCPAuthStore(tmp_path / "tokens.json")
        assert store.read_token("nonexistent") is None

    def test_clear_token(self, tmp_path):
        store = MCPAuthStore(tmp_path / "tokens.json")
        store.save_token("s1", "tok")
        store.clear_token("s1")
        assert store.read_token("s1") is None

    def test_tokens_persist_across_instances(self, tmp_path):
        path = tmp_path / "tokens.json"
        MCPAuthStore(path).save_token("server", "mytoken")
        assert MCPAuthStore(path).read_token("server") == "mytoken"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_mcp.py -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `config.py` and `auth.py`**

```python
# agents/mcp/__init__.py
from agents.mcp.config import MCPConfig, MCPScope
from agents.mcp.auth import MCPAuthStore
from agents.mcp.client import MCPClient, MCPTool, ToolResult, HealthStatus
from agents.mcp.server_manager import MCPServerManager

__all__ = [
    "MCPConfig", "MCPScope", "MCPAuthStore",
    "MCPClient", "MCPTool", "ToolResult", "HealthStatus",
    "MCPServerManager",
]
```

```python
# agents/mcp/config.py
"""MCP server configuration — aligned with Claude Code services/mcp/types.ts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MCPScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"


@dataclass
class MCPConfig:
    """Configuration for a single MCP server."""
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
```

```python
# agents/mcp/auth.py
"""MCP authentication token storage."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class MCPAuthStore:
    """Persists MCP server auth tokens to a JSON file."""

    def __init__(self, token_path: Path) -> None:
        self._path = Path(token_path)

    def save_token(self, server_id: str, token: str) -> None:
        tokens = self._load()
        tokens[server_id] = token
        self._save(tokens)

    def read_token(self, server_id: str) -> Optional[str]:
        return self._load().get(server_id)

    def clear_token(self, server_id: str) -> None:
        tokens = self._load()
        tokens.pop(server_id, None)
        self._save(tokens)

    def _load(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, tokens: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_mcp.py::TestMCPConfig tests/test_mcp.py::TestMCPAuthStore -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/mcp/config.py agents/mcp/auth.py agents/mcp/__init__.py tests/test_mcp.py
git commit -m "feat(mcp): add MCPConfig + MCPAuthStore"
```

---

### Task 6: `agents/mcp/client.py`

**Files:**
- Create: `agents/mcp/client.py`
- Test: add to `tests/test_mcp.py`

- [ ] **Step 1: Add client tests**

Append to `tests/test_mcp.py`:

```python
# Append to tests/test_mcp.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestMCPClient:
    def test_initial_state_disconnected(self):
        from agents.mcp.client import MCPClient, HealthStatus
        from agents.mcp.config import MCPConfig
        cfg = MCPConfig(name="test", command="echo", args=["hello"])
        client = MCPClient(cfg)
        assert client.health_status == HealthStatus.DISCONNECTED

    def test_disconnect_when_not_connected_is_noop(self):
        from agents.mcp.client import MCPClient
        from agents.mcp.config import MCPConfig
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        asyncio.run(client.disconnect())  # should not raise

    def test_health_check_returns_status(self):
        from agents.mcp.client import MCPClient, HealthStatus
        from agents.mcp.config import MCPConfig
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        status = asyncio.run(client.health_check())
        assert isinstance(status, HealthStatus)

    def test_list_tools_returns_empty_when_disconnected(self):
        from agents.mcp.client import MCPClient
        from agents.mcp.config import MCPConfig
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        tools = asyncio.run(client.list_tools())
        assert tools == []

    def test_call_tool_raises_when_disconnected(self):
        from agents.mcp.client import MCPClient
        from agents.mcp.config import MCPConfig
        from agents.exceptions import HardwareError
        cfg = MCPConfig(name="test", command="echo", args=[])
        client = MCPClient(cfg)
        with pytest.raises(HardwareError):
            asyncio.run(client.call_tool("some_tool", {}))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_mcp.py::TestMCPClient -v 2>&1 | head -20
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `client.py`**

```python
# agents/mcp/client.py
"""MCP client — connects to an MCP server via subprocess stdio."""
from __future__ import annotations

import asyncio
import json
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
    """Communicates with an MCP server via JSON-RPC over stdio subprocess."""

    def __init__(self, config: MCPConfig) -> None:
        self._config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self.health_status = HealthStatus.DISCONNECTED

    async def connect(self) -> HealthStatus:
        """Start the MCP server subprocess and initialize the session."""
        try:
            self._process = await asyncio.create_subprocess_exec(
                self._config.command,
                *self._config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**__import__("os").environ, **self._config.env},
            )
            # Send initialize request
            result = await self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "embodied-agents", "version": "1.0.0"},
            })
            if result:
                self.health_status = HealthStatus.CONNECTED
            return self.health_status
        except Exception as e:
            self.health_status = HealthStatus.FAILED
            return self.health_status

    async def disconnect(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except Exception:
                pass
            self._process = None
        self.health_status = HealthStatus.DISCONNECTED

    async def health_check(self) -> HealthStatus:
        """Return current health status without reconnecting."""
        return self.health_status

    async def list_tools(self) -> list[MCPTool]:
        """Return available tools, or empty list if not connected."""
        if self.health_status != HealthStatus.CONNECTED:
            return []
        result = await self._request("tools/list", {})
        if not result:
            return []
        return [
            MCPTool(
                name=t["name"],
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in result.get("tools", [])
        ]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Call a tool on the MCP server."""
        if self.health_status != HealthStatus.CONNECTED:
            raise HardwareError(f"MCP server '{self._config.name}' is not connected")
        result = await self._request("tools/call", {"name": name, "arguments": arguments})
        if result is None:
            return ToolResult(content=None, is_error=True)
        return ToolResult(
            content=result.get("content"),
            is_error=result.get("isError", False),
        )

    async def list_resources(self) -> list[Resource]:
        if self.health_status != HealthStatus.CONNECTED:
            return []
        result = await self._request("resources/list", {})
        if not result:
            return []
        return [
            Resource(uri=r["uri"], name=r.get("name", ""), description=r.get("description", ""))
            for r in result.get("resources", [])
        ]

    async def read_resource(self, uri: str) -> ResourceContent:
        if self.health_status != HealthStatus.CONNECTED:
            raise HardwareError(f"MCP server '{self._config.name}' not connected")
        result = await self._request("resources/read", {"uri": uri})
        contents = result.get("contents", [{}]) if result else [{}]
        first = contents[0] if contents else {}
        return ResourceContent(
            uri=uri,
            content=first.get("text", ""),
            mime_type=first.get("mimeType", "text/plain"),
        )

    async def _request(self, method: str, params: dict) -> Optional[dict]:
        """Send a JSON-RPC request and await the response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            return None
        self._request_id += 1
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }) + "\n"
        try:
            self._process.stdin.write(payload.encode())
            await self._process.stdin.drain()
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=self._config.timeout,
            )
            response = json.loads(line.decode())
            return response.get("result")
        except Exception:
            return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_mcp.py::TestMCPClient -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/mcp/client.py tests/test_mcp.py
git commit -m "feat(mcp): add MCPClient with JSON-RPC stdio transport"
```

---

### Task 7: `agents/mcp/server_manager.py`

**Files:**
- Create: `agents/mcp/server_manager.py`
- Test: add to `tests/test_mcp.py`

- [ ] **Step 1: Add server manager tests**

Append to `tests/test_mcp.py`:

```python
# Append to tests/test_mcp.py


class TestMCPServerManager:
    def test_add_and_list_servers(self):
        from agents.mcp.server_manager import MCPServerManager
        from agents.mcp.config import MCPConfig
        mgr = MCPServerManager()
        cfg = MCPConfig(name="vision", command="python", args=[])
        mgr.add_server(cfg)
        statuses = mgr.list_servers()
        assert any(s["name"] == "vision" for s in statuses)

    def test_get_server_by_id(self):
        from agents.mcp.server_manager import MCPServerManager
        from agents.mcp.config import MCPConfig
        from agents.mcp.client import MCPClient
        mgr = MCPServerManager()
        mgr.add_server(MCPConfig(name="s1", command="echo", args=[]))
        client = mgr.get_server("s1")
        assert isinstance(client, MCPClient)

    def test_get_nonexistent_returns_none(self):
        from agents.mcp.server_manager import MCPServerManager
        mgr = MCPServerManager()
        assert mgr.get_server("unknown") is None

    def test_remove_server(self):
        from agents.mcp.server_manager import MCPServerManager
        from agents.mcp.config import MCPConfig
        mgr = MCPServerManager()
        mgr.add_server(MCPConfig(name="temp", command="echo", args=[]))
        mgr.remove_server("temp")
        assert mgr.get_server("temp") is None

    def test_check_all_health_returns_dict(self):
        from agents.mcp.server_manager import MCPServerManager
        from agents.mcp.config import MCPConfig
        mgr = MCPServerManager()
        mgr.add_server(MCPConfig(name="s1", command="echo", args=[]))
        results = asyncio.run(mgr.check_all_health())
        assert "s1" in results
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_mcp.py::TestMCPServerManager -v 2>&1 | head -20
```
Expected: FAIL

- [ ] **Step 3: Implement `server_manager.py`**

```python
# agents/mcp/server_manager.py
"""Manages multiple MCP server connections."""
from __future__ import annotations

import asyncio
from typing import Optional

from agents.mcp.client import MCPClient, HealthStatus
from agents.mcp.config import MCPConfig


class MCPServerManager:
    """Tracks and manages multiple MCP server clients."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPClient] = {}

    def add_server(self, config: MCPConfig) -> str:
        """Register a server config and create a client. Returns server_id."""
        client = MCPClient(config)
        self._servers[config.server_id] = client
        return config.server_id

    def remove_server(self, server_id: str) -> None:
        """Remove a server (disconnects if connected)."""
        client = self._servers.pop(server_id, None)
        if client:
            asyncio.get_event_loop().run_until_complete(client.disconnect())

    def get_server(self, server_id: str) -> Optional[MCPClient]:
        return self._servers.get(server_id)

    def list_servers(self) -> list[dict]:
        """Return name and health status for all registered servers."""
        return [
            {"name": sid, "health": client.health_status.value}
            for sid, client in self._servers.items()
        ]

    async def check_all_health(self) -> dict[str, HealthStatus]:
        """Concurrently check health of all registered servers."""
        results = await asyncio.gather(
            *(client.health_check() for client in self._servers.values()),
            return_exceptions=True,
        )
        return {
            sid: (r if isinstance(r, HealthStatus) else HealthStatus.FAILED)
            for sid, r in zip(self._servers.keys(), results)
        }
```

- [ ] **Step 4: Run all MCP tests**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_mcp.py -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/mcp/server_manager.py tests/test_mcp.py
git commit -m "feat(mcp): add MCPServerManager with concurrent health checks"
```

---

## Module 4: Context Compression

### Task 8: `agents/context/budget.py` + `compressor.py`

**Files:**
- Create: `agents/context/__init__.py`
- Create: `agents/context/budget.py`
- Create: `agents/context/compressor.py`
- Test: `tests/test_context.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context.py
import pytest
from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import MicroCompressor


class TestContextBudget:
    def _make_messages(self, n_tokens_approx: int) -> list[dict]:
        # Each char ~= 0.25 tokens, so 4 chars = 1 token
        content = "x" * (n_tokens_approx * 4)
        return [{"role": "user", "content": content}]

    def test_ok_when_below_warning(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(700)
        assert budget.check_budget(msgs) == BudgetStatus.OK

    def test_warning_at_80_percent(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(820)
        assert budget.check_budget(msgs) == BudgetStatus.WARNING

    def test_critical_at_95_percent(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(960)
        assert budget.check_budget(msgs) == BudgetStatus.CRITICAL

    def test_estimate_tokens_is_positive(self):
        budget = ContextBudget()
        msgs = [{"role": "user", "content": "hello world"}]
        assert budget.estimate_tokens(msgs) > 0

    def test_should_warn_true_when_warning(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(820)
        assert budget.should_warn(msgs) is True

    def test_should_compress_true_when_critical(self):
        budget = ContextBudget(max_tokens=1000)
        msgs = self._make_messages(960)
        assert budget.should_compress(msgs) is True


class TestMicroCompressor:
    def test_truncate_long_content(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "x" * 5000}
        result = compressor.truncate_long_content(msg, max_chars=100)
        assert len(result["content"]) <= 110  # small slack for truncation note

    def test_short_content_unchanged(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "hello"}
        result = compressor.truncate_long_content(msg, max_chars=1000)
        assert result["content"] == "hello"

    def test_strip_images_removes_image_content(self):
        compressor = MicroCompressor()
        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ],
        }
        result = compressor.strip_images(msg)
        content = result["content"]
        if isinstance(content, list):
            assert all(item.get("type") != "image_url" for item in content)
        else:
            assert "image" not in content.lower()

    def test_compress_message_combines_strategies(self):
        compressor = MicroCompressor()
        msg = {"role": "user", "content": "x" * 10000}
        result = compressor.compress_message(msg)
        assert len(result["content"]) < len(msg["content"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_context.py -v 2>&1 | head -20
```
Expected: FAIL

- [ ] **Step 3: Implement `budget.py` and `compressor.py`**

```python
# agents/context/__init__.py
from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import MicroCompressor, AutoCompactor
from agents.context.manager import ContextManager

__all__ = ["ContextBudget", "BudgetStatus", "MicroCompressor", "AutoCompactor", "ContextManager"]
```

```python
# agents/context/budget.py
"""Token budget tracking for context window management."""
from __future__ import annotations

from enum import Enum
from typing import Any


class BudgetStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"     # >= 80%
    CRITICAL = "critical"   # >= 95%


class ContextBudget:
    """Tracks approximate token usage and signals when compression is needed.

    Token estimation: len(text) // 4  (fast approximation, ~25% error)
    """

    def __init__(
        self,
        max_tokens: int = 100_000,
        warning_threshold: float = 0.80,
        critical_threshold: float = 0.95,
    ) -> None:
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Approximate token count across all messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += max(1, len(content) // 4)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total += max(1, len(item.get("text", "")) // 4)
                    elif isinstance(item, dict) and "image" in item.get("type", ""):
                        total += 1000  # image token estimate
        return total

    def check_budget(self, messages: list[dict[str, Any]]) -> BudgetStatus:
        used = self.estimate_tokens(messages)
        ratio = used / self.max_tokens
        if ratio >= self.critical_threshold:
            return BudgetStatus.CRITICAL
        if ratio >= self.warning_threshold:
            return BudgetStatus.WARNING
        return BudgetStatus.OK

    def should_warn(self, messages: list[dict[str, Any]]) -> bool:
        return self.check_budget(messages) in (BudgetStatus.WARNING, BudgetStatus.CRITICAL)

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        return self.check_budget(messages) == BudgetStatus.CRITICAL
```

```python
# agents/context/compressor.py
"""Message compression strategies for context window management."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MicroCompressor:
    """Single-message compression: strips images, truncates long text."""

    def compress_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Apply all compression strategies to a single message."""
        msg = self.strip_images(msg)
        msg = self.truncate_long_content(msg)
        return msg

    def strip_images(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Remove image content blocks from a message."""
        content = msg.get("content")
        if isinstance(content, list):
            filtered = [
                item for item in content
                if not (isinstance(item, dict) and "image" in item.get("type", ""))
            ]
            return {**msg, "content": filtered}
        return msg

    def truncate_long_content(
        self, msg: dict[str, Any], max_chars: int = 2000
    ) -> dict[str, Any]:
        """Truncate text content exceeding max_chars."""
        content = msg.get("content")
        if isinstance(content, str) and len(content) > max_chars:
            return {**msg, "content": content[:max_chars] + " [truncated]"}
        return msg


@dataclass
class CompactionStats:
    messages_before: int
    messages_after: int
    tokens_before: int
    tokens_after: int


class AutoCompactor:
    """Triggers automatic context compression when budget is exceeded."""

    def __init__(self, micro: MicroCompressor | None = None) -> None:
        self._micro = micro or MicroCompressor()
        self._stats = CompactionStats(0, 0, 0, 0)

    async def compact_if_needed(
        self,
        messages: list[dict[str, Any]],
        should_compress: bool,
    ) -> list[dict[str, Any]]:
        """Apply MicroCompressor to all messages if compression is triggered."""
        if not should_compress:
            return messages
        return [self._micro.compress_message(msg) for msg in messages]

    def get_stats(self) -> CompactionStats:
        return self._stats
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_context.py -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/context/budget.py agents/context/compressor.py agents/context/__init__.py tests/test_context.py
git commit -m "feat(context): add ContextBudget + MicroCompressor + AutoCompactor"
```

---

### Task 9: `agents/context/manager.py`

**Files:**
- Create: `agents/context/manager.py`
- Test: add to `tests/test_context.py`

- [ ] **Step 1: Add manager tests**

Append to `tests/test_context.py`:

```python
# Append to tests/test_context.py
import asyncio


class TestContextManager:
    def _make_small_msgs(self):
        return [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]

    def _make_large_msgs(self, n_tokens=96000):
        content = "x" * (n_tokens * 4)
        return [{"role": "user", "content": content}]

    def test_process_small_returns_unchanged(self):
        from agents.context.manager import ContextManager
        mgr = ContextManager(max_tokens=100_000)
        msgs = self._make_small_msgs()
        result = asyncio.run(mgr.process(msgs))
        assert result == msgs

    def test_process_critical_compresses(self):
        from agents.context.manager import ContextManager
        mgr = ContextManager(max_tokens=100_000)
        msgs = self._make_large_msgs(n_tokens=96000)
        result = asyncio.run(mgr.process(msgs))
        # After compression, content should be shorter
        original_len = sum(len(m.get("content", "")) for m in msgs)
        result_len = sum(len(m.get("content", "")) for m in result)
        assert result_len < original_len

    def test_get_status_returns_budget_status(self):
        from agents.context.manager import ContextManager
        from agents.context.budget import BudgetStatus
        mgr = ContextManager(max_tokens=100_000)
        msgs = self._make_small_msgs()
        status = mgr.get_status(msgs)
        assert status == BudgetStatus.OK
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_context.py::TestContextManager -v 2>&1 | head -10
```
Expected: FAIL

- [ ] **Step 3: Implement `manager.py`**

```python
# agents/context/manager.py
"""Unified context window management entry point."""
from __future__ import annotations

from typing import Any

from agents.context.budget import ContextBudget, BudgetStatus
from agents.context.compressor import AutoCompactor, MicroCompressor


class ContextManager:
    """Coordinate budget tracking and compression.

    Used by RobotAgentLoop:
        result = await context_mgr.process(messages)
    """

    def __init__(self, max_tokens: int = 100_000) -> None:
        self._budget = ContextBudget(max_tokens=max_tokens)
        self._compactor = AutoCompactor(MicroCompressor())

    async def process(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Compress messages if budget is exceeded."""
        should_compress = self._budget.should_compress(messages)
        return await self._compactor.compact_if_needed(messages, should_compress)

    def get_status(self, messages: list[dict[str, Any]]) -> BudgetStatus:
        """Return current budget status without modifying messages."""
        return self._budget.check_budget(messages)
```

- [ ] **Step 4: Run all context tests**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_context.py -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add agents/context/manager.py tests/test_context.py
git commit -m "feat(context): add ContextManager unifying budget + compressor"
```

---

## Module 5: Test Infrastructure

### Task 10: `tests/fixtures/`

**Files:**
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/mock_vla.py`
- Create: `tests/fixtures/mock_arm.py`
- Create: `tests/fixtures/mock_llm.py`
- Create: `tests/fixtures/mock_events.py`
- Test: `tests/test_fixtures.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fixtures.py
import asyncio
import pytest


class TestMockVLAFactory:
    def test_factory_returns_adapter(self):
        from tests.fixtures.mock_vla import make_mock_vla
        adapter = make_mock_vla()
        assert adapter is not None

    def test_factory_success_rate_param(self):
        from tests.fixtures.mock_vla import make_mock_vla
        adapter = make_mock_vla(success_rate=1.0)
        assert adapter.success_rate == 1.0

    def test_act_returns_7dof_action(self):
        from tests.fixtures.mock_vla import make_mock_vla
        adapter = make_mock_vla(action_noise=False)
        action = asyncio.run(adapter.act({"image": "test"}, "grasp"))
        assert len(action) == 7


class TestMockArmFactory:
    def test_factory_returns_adapter(self):
        from tests.fixtures.mock_arm import make_mock_arm
        arm = make_mock_arm()
        assert arm is not None

    def test_move_to_pose_returns_bool(self):
        from tests.fixtures.mock_arm import make_mock_arm
        from agents.hardware.arm_adapter import Pose6D
        arm = make_mock_arm(joint_error_rate=0.0)
        result = asyncio.run(arm.move_to_pose(Pose6D(0.3, 0, 0.2, 0, 0, 0)))
        assert result is True


class TestMockLLMProvider:
    def test_returns_configured_response(self):
        from tests.fixtures.mock_llm import make_mock_llm
        provider = make_mock_llm(responses=["response1", "response2"])
        result = asyncio.run(provider.chat([{"role": "user", "content": "hello"}]))
        assert result.content == "response1"

    def test_cycles_through_responses(self):
        from tests.fixtures.mock_llm import make_mock_llm
        provider = make_mock_llm(responses=["a", "b"])
        asyncio.run(provider.chat([{"role": "user", "content": "1"}]))
        r2 = asyncio.run(provider.chat([{"role": "user", "content": "2"}]))
        assert r2.content == "b"


class TestMockEventBus:
    def test_publish_and_subscribe(self):
        from tests.fixtures.mock_events import MockEventBus
        bus = MockEventBus()
        received = []
        bus.subscribe("test_event", lambda e: received.append(e))
        bus.publish("test_event", {"data": 42})
        assert received == [{"data": 42}]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_fixtures.py -v 2>&1 | head -20
```
Expected: FAIL

- [ ] **Step 3: Implement fixture factories**

```python
# tests/fixtures/__init__.py
```

```python
# tests/fixtures/mock_vla.py
"""MockVLA factory for test use."""
import random


class _MockVLAAdapter:
    def __init__(self, success_rate: float, action_noise: bool):
        self.success_rate = success_rate
        self.action_noise = action_noise
        self.action_history: list = []

    def reset(self) -> None:
        self.action_history.clear()

    async def act(self, observation: dict, instruction: str) -> list[float]:
        base = [0.1, 0.0, 0.2, 0.0, 0.0, 0.0, 0.5]
        if self.action_noise:
            base = [a + random.gauss(0, 0.01) for a in base]
        self.action_history.append(base)
        return base

    async def execute(self, action: list[float]) -> dict:
        success = random.random() < self.success_rate
        return {"success": success, "action": action}


def make_mock_vla(success_rate: float = 1.0, action_noise: bool = False) -> _MockVLAAdapter:
    return _MockVLAAdapter(success_rate=success_rate, action_noise=action_noise)
```

```python
# tests/fixtures/mock_arm.py
"""MockArm factory for test use."""
import asyncio
import random
from agents.hardware.arm_adapter import ArmAdapter, Pose6D, RobotState, RobotCapabilities


class _MockArmAdapter(ArmAdapter):
    def __init__(self, joint_error_rate: float, latency_ms: int):
        self._joint_error_rate = joint_error_rate
        self._latency_ms = latency_ms
        self._joints = [0.0] * 7
        self._gripper = 0.0

    async def move_to_pose(self, pose: Pose6D, speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = [0.1] * 7
        return True

    async def move_joints(self, angles: list[float], speed: float = 0.1) -> bool:
        await asyncio.sleep(self._latency_ms / 1000.0)
        if random.random() < self._joint_error_rate:
            return False
        self._joints = angles[:]
        return True

    async def set_gripper(self, opening: float, force: float = 10.0) -> bool:
        self._gripper = max(0.0, min(1.0, opening))
        return True

    async def get_state(self) -> RobotState:
        return RobotState(
            joint_angles=self._joints[:],
            end_effector_pose=Pose6D(0.3, 0.0, 0.2, 0, 0, 0),
            gripper_opening=self._gripper,
            is_moving=False,
            error_code=0,
        )

    async def is_ready(self) -> bool:
        return True

    async def emergency_stop(self) -> None:
        pass

    def get_capabilities(self) -> RobotCapabilities:
        return RobotCapabilities(robot_type="arm", supported_skills=[])


def make_mock_arm(joint_error_rate: float = 0.0, latency_ms: int = 0) -> _MockArmAdapter:
    return _MockArmAdapter(joint_error_rate=joint_error_rate, latency_ms=latency_ms)
```

```python
# tests/fixtures/mock_llm.py
"""MockLLM factory for test use."""
from dataclasses import dataclass, field
from typing import Any
from agents.llm.provider import LLMProvider, LLMResponse


class _MockLLMProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._index = 0
        self.call_history: list[list] = []

    async def chat(self, messages, tools=None, model=None,
                   max_tokens=4096, temperature=0.7,
                   reasoning_effort=None, tool_choice=None, **kwargs) -> LLMResponse:
        self.call_history.append(messages)
        if self._responses:
            content = self._responses[self._index % len(self._responses)]
            self._index += 1
        else:
            content = "mock response"
        return LLMResponse(content=content, tool_calls=[])

    def get_model_name(self) -> str:
        return "mock-model"


def make_mock_llm(responses: list[str] | None = None) -> _MockLLMProvider:
    return _MockLLMProvider(responses=responses or ["mock response"])
```

```python
# tests/fixtures/mock_events.py
"""MockEventBus for test use."""
from collections import defaultdict
from typing import Any, Callable


class MockEventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self.published_events: list[tuple[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, event: Any) -> None:
        self.published_events.append((event_type, event))
        for handler in self._subscribers.get(event_type, []):
            handler(event)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_fixtures.py -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add tests/fixtures/ tests/test_fixtures.py
git commit -m "feat(tests): add shared mock factories (VLA, Arm, LLM, EventBus)"
```

---

### Task 11: `tests/helpers/`

**Files:**
- Create: `tests/helpers/__init__.py`
- Create: `tests/helpers/async_helpers.py`
- Create: `tests/helpers/assertion_helpers.py`
- Test: add to `tests/test_fixtures.py`

- [ ] **Step 1: Add helper tests**

Append to `tests/test_fixtures.py`:

```python
# Append to tests/test_fixtures.py


class TestAsyncHelpers:
    def test_run_async_runs_coroutine(self):
        from tests.helpers.async_helpers import run_async

        async def coro():
            return 42

        assert run_async(coro()) == 42

    def test_assert_eventually_passes_when_condition_met(self):
        from tests.helpers.async_helpers import assert_eventually
        counter = {"n": 0}

        async def condition():
            counter["n"] += 1
            return counter["n"] >= 3

        asyncio.run(assert_eventually(condition, timeout=1.0, interval=0.01))

    def test_assert_eventually_raises_on_timeout(self):
        from tests.helpers.async_helpers import assert_eventually

        async def always_false():
            return False

        with pytest.raises(AssertionError):
            asyncio.run(assert_eventually(always_false, timeout=0.05, interval=0.01))


class TestAssertionHelpers:
    def test_assert_skill_called(self):
        from tests.helpers.assertion_helpers import assert_skill_called

        class FakeTrace:
            skill_calls = ["manipulation.grasp", "manipulation.place"]

        assert_skill_called(FakeTrace(), "manipulation.grasp")

    def test_assert_skill_called_raises_if_missing(self):
        from tests.helpers.assertion_helpers import assert_skill_called

        class FakeTrace:
            skill_calls = []

        with pytest.raises(AssertionError):
            assert_skill_called(FakeTrace(), "manipulation.grasp")

    def test_assert_no_abort(self):
        from tests.helpers.assertion_helpers import assert_no_abort

        class FakeTrace:
            failure_reason = None
            final_status = "completed"

        assert_no_abort(FakeTrace())

    def test_assert_no_abort_raises_on_abort(self):
        from tests.helpers.assertion_helpers import assert_no_abort

        class FakeTrace:
            failure_reason = "user cancelled"
            final_status = "aborted"

        with pytest.raises(AssertionError):
            assert_no_abort(FakeTrace())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_fixtures.py::TestAsyncHelpers tests/test_fixtures.py::TestAssertionHelpers -v 2>&1 | head -20
```
Expected: FAIL

- [ ] **Step 3: Implement helpers**

```python
# tests/helpers/__init__.py
```

```python
# tests/helpers/async_helpers.py
"""Utilities for testing async code without pytest-asyncio."""
import asyncio
from typing import Callable, Any


def run_async(coro) -> Any:
    """Run a coroutine synchronously in a test."""
    return asyncio.run(coro)


async def assert_eventually(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition never became True",
) -> None:
    """Repeatedly check async condition until True or timeout."""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await condition():
            return
        await asyncio.sleep(interval)
    raise AssertionError(message)
```

```python
# tests/helpers/assertion_helpers.py
"""Domain-specific assertion helpers for robot agent tests."""
from typing import Any


def assert_skill_called(trace: Any, skill_id: str) -> None:
    """Assert that a skill was called during the traced execution."""
    assert skill_id in trace.skill_calls, (
        f"Expected skill '{skill_id}' to be called, "
        f"but skill_calls was: {trace.skill_calls}"
    )


def assert_no_abort(trace: Any) -> None:
    """Assert that the trace ended without an abort."""
    assert trace.final_status != "aborted", (
        f"Expected no abort but trace was aborted: {trace.failure_reason}"
    )
    assert not trace.failure_reason or "abort" not in str(trace.failure_reason).lower(), (
        f"Unexpected abort reason: {trace.failure_reason}"
    )


def assert_error_kind(exc: Exception, kind: Any) -> None:
    """Assert that an exception classifies to the expected ErrorKind."""
    from agents.exceptions import classify_error
    actual = classify_error(exc)
    assert actual == kind, f"Expected ErrorKind.{kind.value}, got ErrorKind.{actual.value}"
```

- [ ] **Step 4: Run all test infrastructure tests**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_fixtures.py -v
```
Expected: All pass

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add tests/helpers/ tests/test_fixtures.py
git commit -m "feat(tests): add async_helpers + assertion_helpers"
```

---

### Task 12: Migrate existing tests to `unit/` + `integration/`

**Files:**
- Create: `tests/unit/` (directory, with migrated test files)
- Create: `tests/integration/` (directory, with migrated test files)

- [ ] **Step 1: Create directories and move integration tests**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
mkdir -p tests/unit tests/integration

# Move integration-level tests
mv tests/test_harness_full.py tests/integration/
mv tests/test_full_integration.py tests/integration/ 2>/dev/null || true
mv tests/test_agent_loop.py tests/integration/ 2>/dev/null || true

# Verify they still import correctly
python3 -m pytest tests/integration/ -v --collect-only 2>&1 | head -20
```

- [ ] **Step 2: Move unit tests by domain**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
mkdir -p tests/unit/harness tests/unit/components tests/unit/clients tests/unit/hardware

# Harness tests
for f in tests/test_harness_mode.py tests/test_harness_config.py tests/test_task_set.py \
          tests/test_task_loader.py tests/test_tracer.py tests/test_trace_replayer.py \
          tests/test_evaluator_base.py tests/test_result_eval.py \
          tests/test_efficiency_robustness_eval.py tests/test_explainability_eval.py \
          tests/test_scorer.py tests/test_mocks.py tests/test_harness_integration.py \
          tests/test_harness_runner.py; do
    [ -f "$f" ] && mv "$f" tests/unit/harness/
done

# Component tests
for f in tests/test_task_planner.py tests/test_robot_memory.py tests/test_skill_format.py \
          tests/test_channels.py tests/test_conversational_onboarding.py \
          tests/test_eap_and_supervision.py tests/test_scene_spec.py; do
    [ -f "$f" ] && mv "$f" tests/unit/components/
done

# Client tests
for f in tests/test_llm_provider.py tests/test_clients.py tests/test_lerobot_adapter.py \
          tests/test_act_adapter.py tests/test_gr00t_adapter.py \
          tests/test_vla_adapter_base.py; do
    [ -f "$f" ] && mv "$f" tests/unit/clients/
done

# Hardware tests
for f in tests/test_arm_adapter.py tests/test_capability_registry.py \
          tests/test_gap_detector.py; do
    [ -f "$f" ] && mv "$f" tests/unit/hardware/
done
```

- [ ] **Step 3: Add `__init__.py` to new directories**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
touch tests/unit/__init__.py tests/unit/harness/__init__.py \
      tests/unit/components/__init__.py tests/unit/clients/__init__.py \
      tests/unit/hardware/__init__.py tests/integration/__init__.py
```

- [ ] **Step 4: Run full test suite to confirm no breakage**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/ -q 2>&1 | tail -15
```
Expected: Previously passing tests all still pass. Any failures are pre-existing, not caused by the move.

- [ ] **Step 5: Commit**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git add tests/unit/ tests/integration/
git commit -m "refactor(tests): reorganize into unit/ and integration/ directories"
```

---

## Phase Final: Full Stream 2 Verification

### Task 13: Run complete test suite

- [ ] **Step 1: Run all Stream 2 tests**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/test_longterm_memory.py tests/test_plugins.py \
  tests/test_mcp.py tests/test_context.py tests/test_fixtures.py -v 2>&1 | tail -20
```
Expected: All new tests pass

- [ ] **Step 2: Run full suite for regression check**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
python3 -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: No regressions from Stream 1 or previously passing tests

- [ ] **Step 3: Tag Stream 2 completion**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
git tag stream2-application
git push origin stream2-application
```

---

## Self-Review Notes

- **Spec coverage:** All 8 subsystems covered across Tasks 1-12. memory/longterm, plugins, mcp, context each have dedicated test files. Test restructure in Task 12 uses `mv` which may vary by environment.
- **Placeholder scan:** No TBDs found. `make_mock_llm` accesses `LLMResponse` from `agents.llm.provider` — verified `LLMResponse` exists (seen in provider.py).
- **Type consistency:** `MCPClient` uses `MCPConfig` (defined in config.py), `MemoryStore` uses `MemoryType` (defined in types.py), `LongTermMemoryManager` uses both `MemoryStore` and `LLMProvider.chat()` with matching signature `(messages, system=..., max_tokens=..., temperature=...)`.
- **`LLMProvider.chat()` signature:** Takes `messages: list[dict]`, keyword args `tools`, `model`, `max_tokens`, `temperature`. `retrieval.py` calls it with `system=_SELECT_SYSTEM_PROMPT` — note: the actual `LLMProvider.chat()` signature does NOT have a `system` parameter; it should be prepended as a system message in `messages`. Fix: pass system prompt as first message with `role: system`.
