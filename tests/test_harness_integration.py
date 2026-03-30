# tests/test_harness_integration.py
import asyncio
import pytest
from unittest.mock import MagicMock
from agents.harness.integration import attach_harness, TracingToolRegistry
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode
from agents.harness.core.tracer import HarnessTracer
from agents.channels.robot_tools import RobotToolRegistry, ToolResult


def _make_real_registry():
    reg = RobotToolRegistry()
    async def _dummy(**kwargs):
        return ToolResult("test_tool", True, "ok")
    reg.register("test_tool", _dummy)
    return reg


def test_tracing_registry_records_calls():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    tracer = HarnessTracer(config)
    tracer.start_trace("t1", "s1")

    real_reg = _make_real_registry()
    tracing_reg = TracingToolRegistry(real_reg, tracer)

    asyncio.run(tracing_reg.call("test_tool", {}))
    trace = tracer.get_trace()
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "test_tool"


def test_tracing_registry_extracts_skill_id():
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)
    tracer = HarnessTracer(config)
    tracer.start_trace("t1", "s1")

    real_reg = _make_real_registry()
    async def _start_policy(skill_id="", **kwargs):
        return ToolResult("start_policy", True, f"started {skill_id}")
    real_reg.register("start_policy", _start_policy)

    tracing_reg = TracingToolRegistry(real_reg, tracer)
    asyncio.run(tracing_reg.call("start_policy", {"skill_id": "manipulation.grasp"}))

    trace = tracer.get_trace()
    assert "manipulation.grasp" in trace.skill_calls


def test_attach_harness_returns_patched_loop():
    from agents.channels.agent_loop import RobotAgentLoop
    from agents.channels.bus import MessageBus
    config = HarnessConfig(mode=HarnessMode.HARDWARE_MOCK)

    mock_provider = MagicMock()
    bus = MessageBus()
    loop = RobotAgentLoop(bus=bus, provider=mock_provider, robot_type="arm")

    patched_loop, tracer = attach_harness(loop, config)
    assert tracer is not None
    assert isinstance(patched_loop.tool_registry, TracingToolRegistry)
