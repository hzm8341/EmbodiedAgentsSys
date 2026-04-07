from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional
import yaml
from agents.plugins.base import Plugin


class PluginRegistry:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._enabled: set[str] = set()
        self._config_path = config_path
        if config_path and Path(config_path).exists():
            self._load_config()

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.name] = plugin

    def enable(self, name: str) -> None:
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not registered")
        self._enabled.add(name)
        self._save_config()

    def disable(self, name: str) -> None:
        self._enabled.discard(name)
        self._save_config()

    def get_all(self) -> list[Plugin]:
        return list(self._plugins.values())

    def get_enabled(self) -> list[Plugin]:
        return [self._plugins[n] for n in self._enabled if n in self._plugins]

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    async def initialize_all(self) -> None:
        await asyncio.gather(*(p.initialize() for p in self.get_enabled()))

    async def shutdown_all(self) -> None:
        await asyncio.gather(*(p.shutdown() for p in self.get_enabled()))

    def _save_config(self) -> None:
        if not self._config_path:
            return
        Path(self._config_path).write_text(
            yaml.dump({"enabled_plugins": sorted(self._enabled)}), encoding="utf-8"
        )

    def _load_config(self) -> None:
        data = yaml.safe_load(Path(self._config_path).read_text(encoding="utf-8")) or {}
        self._enabled = set(data.get("enabled_plugins", []))
