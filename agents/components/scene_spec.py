"""SceneSpec — structured task description filled via voice template or YAML."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

_REQUIRED_FIELDS = ("scene_type", "environment", "robot_type", "task_description")


@dataclass
class SceneSpec:
    """Structured description of a scene and task, produced by VoiceTemplateAgent."""
    scene_type: str           # e.g. "warehouse_pick", "assembly", "inspection"
    environment: str          # free-text environment description
    robot_type: str           # "arm" | "mobile" | "mobile_arm"
    task_description: str     # natural language task goal
    objects: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        d = {
            "scene_type": self.scene_type,
            "environment": self.environment,
            "robot_type": self.robot_type,
            "task_description": self.task_description,
            "objects": self.objects,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "metadata": self.metadata,
        }
        return yaml.dump(d, allow_unicode=True, default_flow_style=False)

    @classmethod
    def from_yaml(cls, text: str) -> SceneSpec:
        """Deserialize from YAML string."""
        d = yaml.safe_load(text)
        return cls.from_dict(d)

    @classmethod
    def from_dict(cls, d: dict) -> SceneSpec:
        """Construct from a plain dict; raises KeyError on missing required fields."""
        for key in _REQUIRED_FIELDS:
            if key not in d:
                raise KeyError(f"SceneSpec missing required field: '{key}'")
        return cls(
            scene_type=d["scene_type"],
            environment=d["environment"],
            robot_type=d["robot_type"],
            task_description=d["task_description"],
            objects=list(d.get("objects") or []),
            constraints=list(d.get("constraints") or []),
            success_criteria=list(d.get("success_criteria") or []),
            metadata=dict(d.get("metadata") or {}),
        )
