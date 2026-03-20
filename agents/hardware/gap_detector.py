"""GapDetectionEngine — Phase 1 hard-gap-only classifier."""
from __future__ import annotations

from dataclasses import dataclass, field

from .capability_registry import GapType, CapabilityResult, RobotCapabilityRegistry


@dataclass
class GapReport:
    """Result of a gap detection pass over a plan's steps."""
    hard_gaps: list[CapabilityResult] = field(default_factory=list)
    adapter_gaps: list[CapabilityResult] = field(default_factory=list)
    performance_gaps: list[CapabilityResult] = field(default_factory=list)

    @property
    def has_gaps(self) -> bool:
        return bool(self.hard_gaps or self.adapter_gaps or self.performance_gaps)

    def summary(self) -> str:
        lines = []
        for gap in self.hard_gaps:
            lines.append(f"[hard] {gap.skill_id}: {gap.reason}")
        for gap in self.adapter_gaps:
            lines.append(f"[adapter] {gap.skill_id}: {gap.reason}")
        for gap in self.performance_gaps:
            lines.append(f"[performance] {gap.skill_id}: {gap.reason}")
        return "\n".join(lines) if lines else "No gaps detected."


class GapDetectionEngine:
    """Classifies plan steps as supported or gap, annotates with status field."""

    def __init__(self, registry: RobotCapabilityRegistry):
        self._registry = registry

    def detect(self, plan_steps: list[dict], robot_type: str) -> GapReport:
        """Run gap detection over all plan steps.

        Returns a GapReport bucketing gaps by type.
        """
        report = GapReport()
        for step in plan_steps:
            skill_id = step.get("skill", "")
            if not skill_id:
                continue
            result = self._registry.query(skill_id, robot_type)
            if result.gap_type == GapType.HARD:
                report.hard_gaps.append(result)
            elif result.gap_type == GapType.ADAPTER:
                report.adapter_gaps.append(result)
            elif result.gap_type == GapType.PERFORMANCE:
                report.performance_gaps.append(result)
        return report

    def annotate_steps(self, plan_steps: list[dict], robot_type: str) -> list[dict]:
        """Return a copy of plan_steps with 'status' set to 'gap' or 'pending'."""
        gap_skills = {
            r.skill_id
            for r in self._registry.list_gaps(plan_steps, robot_type)
        }
        annotated = []
        for step in plan_steps:
            s = dict(step)
            s["status"] = "gap" if s.get("skill", "") in gap_skills else "pending"
            annotated.append(s)
        return annotated
