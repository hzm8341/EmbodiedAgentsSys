"""Process supervision — SubtaskMonitor.

Based on paper §3.3: during skill execution, the system periodically
queries robot/environment state and intervenes when the robot is stuck
or something has gone wrong. This achieves a 25% higher task success
rate vs. no supervision.

The monitor runs as an asyncio task alongside the skill execution coroutine.
It queries:
  - fetch_robot_stats: joint errors, gripper force, motion stall detection
  - env_summary: scene changes that indicate unexpected state

Intervention triggers:
  1. Joint error count exceeds threshold → terminate_policy + call_human
  2. Motion stall (position unchanged for > stall_timeout) → retry or call_human
  3. Gripper force anomaly → terminate_policy
  4. Max subtask duration exceeded → terminate_policy + call_human
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class InterventionReason(str, Enum):
    """Reason for process supervisor intervention."""
    JOINT_ERROR = "joint_error"
    MOTION_STALL = "motion_stall"
    FORCE_ANOMALY = "force_anomaly"
    TIMEOUT = "timeout"
    SKILL_SUCCESS = "skill_success"
    SKILL_FAILURE = "skill_failure"
    NO_INTERVENTION = "no_intervention"


@dataclass
class SubtaskResult:
    """Result of a monitored subtask execution."""
    success: bool
    intervention_reason: InterventionReason = InterventionReason.NO_INTERVENTION
    duration_seconds: float = 0.0
    robot_stats_at_end: dict[str, Any] = field(default_factory=dict)
    error_detail: str = ""


@dataclass
class MonitorConfig:
    """Configuration for SubtaskMonitor."""
    poll_interval: float = 2.0      # seconds between health checks
    max_duration: float = 120.0     # seconds before timeout intervention
    stall_timeout: float = 10.0     # seconds with no position change = stall
    max_joint_errors: int = 0       # any joint error triggers intervention
    max_gripper_force: float = 50.0 # N, exceeding = force anomaly


class SubtaskMonitor:
    """Monitors a skill execution and intervenes when the robot is stuck.

    The monitor wraps skill execution with a concurrent health-check loop.
    If intervention criteria are met, it cancels the skill and returns
    a SubtaskResult with the intervention reason.

    Usage:
        monitor = SubtaskMonitor(
            fetch_robot_stats=my_stats_fn,
            terminate_policy=my_terminate_fn,
            call_human=my_human_fn,
        )
        result = await monitor.monitor_subtask(
            subtask_description="Grasp the cup",
            skill_execution_coro=execute_grasp_skill(),
        )
    """

    def __init__(
        self,
        fetch_robot_stats: Callable[[], Awaitable[dict[str, Any]]] | None = None,
        terminate_policy: Callable[[], Awaitable[None]] | None = None,
        call_human: Callable[[str], Awaitable[None]] | None = None,
        config: MonitorConfig | None = None,
    ):
        self._fetch_stats = fetch_robot_stats or self._default_fetch_stats
        self._terminate = terminate_policy or self._default_terminate
        self._call_human = call_human or self._default_call_human
        self.config = config or MonitorConfig()
        self._last_position: dict[str, float] | None = None
        self._stall_start: float | None = None

    async def monitor_subtask(
        self,
        subtask_description: str,
        skill_execution_coro: Awaitable[bool],
    ) -> SubtaskResult:
        """Execute a skill with concurrent process supervision.

        Args:
            subtask_description: Human-readable description for logs.
            skill_execution_coro: Awaitable that returns True on success.

        Returns:
            SubtaskResult with success/failure and intervention details.
        """
        import time
        start_time = time.monotonic()

        skill_task = asyncio.ensure_future(skill_execution_coro)
        monitor_task = asyncio.ensure_future(
            self._monitor_loop(skill_task, subtask_description, start_time)
        )

        try:
            # Wait for either skill or monitor to finish first
            done, pending = await asyncio.wait(
                [skill_task, monitor_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            duration = time.monotonic() - start_time

            # Clean up pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

            # Determine result
            if skill_task in done and not skill_task.cancelled():
                try:
                    skill_success = skill_task.result()
                    stats = await self._fetch_stats()
                    return SubtaskResult(
                        success=bool(skill_success),
                        intervention_reason=(
                            InterventionReason.SKILL_SUCCESS
                            if skill_success else InterventionReason.SKILL_FAILURE
                        ),
                        duration_seconds=duration,
                        robot_stats_at_end=stats,
                    )
                except Exception as e:
                    return SubtaskResult(
                        success=False,
                        intervention_reason=InterventionReason.SKILL_FAILURE,
                        duration_seconds=duration,
                        error_detail=str(e),
                    )

            # Monitor triggered intervention
            if monitor_task in done and not monitor_task.cancelled():
                try:
                    return monitor_task.result()
                except Exception as e:
                    return SubtaskResult(
                        success=False,
                        intervention_reason=InterventionReason.NO_INTERVENTION,
                        duration_seconds=duration,
                        error_detail=str(e),
                    )

            # Both cancelled (shouldn't happen, but handle gracefully)
            return SubtaskResult(
                success=False,
                intervention_reason=InterventionReason.NO_INTERVENTION,
                duration_seconds=duration,
            )

        except asyncio.CancelledError:
            skill_task.cancel()
            monitor_task.cancel()
            raise

    async def _monitor_loop(
        self,
        skill_task: asyncio.Task,
        subtask_description: str,
        start_time: float,
    ) -> SubtaskResult:
        """Background health-check loop. Runs until skill finishes or intervention."""
        import time

        while not skill_task.done():
            await asyncio.sleep(self.config.poll_interval)

            if skill_task.done():
                break

            elapsed = time.monotonic() - start_time

            # Check timeout
            if elapsed > self.config.max_duration:
                logger.warning(
                    "Subtask timeout after %.1fs: %s",
                    elapsed, subtask_description,
                )
                skill_task.cancel()
                await self._terminate()
                await self._call_human(
                    f"Subtask timed out after {elapsed:.0f}s: {subtask_description}"
                )
                stats = await self._fetch_stats()
                return SubtaskResult(
                    success=False,
                    intervention_reason=InterventionReason.TIMEOUT,
                    duration_seconds=elapsed,
                    robot_stats_at_end=stats,
                    error_detail=f"timeout after {elapsed:.1f}s",
                )

            # Fetch robot health
            try:
                stats = await self._fetch_stats()
            except Exception as e:
                logger.warning("fetch_robot_stats error: %s", e)
                continue

            # Check joint errors
            joint_errors = stats.get("joint_errors", [])
            if len(joint_errors) > self.config.max_joint_errors:
                logger.warning("Joint errors detected: %s", joint_errors)
                skill_task.cancel()
                await self._terminate()
                await self._call_human(f"Joint errors: {joint_errors}")
                return SubtaskResult(
                    success=False,
                    intervention_reason=InterventionReason.JOINT_ERROR,
                    duration_seconds=elapsed,
                    robot_stats_at_end=stats,
                    error_detail=f"joint errors: {joint_errors}",
                )

            # Check gripper force anomaly
            gripper_force = stats.get("gripper_force", 0.0)
            if gripper_force > self.config.max_gripper_force:
                logger.warning("Gripper force anomaly: %.1fN", gripper_force)
                skill_task.cancel()
                await self._terminate()
                return SubtaskResult(
                    success=False,
                    intervention_reason=InterventionReason.FORCE_ANOMALY,
                    duration_seconds=elapsed,
                    robot_stats_at_end=stats,
                    error_detail=f"gripper force {gripper_force:.1f}N > {self.config.max_gripper_force}N",
                )

            # Check motion stall
            if await self._check_stall(stats, elapsed):
                logger.warning("Motion stall detected at %.1fs", elapsed)
                skill_task.cancel()
                await self._terminate()
                await self._call_human(f"Motion stall detected: {subtask_description}")
                return SubtaskResult(
                    success=False,
                    intervention_reason=InterventionReason.MOTION_STALL,
                    duration_seconds=elapsed,
                    robot_stats_at_end=stats,
                    error_detail="motion stall detected",
                )

        # Skill finished — return a no-intervention placeholder
        # (caller handles actual skill result from skill_task.result())
        return SubtaskResult(
            success=True,
            intervention_reason=InterventionReason.NO_INTERVENTION,
        )

    async def _check_stall(self, stats: dict[str, Any], elapsed: float) -> bool:
        """Return True if robot position has not changed beyond threshold."""
        import time
        position = stats.get("joint_positions")
        if not position:
            return False

        if self._last_position is None:
            self._last_position = position
            self._stall_start = time.monotonic()
            return False

        # Check if position changed
        moved = any(
            abs(position.get(k, 0) - self._last_position.get(k, 0)) > 0.01
            for k in position
        )

        if moved:
            self._last_position = position
            self._stall_start = time.monotonic()
            return False

        # Position unchanged — check stall timeout
        stall_duration = time.monotonic() - (self._stall_start or elapsed)
        return stall_duration > self.config.stall_timeout

    # Default stub implementations (replaced in production by tool registry calls)

    @staticmethod
    async def _default_fetch_stats() -> dict[str, Any]:
        return {"joint_errors": [], "gripper_force": 0.0}

    @staticmethod
    async def _default_terminate() -> None:
        logger.info("[stub] terminate_policy called")

    @staticmethod
    async def _default_call_human(reason: str) -> None:
        logger.warning("[stub] call_human: %s", reason)
