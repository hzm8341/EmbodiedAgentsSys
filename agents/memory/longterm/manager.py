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
    """Manager for long-term memory operations across global and project scopes."""

    def __init__(self, global_dir: Path, project_dir: Path, provider: "LLMProvider") -> None:
        """Initialize manager with separate global and project memory stores.

        Args:
            global_dir: Directory for global memories
            project_dir: Directory for project-specific memories
            provider: LLM provider for semantic retrieval
        """
        self._global = MemoryStore(global_dir)
        self._project = MemoryStore(project_dir)
        self._provider = provider

    async def recall(self, query: str, recent_tools: list[str] = []) -> list[str]:
        """Recall relevant memories for a query.

        Args:
            query: Query text to find relevant memories
            recent_tools: List of recently used tools (for context)

        Returns:
            List of memory contents in priority order (project first, then global)
        """
        already_surfaced: set[str] = set()
        project_mems = await find_relevant_memories(
            query, self._project, self._provider, recent_tools, already_surfaced
        )
        already_surfaced.update(m.path for m in project_mems)
        global_mems = await find_relevant_memories(
            query, self._global, self._provider, recent_tools, already_surfaced
        )
        return [m.content for m in project_mems + global_mems]

    def remember(self, name: str, type: MemoryType, description: str,
                 body: str, scope: str = "project") -> None:
        """Store a new memory.

        Args:
            name: Memory identifier
            type: Type of memory (FEEDBACK, REFERENCE, MISSION, ROBOT_CONFIG)
            description: Human-readable description
            body: Memory content
            scope: "project" or "global"
        """
        store = self._project if scope == "project" else self._global
        store.save(name, type, description, body)

    def forget(self, name: str, scope: str = "project") -> None:
        """Delete a memory.

        Args:
            name: Memory identifier
            scope: "project" or "global"
        """
        store = self._project if scope == "project" else self._global
        store.delete(name)

    def get_index(self, scope: str = "both") -> str:
        """Get memory index for a scope.

        Args:
            scope: "global", "project", or "both"

        Returns:
            Formatted index string
        """
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
