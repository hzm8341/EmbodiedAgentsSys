"""Tests for agents/channels — MessageBus, RobotToolRegistry, RobotAgentLoop."""

import asyncio
import pytest
from typing import Any

from agents.channels.events import InboundMessage, OutboundMessage
from agents.channels.bus import MessageBus
from agents.channels.robot_tools import RobotToolRegistry, ToolResult, build_default_robot_tools
from agents.channels.agent_loop import RobotAgentLoop
from agents.llm.provider import LLMProvider, LLMResponse


# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------

class _SequenceProvider(LLMProvider):
    """Returns a sequence of responses (one per call)."""

    def __init__(self, responses: list[str]):
        super().__init__()
        self._responses = responses
        self._index = 0

    async def chat(self, messages, **kwargs) -> LLMResponse:
        if self._index < len(self._responses):
            content = self._responses[self._index]
            self._index += 1
        else:
            content = self._responses[-1]
        return LLMResponse(content=content)

    def get_default_model(self) -> str:
        return "mock-sequence"


# ---------------------------------------------------------------------------
# MessageBus
# ---------------------------------------------------------------------------

def test_message_bus_publish_consume_inbound():
    bus = MessageBus()
    msg = InboundMessage(channel="test", sender_id="user", chat_id="c1", content="hello")

    async def run():
        await bus.publish_inbound(msg)
        received = await bus.consume_inbound()
        return received

    received = asyncio.get_event_loop().run_until_complete(run())
    assert received.content == "hello"
    assert received.channel == "test"


def test_message_bus_publish_consume_outbound():
    bus = MessageBus()
    msg = OutboundMessage(channel="test", chat_id="c1", content="response")

    async def run():
        await bus.publish_outbound(msg)
        received = await bus.consume_outbound()
        return received

    received = asyncio.get_event_loop().run_until_complete(run())
    assert received.content == "response"


def test_message_bus_size_tracking():
    bus = MessageBus()

    async def run():
        msg = InboundMessage(channel="t", sender_id="u", chat_id="c", content="x")
        await bus.publish_inbound(msg)
        assert bus.inbound_size == 1
        await bus.consume_inbound()
        assert bus.inbound_size == 0

    asyncio.get_event_loop().run_until_complete(run())


def test_message_bus_outbound_handler():
    bus = MessageBus()
    received_msgs = []

    async def handler(msg: OutboundMessage):
        received_msgs.append(msg)

    bus.register_outbound_handler(handler)

    async def run():
        await bus.publish_outbound(OutboundMessage(channel="t", chat_id="c", content="hi"))
        await asyncio.sleep(0)  # yield to handlers

    asyncio.get_event_loop().run_until_complete(run())
    assert len(received_msgs) == 1
    assert received_msgs[0].content == "hi"


def test_inbound_message_session_key():
    msg = InboundMessage(channel="ros", sender_id="robot", chat_id="arm_01", content="pick")
    assert msg.session_key == "ros:arm_01"


def test_inbound_message_session_key_override():
    msg = InboundMessage(
        channel="ros", sender_id="robot", chat_id="arm_01", content="pick",
        session_key_override="custom_key",
    )
    assert msg.session_key == "custom_key"


# ---------------------------------------------------------------------------
# RobotToolRegistry
# ---------------------------------------------------------------------------

def test_tool_registry_register_and_call():
    registry = RobotToolRegistry()

    async def my_tool(value: int = 0) -> ToolResult:
        return ToolResult("my_tool", True, f"got {value}")

    registry.register("my_tool", my_tool)

    async def run():
        return await registry.call("my_tool", {"value": 42})

    result = asyncio.get_event_loop().run_until_complete(run())
    assert result.success
    assert "42" in result.content


def test_tool_registry_unknown_tool():
    registry = RobotToolRegistry()

    async def run():
        return await registry.call("nonexistent", {})

    result = asyncio.get_event_loop().run_until_complete(run())
    assert not result.success
    assert "Unknown tool" in result.content


def test_tool_registry_exception_handling():
    registry = RobotToolRegistry()

    async def bad_tool(**kwargs) -> ToolResult:
        raise ValueError("oops")

    registry.register("bad_tool", bad_tool)

    async def run():
        return await registry.call("bad_tool", {})

    result = asyncio.get_event_loop().run_until_complete(run())
    assert not result.success
    assert "oops" in result.content


def test_tool_registry_list_tools():
    registry = RobotToolRegistry()
    registry.register("tool_a", lambda: None)
    registry.register("tool_b", lambda: None)
    tools = registry.list_tools()
    assert "tool_a" in tools
    assert "tool_b" in tools


def test_default_robot_tools_registered():
    registry = build_default_robot_tools()
    expected = ["start_policy", "terminate_policy", "change_policy",
                "env_summary", "fetch_robot_stats", "call_human"]
    for tool in expected:
        assert registry.has_tool(tool), f"Missing tool: {tool}"


def test_default_robot_tools_stubs():
    registry = build_default_robot_tools()

    async def run():
        result = await registry.call("env_summary", {})
        return result

    result = asyncio.get_event_loop().run_until_complete(run())
    assert result.success
    assert "[stub]" in result.content


# ---------------------------------------------------------------------------
# RobotAgentLoop
# ---------------------------------------------------------------------------

def _make_decompose_response(subtasks: list[str]) -> str:
    """JSON array of subtasks for decompose_task."""
    import json
    return json.dumps(subtasks)


def _make_cot_complete_response() -> str:
    return """## Step 4: Evaluate
State: SATISFIED
Reason: Task is done.

## Step 5: Action decision
Action type: complete
Action name: complete
Action args: {}
"""


def _make_cot_skill_response(skill: str) -> str:
    return f"""## Step 4: Evaluate
State: PROGRESSING
Reason: Executing skill.

## Step 5: Action decision
Action type: skill
Action name: {skill}
Action args: {{}}
"""


def test_robot_agent_loop_processes_message():
    """Single subtask task that completes immediately."""
    # Sequence: decompose (returns 1 subtask) → CoT decides SATISFIED
    provider = _SequenceProvider([
        _make_decompose_response(["pick up the cup"]),
        _make_cot_complete_response(),
    ])

    bus = MessageBus()
    loop = RobotAgentLoop(
        bus=bus,
        provider=provider,
        robot_type="6DOF_arm",
        max_iterations=3,
    )

    async def run():
        msg = InboundMessage(
            channel="test", sender_id="user", chat_id="c1",
            content="pick up the cup from the table",
        )
        await bus.publish_inbound(msg)

        # Process just this one message
        inbound = await bus.consume_inbound()
        await loop._handle_message(inbound)

        # Collect outbound messages
        msgs = []
        while bus.outbound_size > 0:
            msgs.append(await bus.consume_outbound())
        return msgs

    msgs = asyncio.get_event_loop().run_until_complete(run())
    # Should have acknowledgment + final result
    assert len(msgs) >= 2
    statuses = [m.status for m in msgs]
    assert "in_progress" in statuses
    assert "complete" in statuses


def test_robot_agent_loop_no_subtasks_uses_full_task():
    """When decomposition returns empty, uses full task as single subtask."""
    provider = _SequenceProvider([
        "",  # empty decompose → falls back to single subtask
        _make_cot_complete_response(),
    ])

    bus = MessageBus()
    loop = RobotAgentLoop(bus=bus, provider=provider, max_iterations=3)

    async def run():
        msg = InboundMessage(channel="t", sender_id="u", chat_id="c", content="do task")
        await bus.publish_inbound(msg)
        inbound = await bus.consume_inbound()
        await loop._handle_message(inbound)
        msgs = []
        while bus.outbound_size > 0:
            msgs.append(await bus.consume_outbound())
        return msgs

    msgs = asyncio.get_event_loop().run_until_complete(run())
    assert any(m.status == "complete" for m in msgs)


def test_robot_agent_loop_respects_max_iterations():
    """Subtask that never completes hits max_iterations and fails."""
    # Always returns PROGRESSING → never finishes
    def make_progressing(skill: str = "env_summary") -> str:
        return _make_cot_skill_response(skill)

    # decompose gives 1 subtask; all CoT calls say PROGRESSING
    responses = [_make_decompose_response(["step 1"])] + [make_progressing()] * 10
    provider = _SequenceProvider(responses)

    bus = MessageBus()
    loop = RobotAgentLoop(bus=bus, provider=provider, max_iterations=2)

    async def run():
        msg = InboundMessage(channel="t", sender_id="u", chat_id="c", content="do task")
        await bus.publish_inbound(msg)
        inbound = await bus.consume_inbound()
        await loop._handle_message(inbound)
        msgs = []
        while bus.outbound_size > 0:
            msgs.append(await bus.consume_outbound())
        return msgs

    msgs = asyncio.get_event_loop().run_until_complete(run())
    final = msgs[-1]
    # Task completes (with failures) — loop doesn't crash
    assert final.status in ("complete", "error")


def test_robot_agent_loop_stop():
    loop = RobotAgentLoop(bus=MessageBus(), provider=_SequenceProvider([]))
    loop._running = True
    loop.stop()
    assert not loop._running
