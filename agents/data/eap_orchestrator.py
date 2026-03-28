"""EAP Orchestrator — autonomous data collection via Entangled Action Pairs.

Based on paper §3.2. The orchestrator alternates:
  1. Forward pass  (τ_k→): run the skill, observe + record
  2. Evaluate: did the skill succeed?
  3. Reverse pass (τ_k←): reset environment to initial state
  4. Repeat until target_trajectories collected or max_failures reached.

When forward or reverse fails beyond retry threshold, escalates to
Call Human (paper §3.1 MCP tool).

Paper results: 8.04× reduction in human interventions vs. baseline.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from agents.data.eap import EAPPhase, EAPTrajectory, Trajectory

logger = logging.getLogger(__name__)

# Type aliases
SkillRunner = Callable[[str, dict[str, Any]], Awaitable[tuple[bool, list[dict], list[dict]]]]
"""Async function: (skill_id, kwargs) → (success, observations, actions)"""

HumanNotifier = Callable[[str], Awaitable[None]]
"""Async function: (reason) → None"""


@dataclass
class EAPConfig:
    """Configuration for an EAP data collection run."""
    skill_id: str               # forward skill to collect data for
    reverse_skill_id: str       # reset skill (often the inverse action)
    target_trajectories: int = 50   # number of successful forward trajectories to collect
    max_forward_retries: int = 3    # retries before calling human (forward)
    max_reverse_retries: int = 3    # retries before calling human (reverse)
    max_failed_cycles: int = 20     # stop after this many consecutive failed cycles
    observation_kwargs: dict[str, Any] = field(default_factory=dict)
    forward_kwargs: dict[str, Any] = field(default_factory=dict)
    reverse_kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class EAPStats:
    """Statistics from a completed EAP collection run."""
    skill_id: str
    cycles_attempted: int = 0
    successful_forward: int = 0
    successful_reverse: int = 0
    human_interventions: int = 0
    total_steps_collected: int = 0

    @property
    def success_rate(self) -> float:
        if self.cycles_attempted == 0:
            return 0.0
        return self.successful_forward / self.cycles_attempted

    def __str__(self) -> str:
        return (
            f"EAP[{self.skill_id}]: "
            f"{self.successful_forward}/{self.cycles_attempted} cycles, "
            f"{self.human_interventions} human calls, "
            f"success_rate={self.success_rate:.1%}"
        )


class EAPOrchestrator:
    """Orchestrates autonomous EAP data collection.

    Usage:
        orchestrator = EAPOrchestrator(
            config=EAPConfig(skill_id="grasp", reverse_skill_id="release"),
            skill_runner=my_skill_runner,
        )
        trajectories, stats = await orchestrator.run_collection_loop()

    The skill_runner is the integration point with the robot's skill execution
    system (VLA policy pool, LeRobot, etc.).
    """

    def __init__(
        self,
        config: EAPConfig,
        skill_runner: SkillRunner,
        human_notifier: HumanNotifier | None = None,
        on_trajectory_complete: Callable[[EAPTrajectory], Awaitable[None]] | None = None,
    ):
        self.config = config
        self._skill_runner = skill_runner
        self._human_notifier = human_notifier
        self._on_trajectory_complete = on_trajectory_complete
        self._running = False

    async def run_collection_loop(self) -> tuple[list[EAPTrajectory], EAPStats]:
        """Run the EAP collection loop until target trajectories are collected.

        Returns:
            (collected_trajectories, stats)
        """
        stats = EAPStats(skill_id=self.config.skill_id)
        collected: list[EAPTrajectory] = []
        self._running = True

        logger.info(
            "EAP collection started: skill=%s, target=%d",
            self.config.skill_id, self.config.target_trajectories,
        )

        cycle_id = 0
        failed_cycles = 0
        while self._running and len(collected) < self.config.target_trajectories:
            cycle_id += 1
            stats.cycles_attempted += 1

            traj = EAPTrajectory(
                skill_id=self.config.skill_id,
                cycle_id=cycle_id,
            )

            # --- Forward pass (τ_k→) ---
            forward_ok = await self._run_phase_with_retry(
                traj=traj,
                phase=EAPPhase.FORWARD,
                skill_id=self.config.skill_id,
                skill_kwargs=self.config.forward_kwargs,
                max_retries=self.config.max_forward_retries,
                stats=stats,
            )

            if forward_ok:
                stats.successful_forward += 1
                traj.overall_success = True
                stats.total_steps_collected += traj.forward.num_steps

            # --- Reverse pass (τ_k←) — always runs to reset environment ---
            reverse_ok = await self._run_phase_with_retry(
                traj=traj,
                phase=EAPPhase.REVERSE,
                skill_id=self.config.reverse_skill_id,
                skill_kwargs=self.config.reverse_kwargs,
                max_retries=self.config.max_reverse_retries,
                stats=stats,
            )

            if reverse_ok:
                stats.successful_reverse += 1
                stats.total_steps_collected += traj.reverse.num_steps

            # --- Record completed trajectory or count failure ---
            if forward_ok:
                failed_cycles = 0
                collected.append(traj)
                if self._on_trajectory_complete:
                    try:
                        await self._on_trajectory_complete(traj)
                    except Exception as e:
                        logger.warning("on_trajectory_complete callback error: %s", e)

            if not forward_ok:
                failed_cycles += 1
                if failed_cycles >= self.config.max_failed_cycles:
                    logger.warning(
                        "EAP stopping: %d consecutive failed cycles (max=%d)",
                        failed_cycles, self.config.max_failed_cycles,
                    )
                    break

            logger.info(
                "EAP cycle %d: forward=%s reverse=%s collected=%d/%d",
                cycle_id, forward_ok, reverse_ok,
                len(collected), self.config.target_trajectories,
            )

        self._running = False
        logger.info("EAP collection complete: %s", stats)
        return collected, stats

    def stop(self) -> None:
        """Stop the collection loop after the current cycle."""
        self._running = False

    async def _run_phase_with_retry(
        self,
        traj: EAPTrajectory,
        phase: EAPPhase,
        skill_id: str,
        skill_kwargs: dict[str, Any],
        max_retries: int,
        stats: EAPStats,
    ) -> bool:
        """Run a skill phase (forward or reverse) with retry on failure.

        Returns True if the phase eventually succeeded.
        """
        trajectory = traj.forward if phase == EAPPhase.FORWARD else traj.reverse
        trajectory.phase = phase
        trajectory.skill_id = skill_id

        for attempt in range(1, max_retries + 1):
            logger.debug(
                "EAP %s attempt %d/%d: %s",
                phase.value, attempt, max_retries, skill_id,
            )
            try:
                success, observations, actions = await self._skill_runner(
                    skill_id, skill_kwargs
                )
            except Exception as e:
                logger.warning("Skill runner error (%s): %s", skill_id, e)
                success, observations, actions = False, [], []

            for obs, act in zip(observations, actions):
                trajectory.add_step(obs, act)

            if success:
                trajectory.finalize(success=True)
                return True

            if attempt < max_retries:
                logger.info(
                    "EAP %s failed (attempt %d/%d), retrying...",
                    phase.value, attempt, max_retries,
                )

        # All retries exhausted — call human
        trajectory.finalize(success=False)
        traj.human_interventions += 1
        stats.human_interventions += 1
        reason = (
            f"EAP {phase.value} phase failed after {max_retries} attempts "
            f"(skill={skill_id}, cycle={traj.cycle_id})"
        )
        logger.warning("Calling human: %s", reason)
        if self._human_notifier:
            try:
                await self._human_notifier(reason)
            except Exception as e:
                logger.error("Human notifier error: %s", e)

        return False
