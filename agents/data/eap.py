"""Entangled Action Pairs (EAP) data structures.

Based on paper §3.2: each skill k forms an Entangled Action Pair
  τ_k = (τ_k→, τ_k←)

where:
  τ_k→  forward trajectory: executing the skill (pick up cup)
  τ_k←  reverse/reset trajectory: undoing the action (put cup back)

Together they form a closed loop that allows autonomous data collection
without human intervention to reset the environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EAPPhase(str, Enum):
    """Current phase of an EAP execution cycle."""
    FORWARD = "forward"   # executing the forward skill
    EVALUATE = "evaluate"  # checking if forward succeeded
    REVERSE = "reverse"   # executing the reset/reverse skill
    COMPLETE = "complete"  # cycle finished
    FAILED = "failed"     # unrecoverable failure, human needed


@dataclass
class Trajectory:
    """A single trajectory (forward OR reverse).

    Observations and actions are stored as raw dicts to remain
    format-agnostic. TrajectoryRecorder handles conversion to
    LeRobot-compatible datasets.
    """
    skill_id: str
    phase: EAPPhase  # FORWARD or REVERSE
    observations: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    success: bool = False
    start_time: str = ""
    end_time: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()

    def finalize(self, success: bool) -> None:
        self.success = success
        self.end_time = datetime.now(timezone.utc).isoformat()

    def add_step(
        self,
        observation: dict[str, Any],
        action: dict[str, Any],
    ) -> None:
        """Record one observation-action pair."""
        self.observations.append(observation)
        self.actions.append(action)

    @property
    def num_steps(self) -> int:
        return len(self.actions)


@dataclass
class EAPTrajectory:
    """A complete Entangled Action Pair: τ_k = (τ_k→, τ_k←).

    skill_id: the skill this pair trains (e.g. "manipulation.grasp")
    forward:  τ_k→  (executing the skill)
    reverse:  τ_k←  (resetting the environment)
    cycle_id: sequential cycle number within a collection run
    """
    skill_id: str
    cycle_id: int
    forward: Trajectory = field(default_factory=lambda: Trajectory("", EAPPhase.FORWARD))
    reverse: Trajectory = field(default_factory=lambda: Trajectory("", EAPPhase.REVERSE))
    overall_success: bool = False
    human_interventions: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.forward.skill_id:
            self.forward.skill_id = self.skill_id
        if not self.reverse.skill_id:
            self.reverse.skill_id = f"{self.skill_id}.reverse"

    def is_complete(self) -> bool:
        return self.forward.success  # reverse always runs; overall success = forward worked
