"""PlanGenerator — wraps TaskPlanner to emit dot-notation YAML + Markdown plans."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import yaml

from .scene_spec import SceneSpec
from .task_planner import TaskPlanner, _SKILL_NAMESPACE_MAP
from ..hardware.capability_registry import RobotCapabilityRegistry
from ..hardware.gap_detector import GapDetectionEngine


@dataclass
class ExecutionPlan:
    """Dual-format execution plan: YAML machine-readable + Markdown human-readable."""
    plan_id: str
    scene_spec: SceneSpec
    steps: list[dict]                        # annotated with status, skill (dot-notation)
    capability_gaps: list[str] = field(default_factory=list)  # informational
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_yaml(self) -> str:
        """Serialize to YAML execution plan string."""
        d = {
            "plan_id": self.plan_id,
            "scene_spec_ref": self.scene_spec.scene_type,
            "created_at": self.created_at,
            "status": self.status,
            "capability_gaps": self.capability_gaps,
            "steps": self.steps,
        }
        return yaml.dump(d, allow_unicode=True, default_flow_style=False)

    def to_markdown(self) -> str:
        """Render human-readable Markdown technical report."""
        lines = [
            "# 技术方案报告",
            "",
            f"**Plan ID:** `{self.plan_id}`  ",
            f"**创建时间:** {self.created_at}  ",
            f"**场景类型:** {self.scene_spec.scene_type}  ",
            f"**机器人类型:** {self.scene_spec.robot_type}  ",
            f"**任务描述:** {self.scene_spec.task_description}",
            "",
            "## 执行步骤",
            "",
        ]
        for i, step in enumerate(self.steps, 1):
            status_badge = "⚠️ GAP" if step.get("status") == "gap" else "✅"
            params_str = ", ".join(
                f"{k}={v}" for k, v in (step.get("params") or {}).items()
            )
            lines.append(
                f"{i}. {status_badge} **{step['skill']}**"
                + (f" ({params_str})" if params_str else "")
            )
        if self.capability_gaps:
            lines += ["", "## 能力缺口 (Capability Gaps)", ""]
            for gap in self.capability_gaps:
                lines.append(f"- ⚠️ {gap}")
        return "\n".join(lines)


class PlanGenerator:
    """Generates dual-format execution plans from a SceneSpec.

    Internally uses TaskPlanner (mock or ollama) and maps flat actions
    to dot-notation skill IDs via _SKILL_NAMESPACE_MAP.
    """

    def __init__(
        self,
        registry_yaml_path: str,
        ollama_model: str = "qwen2.5:3b",
        backend: str = "ollama",
    ):
        self._planner = TaskPlanner(ollama_model=ollama_model, backend=backend)
        self._registry = RobotCapabilityRegistry(registry_yaml_path)
        self._gap_engine = GapDetectionEngine(self._registry)

    async def generate(self, scene: SceneSpec) -> ExecutionPlan:
        """Generate an ExecutionPlan for the given SceneSpec."""
        task_plan = await self._planner.plan(scene.task_description)

        # Convert flat actions → dot-notation steps
        raw_steps = []
        for action in task_plan.actions:
            skill_id = _SKILL_NAMESPACE_MAP.get(action.action, action.action)
            raw_steps.append({
                "step_id": str(len(raw_steps) + 1),
                "skill": skill_id,
                "params": {
                    "target": action.target,
                    **({"location": action.location} if action.location else {}),
                },
            })

        # Annotate steps with gap status
        annotated = self._gap_engine.annotate_steps(raw_steps, scene.robot_type)

        # Build capability_gaps list (informational)
        gap_report = self._gap_engine.detect(raw_steps, scene.robot_type)
        cap_gaps = [
            f"{g.skill_id}: {g.reason}" for g in gap_report.hard_gaps
        ]

        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            scene_spec=scene,
            steps=annotated,
            capability_gaps=cap_gaps,
        )
