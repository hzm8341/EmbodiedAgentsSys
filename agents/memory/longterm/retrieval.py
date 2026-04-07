# agents/memory/longterm/retrieval.py
"""Semantic memory retrieval."""
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
    """Find relevant memories for a query using LLM selection."""
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
