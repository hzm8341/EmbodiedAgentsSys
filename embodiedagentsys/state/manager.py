"""State manager with optional disk persistence."""

from pathlib import Path
from typing import Optional

from embodiedagentsys.state.types import ProtocolType, StateEntry


class StateManager:
    """Manages state protocols with optional disk persistence."""

    def __init__(
        self,
        workspace_path: Optional[Path] = None,
        enable_state_files: bool = False
    ):
        self._workspace = workspace_path or Path.home() / ".embodiedagents" / "workspace"
        self._enable_files = enable_state_files
        self._memory_cache: dict[ProtocolType, dict] = {}

    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def enable_files(self) -> bool:
        return self._enable_files

    def write_protocol(self, protocol_type: ProtocolType, content: dict) -> None:
        """Write state to protocol."""
        self._memory_cache[protocol_type] = content
        if self._enable_files:
            self._write_to_disk(protocol_type, content)

    def read_protocol(self, protocol_type: ProtocolType) -> dict:
        """Read state from protocol."""
        if self._enable_files:
            return self._read_from_disk(protocol_type)
        return self._memory_cache.get(protocol_type, {})

    def get_entry(self, protocol_type: ProtocolType, updated_by: str = "system") -> StateEntry:
        """Get StateEntry for current state."""
        content = self.read_protocol(protocol_type)
        return StateEntry(
            protocol_type=protocol_type,
            content=content,
            updated_by=updated_by,
        )

    def _write_to_disk(self, protocol_type: ProtocolType, content: dict) -> None:
        """Write content to disk as JSON."""
        import json
        self._workspace.mkdir(parents=True, exist_ok=True)
        filename = self._get_filename(protocol_type)
        filepath = self._workspace / filename
        with open(filepath, 'w') as f:
            json.dump(content, f, indent=2)

    def _read_from_disk(self, protocol_type: ProtocolType) -> dict:
        """Read content from disk."""
        import json
        filepath = self._workspace / self._get_filename(protocol_type)
        if not filepath.exists():
            return {}
        with open(filepath, 'r') as f:
            return json.load(f)

    def _get_filename(self, protocol_type: ProtocolType) -> str:
        """Get filename for protocol type."""
        return f"{protocol_type.value.upper()}.json"
