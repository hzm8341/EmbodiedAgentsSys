from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


class MCPAuthStore:
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
