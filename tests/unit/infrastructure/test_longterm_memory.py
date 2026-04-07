# tests/test_longterm_memory.py
import json
import pytest
from pathlib import Path
from agents.memory.longterm.types import MemoryType, MemoryHeader, parse_frontmatter
from agents.memory.longterm.store import MemoryStore, truncate_entrypoint


class TestParseFrontmatter:
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
        from agents.memory.longterm.types import MemoryType
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
        from agents.memory.longterm.types import MemoryType
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
        from agents.memory.longterm.types import MemoryType
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
        from agents.memory.longterm.store import MemoryStore
        from agents.memory.longterm.types import MemoryType
        mock_provider = MagicMock()
        mgr = LongTermMemoryManager(
            global_dir=tmp_path / "global",
            project_dir=tmp_path / "project",
            provider=mock_provider,
        )
        mgr.remember("temp", MemoryType.MISSION, "temp mission", "body", scope="project")
        mgr.forget("temp", scope="project")
        assert MemoryStore(tmp_path / "project").load("temp") is None

    def test_get_index_both(self, tmp_path):
        from agents.memory.longterm.manager import LongTermMemoryManager
        from agents.memory.longterm.types import MemoryType
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
