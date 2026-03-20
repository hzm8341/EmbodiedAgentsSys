"""RobotCapabilityRegistry — static YAML-backed skill registry (Phase 1)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import yaml


class GapType(Enum):
    NONE = "none"              # skill fully supported
    HARD = "hard"              # skill not registered for robot_type
    ADAPTER = "adapter"        # registered but no adapter implementation
    PERFORMANCE = "performance"  # adapter exists but below threshold


@dataclass
class CapabilityResult:
    skill_id: str
    robot_type: str
    gap_type: GapType
    reason: str = ""
    suggested_fallback: str | None = None


class RobotCapabilityRegistry:
    """Loads a YAML skill registry and answers capability queries.

    YAML format::

        skills:
          - id: manipulation.grasp
            robot_types: [arm, mobile_arm]
            description: "..."
    """

    def __init__(self, registry_yaml_path: str):
        self._skills: dict[str, list[str]] = {}  # skill_id → [robot_types]
        self._meta: dict[str, dict] = {}
        self._load(registry_yaml_path)

    def _load(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for entry in data.get("skills", []):
            sid = entry["id"]
            self._skills[sid] = entry.get("robot_types", [])
            self._meta[sid] = entry

    def register(self, skill_meta: dict) -> None:
        """Dynamically register a new skill (or overwrite existing)."""
        sid = skill_meta["id"]
        self._skills[sid] = skill_meta.get("robot_types", [])
        self._meta[sid] = skill_meta

    def query(self, skill_id: str, robot_type: str) -> CapabilityResult:
        """Return CapabilityResult for (skill_id, robot_type) pair."""
        if skill_id not in self._skills:
            return CapabilityResult(
                skill_id=skill_id,
                robot_type=robot_type,
                gap_type=GapType.HARD,
                reason=f"Skill '{skill_id}' not found in registry",
            )
        supported_types = self._skills[skill_id]
        if robot_type not in supported_types:
            return CapabilityResult(
                skill_id=skill_id,
                robot_type=robot_type,
                gap_type=GapType.HARD,
                reason=(
                    f"Skill '{skill_id}' does not support robot_type='{robot_type}'. "
                    f"Supported: {supported_types}"
                ),
            )
        return CapabilityResult(
            skill_id=skill_id,
            robot_type=robot_type,
            gap_type=GapType.NONE,
        )

    def update_performance(self, skill_id: str, metrics: dict) -> None:
        """Placeholder for Phase 2 performance tracking — no-op in Phase 1."""
        if skill_id in self._meta:
            self._meta[skill_id].setdefault("performance", {}).update(metrics)

    def list_gaps(
        self, plan_steps: list[dict], robot_type: str
    ) -> list[CapabilityResult]:
        """Return CapabilityResults with gap_type != NONE for each plan step."""
        gaps = []
        for step in plan_steps:
            skill_id = step.get("skill", "")
            if not skill_id:
                continue
            result = self.query(skill_id, robot_type)
            if result.gap_type != GapType.NONE:
                gaps.append(result)
        return gaps
