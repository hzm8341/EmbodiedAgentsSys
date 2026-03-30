# tests/test_tracer.py
import pytest
from datetime import datetime
from agents.harness.core.tracer import HarnessTracer, TaskStatus
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode


def test_tracer_start_stop():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("task_001", "sess_001")
    trace = tracer.stop_trace(TaskStatus.COMPLETED)
    assert trace.task_id == "task_001"
    assert trace.final_status == TaskStatus.COMPLETED
    assert trace.duration_ms is not None
    assert trace.duration_ms >= 0


def test_tracer_records_tool_call():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("t1", "s1")
    tracer.record_tool_call("env_summary", {}, "ok")
    trace = tracer.get_trace()
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "env_summary"


def test_tracer_extracts_skill_from_start_policy():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("t1", "s1")
    tracer.record_tool_call("start_policy", {"skill_id": "manipulation.grasp"}, "ok")
    trace = tracer.get_trace()
    assert "manipulation.grasp" in trace.skill_calls


def test_tracer_records_cot_decision():
    tracer = HarnessTracer(HarnessConfig())
    tracer.start_trace("t1", "s1")
    tracer.record_cot_decision("running", "skill", "start_policy",
                               {"skill_id": "manipulation.reach"}, "reach first")
    trace = tracer.get_trace()
    assert len(trace.cot_decisions) == 1
    assert trace.cot_decisions[0].action_name == "start_policy"


def test_tracer_stop_without_start_raises():
    tracer = HarnessTracer(HarnessConfig())
    with pytest.raises(RuntimeError):
        tracer.stop_trace()
