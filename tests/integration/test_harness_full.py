"""Full integration test: TaskLoader → HarnessRunner → ScoreReport."""
import pytest
from pathlib import Path
from agents.harness import HarnessRunner, HarnessConfig, TaskSet, Task
from agents.harness.core.mode import HarnessMode


def test_full_pipeline_skill_mock():
    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    config.skill_mock.default_success_rate = 1.0  # ensure all skills succeed

    ts = TaskSet()
    ts.declarative.append(Task(
        task_id="full_test_001",
        description="full pipeline test",
        robot_type="arm",
        expected_skills=["manipulation.reach", "manipulation.grasp"],
    ))

    runner = HarnessRunner(config)
    reports = runner.evaluate(ts)
    assert len(reports) == 1
    r = reports[0]
    assert r.task_id == "full_test_001"
    assert r.total_score > 0.0
    print("\n" + runner.summary(reports))


def test_full_pipeline_loads_yaml_tasks():
    from agents.harness.core.task_loader import TaskLoader
    tasks_dir = Path("agents/harness/tasks")
    if not tasks_dir.exists():
        pytest.skip("tasks dir not found")
    loader = TaskLoader()
    ts = loader.load_from_dir(tasks_dir)
    assert len(ts.declarative) >= 1

    config = HarnessConfig(mode=HarnessMode.SKILL_MOCK)
    config.skill_mock.default_success_rate = 0.9
    runner = HarnessRunner(config)
    reports = runner.evaluate(ts)
    assert len(reports) == len(ts.declarative)
    for r in reports:
        assert 0.0 <= r.total_score <= 1.0
