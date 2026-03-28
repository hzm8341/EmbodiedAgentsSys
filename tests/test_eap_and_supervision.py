"""Tests for EAP orchestrator, TrajectoryRecorder, and SubtaskMonitor."""

import asyncio
import tempfile
from pathlib import Path
import pytest

from agents.data.eap import EAPPhase, EAPTrajectory, Trajectory
from agents.data.eap_orchestrator import EAPConfig, EAPOrchestrator, EAPStats
from agents.training.trajectory_recorder import TrajectoryRecorder
from agents.components.subtask_monitor import (
    InterventionReason,
    MonitorConfig,
    SubtaskMonitor,
    SubtaskResult,
)


# ---------------------------------------------------------------------------
# EAP data structures
# ---------------------------------------------------------------------------

def test_trajectory_add_steps():
    traj = Trajectory(skill_id="grasp", phase=EAPPhase.FORWARD)
    traj.add_step({"image": [1, 2, 3]}, {"joint_angles": [0.0] * 6})
    traj.add_step({"image": [4, 5, 6]}, {"joint_angles": [0.1] * 6})
    assert traj.num_steps == 2


def test_trajectory_finalize():
    traj = Trajectory(skill_id="grasp", phase=EAPPhase.FORWARD)
    traj.finalize(success=True)
    assert traj.success
    assert traj.end_time != ""


def test_eap_trajectory_is_complete():
    traj = EAPTrajectory(skill_id="grasp", cycle_id=1)
    assert not traj.is_complete()
    traj.forward.success = True
    assert traj.is_complete()


def test_eap_trajectory_default_skill_ids():
    traj = EAPTrajectory(skill_id="manipulation.grasp", cycle_id=1)
    assert traj.forward.skill_id == "manipulation.grasp"
    assert traj.reverse.skill_id == "manipulation.grasp.reverse"


# ---------------------------------------------------------------------------
# EAPOrchestrator
# ---------------------------------------------------------------------------

def _make_skill_runner(success_sequence: list[bool]):
    """Returns a skill runner that succeeds/fails per the sequence."""
    call_count = [0]

    async def runner(skill_id: str, kwargs: dict) -> tuple[bool, list, list]:
        idx = min(call_count[0], len(success_sequence) - 1)
        success = success_sequence[idx]
        call_count[0] += 1
        obs = [{"obs": i} for i in range(3)] if success else []
        acts = [{"act": i} for i in range(3)] if success else []
        return success, obs, acts

    return runner


def test_eap_orchestrator_collects_target():
    config = EAPConfig(
        skill_id="grasp",
        reverse_skill_id="release",
        target_trajectories=3,
        max_forward_retries=1,
        max_reverse_retries=1,
    )
    runner = _make_skill_runner([True, True])  # always succeeds

    async def run():
        orch = EAPOrchestrator(config=config, skill_runner=runner)
        return await orch.run_collection_loop()

    trajectories, stats = asyncio.get_event_loop().run_until_complete(run())
    assert len(trajectories) == 3
    assert stats.successful_forward == 3
    assert stats.success_rate == 1.0


def test_eap_orchestrator_retries_and_calls_human():
    config = EAPConfig(
        skill_id="grasp",
        reverse_skill_id="release",
        target_trajectories=1,
        max_forward_retries=2,
        max_reverse_retries=2,
        max_failed_cycles=1,  # stop after 1 failed cycle
    )
    human_calls = []

    async def notifier(reason: str):
        human_calls.append(reason)

    runner = _make_skill_runner([False, False, False, False])  # always fails

    async def run():
        orch = EAPOrchestrator(
            config=config,
            skill_runner=runner,
            human_notifier=notifier,
        )
        return await orch.run_collection_loop()

    trajectories, stats = asyncio.get_event_loop().run_until_complete(run())
    # No successful trajectories
    assert len(trajectories) == 0
    assert stats.human_interventions > 0
    assert len(human_calls) > 0


def test_eap_orchestrator_callback():
    config = EAPConfig(
        skill_id="grasp",
        reverse_skill_id="release",
        target_trajectories=2,
        max_forward_retries=1,
        max_reverse_retries=1,
    )
    runner = _make_skill_runner([True, True])
    callbacks = []

    async def on_complete(traj: EAPTrajectory):
        callbacks.append(traj.cycle_id)

    async def run():
        orch = EAPOrchestrator(
            config=config,
            skill_runner=runner,
            on_trajectory_complete=on_complete,
        )
        return await orch.run_collection_loop()

    trajectories, stats = asyncio.get_event_loop().run_until_complete(run())
    assert len(callbacks) == 2
    assert callbacks == [1, 2]


def test_eap_stats_success_rate():
    stats = EAPStats(skill_id="grasp", cycles_attempted=10, successful_forward=7)
    assert stats.success_rate == pytest.approx(0.7)


def test_eap_stats_zero_division():
    stats = EAPStats(skill_id="grasp")
    assert stats.success_rate == 0.0


# ---------------------------------------------------------------------------
# TrajectoryRecorder
# ---------------------------------------------------------------------------

def _make_test_trajectory(success: bool = True, num_steps: int = 3) -> EAPTrajectory:
    traj = EAPTrajectory(skill_id="manipulation.grasp", cycle_id=1)
    for i in range(num_steps):
        traj.forward.add_step({"image": [i] * 3}, {"joint": [float(i)] * 6})
        traj.reverse.add_step({"image": [i + 10] * 3}, {"joint": [-float(i)] * 6})
    traj.forward.finalize(success=success)
    traj.reverse.finalize(success=True)
    return traj


def test_trajectory_recorder_save_eap():
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TrajectoryRecorder(data_dir=tmpdir)
        traj = _make_test_trajectory(success=True)

        async def run():
            return await recorder.save_eap_trajectory(traj)

        paths = asyncio.get_event_loop().run_until_complete(run())
        assert len(paths) == 2
        assert all(p.exists() for p in paths)
        assert any("forward" in str(p) for p in paths)
        assert any("reverse" in str(p) for p in paths)


def test_trajectory_recorder_load_episode():
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TrajectoryRecorder(data_dir=tmpdir)
        traj = _make_test_trajectory(success=True, num_steps=5)

        async def run():
            paths = await recorder.save_eap_trajectory(traj)
            forward_path = next(p for p in paths if "forward" in str(p))
            return await recorder.load_episode(forward_path)

        header, steps = asyncio.get_event_loop().run_until_complete(run())
        assert header["type"] == "episode_info"
        assert header["success"] is True
        assert header["num_steps"] == 5
        assert len(steps) == 5
        assert steps[0]["type"] == "step"
        assert "observation" in steps[0]
        assert "action" in steps[0]


def test_trajectory_recorder_save_deployment():
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TrajectoryRecorder(data_dir=tmpdir)
        obs = [{"image": [i] * 3} for i in range(4)]
        acts = [{"joint": [0.0] * 6} for _ in range(4)]

        async def run():
            return await recorder.save_deployment_trajectory(
                skill_id="manipulation.grasp",
                observations=obs,
                actions=acts,
                success=True,
                metadata={"robot_id": "arm_01"},
            )

        path = asyncio.get_event_loop().run_until_complete(run())
        assert path.exists()
        assert "deployment" in str(path)


def test_trajectory_recorder_count_episodes():
    with tempfile.TemporaryDirectory() as tmpdir:
        recorder = TrajectoryRecorder(data_dir=tmpdir)

        async def run():
            for i in range(3):
                traj = EAPTrajectory(skill_id="grasp", cycle_id=i + 1)
                traj.forward.add_step({"obs": i}, {"act": i})
                traj.forward.finalize(success=True)
                traj.reverse.finalize(success=True)
                await recorder.save_eap_trajectory(traj)

        asyncio.get_event_loop().run_until_complete(run())
        # 3 cycles × 1 file (forward only, reverse has no steps) = 3
        count = recorder.count_episodes("grasp", phase="eap")
        assert count == 3


# ---------------------------------------------------------------------------
# SubtaskMonitor
# ---------------------------------------------------------------------------

async def _successful_skill() -> bool:
    await asyncio.sleep(0.05)
    return True


async def _failing_skill() -> bool:
    await asyncio.sleep(0.05)
    return False


async def _slow_skill() -> bool:
    await asyncio.sleep(10.0)
    return True


def test_subtask_monitor_skill_success():
    monitor = SubtaskMonitor(config=MonitorConfig(poll_interval=0.01, max_duration=10.0))

    async def run():
        return await monitor.monitor_subtask(
            subtask_description="Test skill",
            skill_execution_coro=_successful_skill(),
        )

    result = asyncio.get_event_loop().run_until_complete(run())
    assert result.success
    assert result.intervention_reason == InterventionReason.SKILL_SUCCESS


def test_subtask_monitor_skill_failure():
    monitor = SubtaskMonitor(config=MonitorConfig(poll_interval=0.01, max_duration=10.0))

    async def run():
        return await monitor.monitor_subtask(
            subtask_description="Test skill",
            skill_execution_coro=_failing_skill(),
        )

    result = asyncio.get_event_loop().run_until_complete(run())
    assert not result.success
    assert result.intervention_reason == InterventionReason.SKILL_FAILURE


def test_subtask_monitor_timeout():
    monitor = SubtaskMonitor(config=MonitorConfig(poll_interval=0.05, max_duration=0.1))
    human_calls = []

    async def call_human(reason: str):
        human_calls.append(reason)

    monitor._call_human = call_human

    async def run():
        return await monitor.monitor_subtask(
            subtask_description="Long skill",
            skill_execution_coro=_slow_skill(),
        )

    result = asyncio.get_event_loop().run_until_complete(run())
    assert not result.success
    assert result.intervention_reason == InterventionReason.TIMEOUT
    assert len(human_calls) > 0


def test_subtask_monitor_joint_error():
    call_count = [0]

    async def bad_stats() -> dict:
        call_count[0] += 1
        if call_count[0] >= 2:
            return {"joint_errors": ["joint_3_overload"], "gripper_force": 0.0}
        return {"joint_errors": [], "gripper_force": 0.0}

    human_calls = []

    async def call_human(reason: str):
        human_calls.append(reason)

    monitor = SubtaskMonitor(
        fetch_robot_stats=bad_stats,
        call_human=call_human,
        config=MonitorConfig(poll_interval=0.02, max_duration=5.0, max_joint_errors=0),
    )

    async def run():
        return await monitor.monitor_subtask(
            subtask_description="Grasp",
            skill_execution_coro=_slow_skill(),
        )

    result = asyncio.get_event_loop().run_until_complete(run())
    assert not result.success
    assert result.intervention_reason == InterventionReason.JOINT_ERROR
    assert len(human_calls) > 0


def test_subtask_monitor_force_anomaly():
    async def high_force_stats() -> dict:
        return {"joint_errors": [], "gripper_force": 100.0}

    monitor = SubtaskMonitor(
        fetch_robot_stats=high_force_stats,
        config=MonitorConfig(poll_interval=0.02, max_duration=5.0, max_gripper_force=50.0),
    )

    async def run():
        return await monitor.monitor_subtask(
            subtask_description="Grasp with high force",
            skill_execution_coro=_slow_skill(),
        )

    result = asyncio.get_event_loop().run_until_complete(run())
    assert not result.success
    assert result.intervention_reason == InterventionReason.FORCE_ANOMALY
