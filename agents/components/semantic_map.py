"""Semantic map — YAML-persisted storage of named locations and objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


__all__ = ["SemanticMap"]


class SemanticMap:
    """Persistent map of named locations and objects for LLM task planning.

    Locations map a human-readable name to robot-frame coordinates (x, y, theta).
    Objects map a name to the location where they were last observed.

    All list fields within a location or object entry are independent; there is
    no parallel-list constraint across the top-level dicts.

    YAML schema::

        locations:
          desk: {x: 1.2, y: 0.5, theta: 0.0}
        objects:
          cup: {location: desk, pos_3d: [1.2, 0.5, 0.85]}
    """

    def __init__(self, map_path: str = "config/semantic_map.yaml") -> None:
        self._path = Path(map_path)
        self._data: Dict[str, Any] = {"locations": {}, "objects": {}}
        if self._path.exists():
            self.load()

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    def add_location(self, name: str, x: float, y: float, theta: float) -> None:
        """Add or update a named location with robot-frame pose."""
        self._data["locations"][name] = {"x": x, "y": y, "theta": theta}

    def get_location(self, name: str) -> Optional[Dict[str, float]]:
        """Return pose dict for *name*, or None if unknown."""
        return self._data["locations"].get(name)

    def list_locations(self) -> List[str]:
        """Return all known location names."""
        return list(self._data["locations"].keys())

    # ------------------------------------------------------------------
    # Objects
    # ------------------------------------------------------------------

    def add_object(
        self,
        name: str,
        location: str,
        pos_3d: Optional[List[float]] = None,
    ) -> None:
        """Record an object's semantic location."""
        self._data["objects"][name] = {
            "location": location,
            "pos_3d": pos_3d if pos_3d is not None else [],
        }

    def get_object(self, name: str) -> Optional[Dict[str, Any]]:
        """Return object info dict, or None if unknown."""
        return self._data["objects"].get(name)

    def list_objects(self) -> List[str]:
        """Return all known object names."""
        return list(self._data["objects"].keys())

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Persist the map to the YAML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def load(self) -> None:
        """Load the map from the YAML file, replacing current state."""
        with open(self._path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        self._data["locations"] = loaded.get("locations", {})
        self._data["objects"] = loaded.get("objects", {})

    # ------------------------------------------------------------------
    # LLM prompt helper
    # ------------------------------------------------------------------

    def summary_for_prompt(self) -> str:
        """Return a concise map summary suitable for inclusion in an LLM prompt."""
        lines = ["Known locations:"]
        for name, coord in self._data["locations"].items():
            lines.append(f"  {name}: ({coord['x']:.1f}, {coord['y']:.1f})")
        if self._data["objects"]:
            lines.append("Known objects:")
            for name, info in self._data["objects"].items():
                lines.append(f"  {name} at {info['location']}")
        return "\n".join(lines)
