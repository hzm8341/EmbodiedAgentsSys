"""Structured robot memory state m_t = (r_t, g_t, w_t).

Based on paper §3.1: each timestep t the robot maintains:
  r_t  Role Identity     — current mode, robot type, available tool list
  g_t  Task Graph        — global task description + subtask DAG + per-subtask status
  w_t  Working Memory    — current skill being executed, recent tool call history,
                           latest environment summary from Env Summary MCP tool
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SubtaskStatus(str, Enum):
    """Execution status of a single subtask node."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubtaskNode:
    """A single node in the task graph (g_t)."""
    id: str
    description: str
    status: SubtaskStatus = SubtaskStatus.PENDING
    depends_on: list[str] = field(default_factory=list)  # IDs of prerequisite subtasks
    skill_id: str | None = None  # skill assigned to this subtask
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "skill_id": self.skill_id,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SubtaskNode":
        return cls(
            id=d["id"],
            description=d["description"],
            status=SubtaskStatus(d.get("status", "pending")),
            depends_on=d.get("depends_on", []),
            skill_id=d.get("skill_id"),
            failure_reason=d.get("failure_reason"),
        )


@dataclass
class RoleIdentity:
    """r_t — Role identity: what mode the robot is in and what tools it has.

    mode: e.g. "autonomous_task", "data_collection", "human_guided", "idle"
    robot_type: hardware description, e.g. "6DOF_arm_with_gripper"
    available_tools: list of MCP tool names available in this context
    """
    mode: str = "idle"
    robot_type: str = "unknown"
    available_tools: list[str] = field(default_factory=list)

    def to_context_block(self) -> str:
        tools_str = ", ".join(self.available_tools) if self.available_tools else "(none)"
        return (
            f"[Role]\n"
            f"Mode: {self.mode}\n"
            f"Robot: {self.robot_type}\n"
            f"Available tools: {tools_str}"
        )


@dataclass
class TaskGraph:
    """g_t — Task-level memory: global objective + subtask DAG.

    global_task: natural language description of the overall task
    subtasks: ordered list of SubtaskNodes (may form a DAG via depends_on)
    """
    global_task: str = ""
    subtasks: list[SubtaskNode] = field(default_factory=list)

    def get_current_subtask(self) -> SubtaskNode | None:
        """Return the first IN_PROGRESS subtask, or the next PENDING one."""
        for st in self.subtasks:
            if st.status == SubtaskStatus.IN_PROGRESS:
                return st
        for st in self.subtasks:
            if st.status == SubtaskStatus.PENDING:
                # Check all dependencies are completed
                deps_done = all(
                    self._find(dep_id) is not None
                    and self._find(dep_id).status == SubtaskStatus.COMPLETED  # type: ignore
                    for dep_id in st.depends_on
                )
                if deps_done:
                    return st
        return None

    def _find(self, subtask_id: str) -> SubtaskNode | None:
        for st in self.subtasks:
            if st.id == subtask_id:
                return st
        return None

    def progress_summary(self) -> str:
        total = len(self.subtasks)
        done = sum(1 for s in self.subtasks if s.status == SubtaskStatus.COMPLETED)
        failed = sum(1 for s in self.subtasks if s.status == SubtaskStatus.FAILED)
        return f"{done}/{total} completed, {failed} failed"

    def to_context_block(self) -> str:
        lines = [f"[Task]\nGoal: {self.global_task}", f"Progress: {self.progress_summary()}"]
        for st in self.subtasks:
            status_icon = {
                SubtaskStatus.PENDING: "○",
                SubtaskStatus.IN_PROGRESS: "◎",
                SubtaskStatus.COMPLETED: "●",
                SubtaskStatus.FAILED: "✗",
                SubtaskStatus.SKIPPED: "—",
            }.get(st.status, "?")
            line = f"  {status_icon} [{st.id}] {st.description}"
            if st.failure_reason:
                line += f" (FAILED: {st.failure_reason})"
            lines.append(line)
        return "\n".join(lines)


@dataclass
class WorkingMemory:
    """w_t — Working memory: immediate execution context.

    current_skill: skill currently being executed (or None if idle)
    tool_history: recent tool call records (name + args + result), last N entries
    env_summary: latest environment summary from Env Summary MCP tool
    max_history: how many tool calls to retain
    """
    current_skill: str | None = None
    tool_history: list[dict[str, Any]] = field(default_factory=list)
    env_summary: str = ""
    max_history: int = 10

    def record_tool_call(self, name: str, args: dict[str, Any], result: str) -> None:
        """Append a tool call to history, trimming to max_history."""
        self.tool_history.append({"tool": name, "args": args, "result": result})
        if len(self.tool_history) > self.max_history:
            self.tool_history = self.tool_history[-self.max_history:]

    def to_context_block(self) -> str:
        lines = ["[Working Memory]"]
        lines.append(f"Current skill: {self.current_skill or '(none)'}")
        lines.append(f"Environment: {self.env_summary or '(not yet observed)'}")
        if self.tool_history:
            lines.append("Recent tool calls:")
            for entry in self.tool_history[-5:]:  # show last 5
                args_str = json.dumps(entry["args"], ensure_ascii=False)[:80]
                lines.append(f"  {entry['tool']}({args_str}) → {str(entry['result'])[:60]}")
        return "\n".join(lines)


@dataclass
class RobotMemoryState:
    """Full structured robot memory m_t = (r_t, g_t, w_t).

    This is instantiated once per task execution and updated incrementally.
    It is passed to the CoT planner to build the system prompt context.
    """
    role: RoleIdentity = field(default_factory=RoleIdentity)
    task_graph: TaskGraph = field(default_factory=TaskGraph)
    working: WorkingMemory = field(default_factory=WorkingMemory)

    def to_context_block(self) -> str:
        """Render full memory state as a context string for LLM system prompt."""
        return "\n\n".join([
            self.role.to_context_block(),
            self.task_graph.to_context_block(),
            self.working.to_context_block(),
        ])

    def update_env_summary(self, summary: str) -> None:
        self.working.env_summary = summary

    def start_subtask(self, subtask_id: str, skill_id: str | None = None) -> None:
        """Mark a subtask as in-progress and update working memory."""
        st = self.task_graph._find(subtask_id)
        if st is None:
            raise ValueError(f"Unknown subtask ID: {subtask_id}")
        st.status = SubtaskStatus.IN_PROGRESS
        st.skill_id = skill_id
        self.working.current_skill = skill_id

    def complete_subtask(self, subtask_id: str) -> None:
        """Mark a subtask as completed."""
        st = self.task_graph._find(subtask_id)
        if st is None:
            raise ValueError(f"Unknown subtask ID: {subtask_id}")
        st.status = SubtaskStatus.COMPLETED
        if self.working.current_skill == st.skill_id:
            self.working.current_skill = None

    def fail_subtask(self, subtask_id: str, reason: str) -> None:
        """Mark a subtask as failed with a reason."""
        st = self.task_graph._find(subtask_id)
        if st is None:
            raise ValueError(f"Unknown subtask ID: {subtask_id}")
        st.status = SubtaskStatus.FAILED
        st.failure_reason = reason
        if self.working.current_skill == st.skill_id:
            self.working.current_skill = None

    @classmethod
    def create_for_task(
        cls,
        global_task: str,
        subtask_descriptions: list[str],
        robot_type: str = "unknown",
        mode: str = "autonomous_task",
        available_tools: list[str] | None = None,
    ) -> "RobotMemoryState":
        """Factory: create a fresh memory state for a new task.

        Args:
            global_task: Natural language task description.
            subtask_descriptions: Ordered list of subtask descriptions.
            robot_type: Hardware description string.
            mode: Robot operating mode.
            available_tools: MCP tool names available in this execution context.
        """
        subtasks = [
            SubtaskNode(id=f"st_{i:02d}", description=desc)
            for i, desc in enumerate(subtask_descriptions)
        ]
        return cls(
            role=RoleIdentity(
                mode=mode,
                robot_type=robot_type,
                available_tools=available_tools or [],
            ),
            task_graph=TaskGraph(global_task=global_task, subtasks=subtasks),
            working=WorkingMemory(),
        )
