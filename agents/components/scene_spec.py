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

    @classmethod
    def from_partial(cls, data: dict) -> "SceneSpec":
        """从部分字段构造 SceneSpec，缺失必填字段设为空字符串/空列表。

        与 from_dict() 不同：不抛 KeyError，而是允许缺失字段。
        """
        return cls(
            scene_type=data.get("scene_type", ""),
            environment=data.get("environment", ""),
            robot_type=data.get("robot_type", ""),
            task_description=data.get("task_description", ""),
            objects=list(data.get("objects") or []),
            constraints=list(data.get("constraints") or []),
            success_criteria=list(data.get("success_criteria") or []),
            metadata=dict(data.get("metadata") or {}),
        )

    def is_complete(self) -> bool:
        """检查所有必填字段是否非空。"""
        return all(
            bool(getattr(self, f, ""))
            for f in ("scene_type", "environment", "robot_type", "task_description")
        )

    def missing_fields(self) -> list[str]:
        """返回缺失（空）的必填字段名称列表。"""
        required = ("scene_type", "environment", "robot_type", "task_description")
        return [f for f in required if not bool(getattr(self, f, ""))]
