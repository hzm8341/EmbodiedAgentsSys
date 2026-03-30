import pytest
from datetime import datetime
from agents.harness.core.evaluators.explainability_eval import ExplainabilityEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, CoTDecisionRecord
from agents.harness.core.task_set import Task
from agents.harness.core.mode import HarnessMode


def _make_trace(mode=HarnessMode.REAL, cot_decisions=None):
    return HarnessTrace(
        task_id="t1", session_id="s1",
        mode=mode,
        start_time=datetime.now(),
        final_status=TaskStatus.COMPLETED,
        skill_calls=[],
        cot_decisions=cot_decisions or [],
    )


def _make_task():
    return Task(task_id="t1", description="test", robot_type="arm",
                expected_skills=["manipulation.grasp"])


def test_explainability_mock_mode_no_cot_returns_weight_zero():
    """Mock mode with no CoT decisions: weight=0, excluded from scoring."""
    evaluator = ExplainabilityEvaluator()
    trace = _make_trace(mode=HarnessMode.SKILL_MOCK, cot_decisions=[])
    score = evaluator.evaluate(trace, _make_task())
    assert score.weight == 0.0
    assert score.details.get("mode_aware") is True


def test_explainability_real_mode_with_cot():
    evaluator = ExplainabilityEvaluator()
    decisions = [
        CoTDecisionRecord(datetime.now(), "running", "skill",
                          "start_policy", {"skill_id": "manipulation.grasp"},
                          "grasp object first")
    ]
    trace = _make_trace(mode=HarnessMode.REAL, cot_decisions=decisions)
    score = evaluator.evaluate(trace, _make_task())
    assert score.weight == 0.25
    assert score.score > 0.0


def test_explainability_real_mode_no_cot_penalized():
    """Real mode with no CoT decisions is suspicious — penalize."""
    evaluator = ExplainabilityEvaluator()
    trace = _make_trace(mode=HarnessMode.REAL, cot_decisions=[])
    score = evaluator.evaluate(trace, _make_task())
    assert score.weight == 0.25
    assert score.score == pytest.approx(0.0)
