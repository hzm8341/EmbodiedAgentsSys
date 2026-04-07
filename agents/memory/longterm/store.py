# agents/memory/longterm/store.py
"""File-based memory storage."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from agents.memory.longterm.types import MemoryType, MemoryHeader, parse_frontmatter

MAX_MEMORY_FILES = 200
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000
ENTRYPOINT_NAME = "MEMORY.md"


class MemoryStore:
    def __init__(self, memory_dir: Path) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, type: MemoryType,
             description: str, body: str) -> Path:
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
        for path in self.memory_dir.glob("*.md"):
            if path.name == ENTRYPOINT_NAME:
                continue
            fm = parse_frontmatter(path.read_text(encoding="utf-8"))
            if fm.get("name") == name:
                path.unlink()
                self._rebuild_index()
                return

    def load(self, name: str) -> Optional[str]:
        for path in self.memory_dir.glob("*.md"):
            if path.name == ENTRYPOINT_NAME:
                continue
            content = path.read_text(encoding="utf-8")
            fm = parse_frontmatter(content)
            if fm.get("name") == name:
                return content
        return None

    def scan_files(self) -> list[MemoryHeader]:
        headers: list[MemoryHeader] = []
        paths = sorted(
            (p for p in self.memory_dir.glob("*.md") if p.name != ENTRYPOINT_NAME),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in paths[:MAX_MEMORY_FILES]:
            try:
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
