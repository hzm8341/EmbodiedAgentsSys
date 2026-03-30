import pytest
from datetime import datetime
from agents.harness.core.evaluators.result_eval import ResultEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode


def _make_trace(status=TaskStatus.COMPLETED, skill_calls=None):
    return HarnessTrace(
        task_id="t1", session_id="s1",
        mode=HarnessMode.HARDWARE_MOCK,
        start_time=datetime.now(),
        final_status=status,
        skill_calls=skill_calls or [],
    )


def _make_task(expected_skills=None):
    return Task(task_id="t1", description="test", robot_type="arm",
                expected_skills=expected_skills or [])


def test_completed_task_full_skill_coverage():
    evaluator = ResultEvaluator()
    trace = _make_trace(
        status=TaskStatus.COMPLETED,
        skill_calls=["manipulation.reach", "manipulation.grasp", "manipulation.place"],
    )
    task = _make_task(["manipulation.reach", "manipulation.grasp", "manipulation.place"])
    score = evaluator.evaluate(trace, task)
    assert score.score == pytest.approx(1.0)
    assert score.passed is True


def test_failed_task_scores_zero():
    evaluator = ResultEvaluator()
    trace = _make_trace(status=TaskStatus.FAILED, skill_calls=[])
    task = _make_task(["manipulation.grasp"])
    score = evaluator.evaluate(trace, task)
    assert score.score == 0.0


def test_partial_skill_coverage():
    evaluator = ResultEvaluator()
    trace = _make_trace(
        status=TaskStatus.COMPLETED,
        skill_calls=["manipulation.grasp"],
    )
    task = _make_task(["manipulation.reach", "manipulation.grasp", "manipulation.place"])
    score = evaluator.evaluate(trace, task)
    assert score.score == pytest.approx(1/3, abs=0.01)


def test_no_expected_skills_full_score():
    evaluator = ResultEvaluator()
    trace = _make_trace(status=TaskStatus.COMPLETED)
    task = _make_task([])
    score = evaluator.evaluate(trace, task)
    assert score.score == pytest.approx(1.0)
