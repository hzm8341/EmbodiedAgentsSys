import pytest
from datetime import datetime, timedelta
from agents.harness.core.evaluators.efficiency_eval import EfficiencyEvaluator
from agents.harness.core.evaluators.robustness_eval import RobustnessEvaluator
from agents.harness.core.tracer import HarnessTrace, TaskStatus, ToolCallRecord
from agents.harness.core.task_set import Task, SuccessCriteria, EfficiencyCriteria, RobustnessCriteria
from agents.harness.core.mode import HarnessMode


def _make_trace(duration_ms=10000, tool_calls=None, status=TaskStatus.COMPLETED):
    start = datetime.now()
    return HarnessTrace(
        task_id="t1", session_id="s1",
        mode=HarnessMode.HARDWARE_MOCK,
        start_time=start,
        end_time=start + timedelta(milliseconds=duration_ms),
        duration_ms=duration_ms,
        final_status=status,
        skill_calls=[],
        tool_calls=tool_calls or [],
    )


def _make_task(max_dur=30, max_retry=2):
    return Task(
        task_id="t1", description="test", robot_type="arm",
        success_criteria=SuccessCriteria(
            efficiency=EfficiencyCriteria(max_duration_seconds=max_dur),
            robustness=RobustnessCriteria(max_retry_count=max_retry),
        )
    )


def test_efficiency_fast_task():
    score = EfficiencyEvaluator().evaluate(_make_trace(duration_ms=5000), _make_task(max_dur=30))
    assert score.score > 0.8


def test_efficiency_slow_task():
    score = EfficiencyEvaluator().evaluate(_make_trace(duration_ms=60000), _make_task(max_dur=30))
    assert score.score < 0.5


def test_efficiency_no_duration():
    trace = _make_trace()
    trace.duration_ms = None
    score = EfficiencyEvaluator().evaluate(trace, _make_task())
    assert 0.0 <= score.score <= 1.0


def test_robustness_no_retries():
    calls = [ToolCallRecord(datetime.now(), "start_policy", {}, "ok")]
    score = RobustnessEvaluator().evaluate(_make_trace(tool_calls=calls), _make_task())
    assert score.score == pytest.approx(1.0)


def test_robustness_within_limit():
    calls = [
        ToolCallRecord(datetime.now(), "start_policy", {}, "failed"),
        ToolCallRecord(datetime.now(), "start_policy", {}, "ok"),
    ]
    score = RobustnessEvaluator().evaluate(_make_trace(tool_calls=calls), _make_task(max_retry=2))
    assert score.score >= 0.5


def test_robustness_exceeded_limit():
    calls = [ToolCallRecord(datetime.now(), "start_policy", {}, "failed")] * 5
    score = RobustnessEvaluator().evaluate(_make_trace(tool_calls=calls), _make_task(max_retry=2))
    assert score.score < 0.5
