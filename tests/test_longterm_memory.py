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
