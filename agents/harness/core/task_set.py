from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SceneObject:
    id: str
    type: str
    color: str = ""
    initial_position: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    size: list = field(default_factory=lambda: [0.05, 0.05, 0.05])


@dataclass
class ResultCriteria:
    type: str = "position_match"
    object: str = ""
    target: str = ""
    tolerance: float = 0.02


@dataclass
class EfficiencyCriteria:
    max_duration_seconds: int = 30


@dataclass
class RobustnessCriteria:
    max_retry_count: int = 2
    allowed_failures: list = field(default_factory=list)


@dataclass
class SuccessCriteria:
    result: ResultCriteria = field(default_factory=ResultCriteria)
    efficiency: EfficiencyCriteria = field(default_factory=EfficiencyCriteria)
    robustness: RobustnessCriteria = field(default_factory=RobustnessCriteria)


@dataclass
class Task:
    task_id: str
    description: str
    robot_type: str
    scene_objects: list[SceneObject] = field(default_factory=list)
    expected_skills: list[str] = field(default_factory=list)
    success_criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    is_regression: bool = False
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        raw_objects = data.get("scene", {}).get("objects", [])
        objects = [SceneObject(**obj) for obj in raw_objects]

        sc = data.get("success_criteria", {})
        criteria = SuccessCriteria(
            result=ResultCriteria(**sc.get("result", {})),
            efficiency=EfficiencyCriteria(**sc.get("efficiency", {})),
            robustness=RobustnessCriteria(**sc.get("robustness", {})),
        )
        return cls(
            task_id=data["task_id"],
            description=data.get("description", ""),
            robot_type=data.get("robot_type", "arm"),
            scene_objects=objects,
            expected_skills=data.get("expected_skills", []),
            success_criteria=criteria,
            is_regression=data.get("is_regression", False),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "robot_type": self.robot_type,
            "scene": {"objects": [o.__dict__ for o in self.scene_objects]},
            "expected_skills": self.expected_skills,
            "success_criteria": {
                "result": self.success_criteria.result.__dict__,
                "efficiency": self.success_criteria.efficiency.__dict__,
                "robustness": self.success_criteria.robustness.__dict__,
            },
            "is_regression": self.is_regression,
            "tags": self.tags,
        }


@dataclass          # 关键修复：必须有 @dataclass，否则 field() 不生效
class TaskSet:
    declarative: list[Task] = field(default_factory=list)
    regression: list[Task] = field(default_factory=list)
    custom: list[Task] = field(default_factory=list)

    def all_tasks(self) -> list[Task]:
        return self.declarative + self.regression + self.custom

    def filter(self, tags: list[str]) -> "TaskSet":
        tag_set = set(tags)
        return TaskSet(
            declarative=[t for t in self.declarative if tag_set & set(t.tags)],
            regression=[t for t in self.regression if tag_set & set(t.tags)],
            custom=[t for t in self.custom if tag_set & set(t.tags)],
        )

    def merge(self, other: "TaskSet") -> "TaskSet":
        return TaskSet(
            declarative=self.declarative + other.declarative,
            regression=self.regression + other.regression,
            custom=self.custom + other.custom,
        )
