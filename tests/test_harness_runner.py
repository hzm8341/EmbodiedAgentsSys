# tests/test_harness_runner.py
import pytest
from agents.harness.runner import HarnessRunner
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode
from agents.harness.core.task_set import Task, TaskSet


def _make_simple_task_set():
    ts = TaskSet()
    ts.declarative.append(Task(
        task_id="run_test_001",
        description="test run",
        robot_type="arm",
        expected_skills=["manipulation.grasp"],
    ))
    return ts


def test_runner_creates_with_config():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    assert runner.config.mode == HarnessMode.SKILL_MOCK


def test_runner_evaluate_returns_reports():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    ts = _make_simple_task_set()
    reports = runner.evaluate(ts)
    assert len(reports) == 1
    assert reports[0].task_id == "run_test_001"
    assert 0.0 <= reports[0].total_score <= 1.0


def test_runner_summary_str():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    runner = HarnessRunner(config)
    ts = _make_simple_task_set()
    reports = runner.evaluate(ts)
    summary = runner.summary(reports)
    assert "run_test_001" in summary
    assert "PASS" in summary or "FAIL" in summary
