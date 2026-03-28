"""Tests for agents/memory — RobotMemoryState, CoTTaskPlanner, FailureLog."""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path

from agents.memory.robot_memory import (
    RobotMemoryState,
    RoleIdentity,
    TaskGraph,
    WorkingMemory,
    SubtaskNode,
    SubtaskStatus,
)
from agents.memory.failure_log import FailureLog, FailureRecord
from agents.components.cot_planner import CoTTaskPlanner, CoTDecision, TaskState
from agents.llm.provider import LLMProvider, LLMResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockProvider(LLMProvider):
    def __init__(self, content: str):
        super().__init__()
        self._content = content

    async def chat(self, messages, **kwargs) -> LLMResponse:
        return LLMResponse(content=self._content)

    def get_default_model(self) -> str:
        return "mock"


# ---------------------------------------------------------------------------
# SubtaskNode
# ---------------------------------------------------------------------------

def test_subtask_node_default_status():
    node = SubtaskNode(id="st_01", description="Pick up the cup")
    assert node.status == SubtaskStatus.PENDING
    assert node.depends_on == []


def test_subtask_node_serialization():
    node = SubtaskNode(id="st_01", description="Move arm", status=SubtaskStatus.COMPLETED)
    d = node.to_dict()
    assert d["status"] == "completed"
    restored = SubtaskNode.from_dict(d)
    assert restored.status == SubtaskStatus.COMPLETED
    assert restored.id == "st_01"


# ---------------------------------------------------------------------------
# TaskGraph
# ---------------------------------------------------------------------------

def test_task_graph_get_current_subtask_returns_first_pending():
    graph = TaskGraph(
        global_task="Pick and place",
        subtasks=[
            SubtaskNode(id="st_00", description="Navigate to table"),
            SubtaskNode(id="st_01", description="Grasp cup"),
        ],
    )
    current = graph.get_current_subtask()
    assert current is not None
    assert current.id == "st_00"


def test_task_graph_skips_completed():
    graph = TaskGraph(
        global_task="Pick and place",
        subtasks=[
            SubtaskNode(id="st_00", description="Nav", status=SubtaskStatus.COMPLETED),
            SubtaskNode(id="st_01", description="Grasp"),
        ],
    )
    current = graph.get_current_subtask()
    assert current.id == "st_01"


def test_task_graph_dependency_check():
    graph = TaskGraph(
        global_task="Pick and place",
        subtasks=[
            SubtaskNode(id="st_00", description="Nav"),
            SubtaskNode(id="st_01", description="Grasp", depends_on=["st_00"]),
        ],
    )
    # st_01 depends on st_00 which is still PENDING → should not be returned
    current = graph.get_current_subtask()
    assert current.id == "st_00"

    graph.subtasks[0].status = SubtaskStatus.COMPLETED
    current = graph.get_current_subtask()
    assert current.id == "st_01"


def test_task_graph_progress_summary():
    graph = TaskGraph(
        global_task="test",
        subtasks=[
            SubtaskNode(id="a", description="A", status=SubtaskStatus.COMPLETED),
            SubtaskNode(id="b", description="B", status=SubtaskStatus.FAILED),
            SubtaskNode(id="c", description="C"),
        ],
    )
    summary = graph.progress_summary()
    assert "1/3" in summary
    assert "1 failed" in summary


# ---------------------------------------------------------------------------
# RobotMemoryState
# ---------------------------------------------------------------------------

def test_robot_memory_state_create_for_task():
    memory = RobotMemoryState.create_for_task(
        global_task="Pick cup from table and place on shelf",
        subtask_descriptions=["Navigate to table", "Grasp cup", "Navigate to shelf", "Place cup"],
        robot_type="6DOF_arm",
        mode="autonomous_task",
        available_tools=["start_policy", "terminate_policy", "env_summary"],
    )
    assert memory.role.robot_type == "6DOF_arm"
    assert memory.role.mode == "autonomous_task"
    assert len(memory.role.available_tools) == 3
    assert len(memory.task_graph.subtasks) == 4
    assert memory.task_graph.subtasks[0].id == "st_00"


def test_robot_memory_start_complete_subtask():
    memory = RobotMemoryState.create_for_task(
        global_task="test",
        subtask_descriptions=["Step A", "Step B"],
    )
    memory.start_subtask("st_00", skill_id="navigation.goto")
    assert memory.task_graph.subtasks[0].status == SubtaskStatus.IN_PROGRESS
    assert memory.working.current_skill == "navigation.goto"

    memory.complete_subtask("st_00")
    assert memory.task_graph.subtasks[0].status == SubtaskStatus.COMPLETED
    assert memory.working.current_skill is None


def test_robot_memory_fail_subtask():
    memory = RobotMemoryState.create_for_task(
        global_task="test",
        subtask_descriptions=["Step A"],
    )
    memory.start_subtask("st_00", skill_id="manipulation.grasp")
    memory.fail_subtask("st_00", reason="object not found")
    assert memory.task_graph.subtasks[0].status == SubtaskStatus.FAILED
    assert "object not found" in memory.task_graph.subtasks[0].failure_reason


def test_robot_memory_to_context_block():
    memory = RobotMemoryState.create_for_task(
        global_task="Pick and place",
        subtask_descriptions=["Navigate", "Grasp"],
        available_tools=["env_summary"],
    )
    ctx = memory.to_context_block()
    assert "Pick and place" in ctx
    assert "Navigate" in ctx
    assert "env_summary" in ctx
    assert "[Role]" in ctx
    assert "[Task]" in ctx
    assert "[Working Memory]" in ctx


def test_working_memory_record_tool_call():
    wm = WorkingMemory(max_history=3)
    for i in range(5):
        wm.record_tool_call(f"tool_{i}", {"arg": i}, f"result_{i}")
    assert len(wm.tool_history) == 3
    assert wm.tool_history[0]["tool"] == "tool_2"


def test_working_memory_update_env_summary():
    memory = RobotMemoryState.create_for_task("test", ["step"])
    memory.update_env_summary("Cup is on the left side")
    assert "Cup is on the left side" in memory.working.env_summary


# ---------------------------------------------------------------------------
# CoTTaskPlanner._parse_cot_response
# ---------------------------------------------------------------------------

_SAMPLE_COT = """## Step 1: Observe
The cup is positioned on the left side of the table, approximately 30cm from the edge.

## Step 2: Objective
Grasp the cup using the robot arm.

## Step 3: Success criteria
The gripper closes around the cup and lifts it 10cm off the table surface.

## Step 4: Evaluate
State: PROGRESSING
Reason: The cup is visible and within reach, no obstacles detected.

## Step 5: Action decision
Action type: skill
Action name: manipulation.grasp
Action args: {"object_id": "cup_01", "approach": "top_down"}
"""


def test_parse_cot_response_skill():
    decision = CoTTaskPlanner._parse_cot_response(_SAMPLE_COT)
    assert decision.task_state == TaskState.PROGRESSING
    assert decision.action_type == "skill"
    assert decision.action_name == "manipulation.grasp"
    assert decision.action_args == {"object_id": "cup_01", "approach": "top_down"}


def test_parse_cot_response_satisfied():
    text = """## Step 4: Evaluate
State: SATISFIED
Reason: Task complete.

## Step 5: Action decision
Action type: complete
Action name: complete
Action args: {}
"""
    decision = CoTTaskPlanner._parse_cot_response(text)
    assert decision.task_state == TaskState.SATISFIED
    assert decision.action_type == "complete"


def test_parse_cot_response_stuck_calls_human():
    text = """## Step 4: Evaluate
State: STUCK
Reason: Cannot locate object after 3 attempts.

## Step 5: Action decision
Action type: call_human
Action name: call_human
Action args: {"reason": "object not found"}
"""
    decision = CoTTaskPlanner._parse_cot_response(text)
    assert decision.task_state == TaskState.STUCK
    assert decision.action_type == "call_human"


def test_parse_cot_response_mcp_tool():
    text = """## Step 4: Evaluate
State: PROGRESSING
Reason: Need env update.

## Step 5: Action decision
Action type: mcp_tool
Action name: env_summary
Action args: {}
"""
    decision = CoTTaskPlanner._parse_cot_response(text)
    assert decision.action_type == "mcp_tool"
    assert decision.action_name == "env_summary"


# ---------------------------------------------------------------------------
# CoTTaskPlanner.decide_next_action (with mock provider)
# ---------------------------------------------------------------------------

def test_decide_next_action_uses_provider():
    provider = _MockProvider(_SAMPLE_COT)
    planner = CoTTaskPlanner(provider=provider)
    memory = RobotMemoryState.create_for_task(
        global_task="Pick cup",
        subtask_descriptions=["Grasp cup"],
    )

    async def run():
        return await planner.decide_next_action(
            memory=memory,
            observation="Cup is on the table",
        )

    decision = asyncio.get_event_loop().run_until_complete(run())
    assert decision.action_name == "manipulation.grasp"
    assert decision.task_state == TaskState.PROGRESSING


def test_decide_next_action_llm_error_returns_call_human():
    provider = _MockProvider("error content")

    class _ErrorProvider(LLMProvider):
        async def chat(self, messages, **kwargs) -> LLMResponse:
            return LLMResponse(content="Error calling LLM: 500 server error", finish_reason="error")

        def get_default_model(self) -> str:
            return "mock"

    planner = CoTTaskPlanner(provider=_ErrorProvider())
    memory = RobotMemoryState.create_for_task("test", ["step"])

    async def run():
        return await planner.decide_next_action(memory=memory, observation="obs")

    decision = asyncio.get_event_loop().run_until_complete(run())
    assert decision.action_type == "call_human"
    assert decision.task_state == TaskState.STUCK


# ---------------------------------------------------------------------------
# CoTTaskPlanner.decompose_task
# ---------------------------------------------------------------------------

def test_decompose_task_parses_json_array():
    provider = _MockProvider('["Navigate to table", "Grasp cup", "Place on shelf"]')
    planner = CoTTaskPlanner(provider=provider)

    async def run():
        return await planner.decompose_task("Pick up cup and place on shelf")

    subtasks = asyncio.get_event_loop().run_until_complete(run())
    assert len(subtasks) == 3
    assert "Grasp cup" in subtasks


def test_decompose_task_handles_json_with_extra_text():
    provider = _MockProvider('Here is the plan:\n["step 1", "step 2"]\nDone.')
    planner = CoTTaskPlanner(provider=provider)

    async def run():
        return await planner.decompose_task("task")

    subtasks = asyncio.get_event_loop().run_until_complete(run())
    assert subtasks == ["step 1", "step 2"]


# ---------------------------------------------------------------------------
# FailureLog
# ---------------------------------------------------------------------------

def test_failure_log_append_and_read():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FailureLog(Path(tmpdir) / "failures.ndjson")

        record = FailureRecord.create(
            task_description="Pick cup",
            subtask_id="st_01",
            subtask_description="Grasp cup",
            error_type="grasp_failure",
            error_detail="gripper did not close",
            skill_id="manipulation.grasp",
            robot_type="6DOF_arm",
        )

        async def run():
            await log.append(record)
            return await log.read_all()

        records = asyncio.get_event_loop().run_until_complete(run())
        assert len(records) == 1
        assert records[0].error_type == "grasp_failure"
        assert records[0].subtask_id == "st_01"


def test_failure_log_read_recent():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FailureLog(Path(tmpdir) / "failures.ndjson")

        async def run():
            for i in range(5):
                r = FailureRecord.create(
                    task_description=f"task_{i}",
                    subtask_id="st_00",
                    subtask_description="step",
                    error_type="timeout",
                    error_detail=f"timed out attempt {i}",
                )
                await log.append(r)
            return await log.read_recent(n=3)

        records = asyncio.get_event_loop().run_until_complete(run())
        assert len(records) == 3
        assert records[-1].task_description == "task_4"


def test_failure_log_summary_for_prompt():
    with tempfile.TemporaryDirectory() as tmpdir:
        log = FailureLog(Path(tmpdir) / "f.ndjson")

        async def run():
            r = FailureRecord.create(
                task_description="pick",
                subtask_id="st_00",
                subtask_description="Grasp cup",
                error_type="collision",
                error_detail="arm hit table edge",
            )
            await log.append(r)
            return await log.summary_for_prompt()

        summary = asyncio.get_event_loop().run_until_complete(run())
        assert "Grasp cup" in summary
        assert "collision" in summary
