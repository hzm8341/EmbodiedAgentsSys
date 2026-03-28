"""Trajectory Recorder — saves EAP and deployment trajectories.

Outputs LeRobot-compatible NDJSON files that can be loaded by the
training pipeline. Each episode is one NDJSON file with header + steps.

Format (LeRobot-compatible):
  Line 0: {"type": "episode_info", "skill_id": ..., "success": ..., ...}
  Line N: {"type": "step", "observation": {...}, "action": {...}, "step": N}

This is an append-friendly format that avoids loading large HDF5 files
during collection. The training script converts these to HuggingFace
datasets as a post-processing step.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.data.eap import EAPTrajectory, EAPPhase

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = Path("data/trajectories")


class TrajectoryRecorder:
    """Records robot trajectories in LeRobot-compatible NDJSON format.

    EAP trajectories: saved as forward + reverse files under
      data/trajectories/eap/{skill_id}/episode_{cycle_id:06d}_{phase}.ndjson

    Deployment trajectories: saved under
      data/trajectories/deployment/{skill_id}/episode_{timestamp}.ndjson
    """

    def __init__(self, data_dir: Path | str = _DEFAULT_DATA_DIR):
        self._data_dir = Path(data_dir)

    async def save_eap_trajectory(self, traj: EAPTrajectory) -> list[Path]:
        """Save both forward and reverse trajectories from an EAP cycle.

        Returns list of paths written (up to 2).
        """
        paths = []
        for trajectory, phase_name in [
            (traj.forward, "forward"),
            (traj.reverse, "reverse"),
        ]:
            if not trajectory.observations and not trajectory.actions:
                continue  # skip empty trajectories

            out_dir = self._data_dir / "eap" / traj.skill_id
            filename = f"episode_{traj.cycle_id:06d}_{phase_name}.ndjson"
            path = out_dir / filename

            header = {
                "type": "episode_info",
                "skill_id": trajectory.skill_id,
                "phase": phase_name,
                "cycle_id": traj.cycle_id,
                "success": trajectory.success,
                "num_steps": trajectory.num_steps,
                "start_time": trajectory.start_time,
                "end_time": trajectory.end_time,
                "human_interventions": traj.human_interventions,
                "metadata": trajectory.metadata,
            }
            steps = [
                {
                    "type": "step",
                    "step": i,
                    "observation": obs,
                    "action": act,
                }
                for i, (obs, act) in enumerate(
                    zip(trajectory.observations, trajectory.actions)
                )
            ]

            await self._write_ndjson(path, [header] + steps)
            paths.append(path)

        return paths

    async def save_deployment_trajectory(
        self,
        skill_id: str,
        observations: list[dict[str, Any]],
        actions: list[dict[str, Any]],
        success: bool,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save a deployment trajectory (collected during real task execution).

        These are used for online learning — each successful real deployment
        generates training data that feeds back into the VLA policy.

        Returns path of written file.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        out_dir = self._data_dir / "deployment" / skill_id
        path = out_dir / f"episode_{timestamp}.ndjson"

        header = {
            "type": "episode_info",
            "skill_id": skill_id,
            "phase": "deployment",
            "success": success,
            "num_steps": len(actions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        steps = [
            {
                "type": "step",
                "step": i,
                "observation": obs,
                "action": act,
            }
            for i, (obs, act) in enumerate(zip(observations, actions))
        ]

        await self._write_ndjson(path, [header] + steps)
        return path

    async def _write_ndjson(self, path: Path, records: list[dict[str, Any]]) -> None:
        """Write records as newline-delimited JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(r, ensure_ascii=False) for r in records]
        content = "\n".join(lines) + "\n"
        await asyncio.to_thread(path.write_text, content, "utf-8")
        logger.debug("Saved trajectory: %s (%d steps)", path, len(records) - 1)

    async def list_episodes(self, skill_id: str, phase: str = "eap") -> list[Path]:
        """List all trajectory files for a given skill and phase."""
        base = self._data_dir / phase / skill_id
        if not base.exists():
            return []
        return sorted(base.glob("*.ndjson"))

    async def load_episode(self, path: Path) -> tuple[dict, list[dict]]:
        """Load an episode file. Returns (header, steps)."""
        content = await asyncio.to_thread(path.read_text, "utf-8")
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            return {}, []
        header = json.loads(lines[0])
        steps = [json.loads(l) for l in lines[1:]]
        return header, steps

    def count_episodes(self, skill_id: str, phase: str = "eap") -> int:
        """Count existing episodes for a skill (synchronous, for quick checks)."""
        base = self._data_dir / phase / skill_id
        if not base.exists():
            return 0
        return len(list(base.glob("*.ndjson")))
