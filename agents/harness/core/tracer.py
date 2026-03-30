from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from agents.harness.core.config import HarnessConfig
from agents.harness.core.mode import HarnessMode


class TaskStatus:
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass
class ToolCallRecord:
    timestamp: datetime
    tool_name: str
    args: dict
    result: str
    duration_ms: int = 0


@dataclass
class ObservationRecord:
    timestamp: datetime
    content: str


@dataclass
class CoTDecisionRecord:
    timestamp: datetime
    task_state: str
    action_type: str
    action_name: str
    action_args: dict
    reasoning: str


@dataclass
class SubtaskRecord:
    subtask_id: str
    status: str
    description: str
    start_time: datetime
    end_time: Optional[datetime] = None
    failure_reason: Optional[str] = None


@dataclass
class MemorySnapshot:
    timestamp: datetime
    role: str
    task_graph_summary: str
    current_skill: Optional[str] = None


@dataclass
class HarnessTrace:
    task_id: str
    session_id: str
    mode: HarnessMode
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    subtask_graph: list[SubtaskRecord] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    skill_calls: list[str] = field(default_factory=list)
    observations: list[ObservationRecord] = field(default_factory=list)
    cot_decisions: list[CoTDecisionRecord] = field(default_factory=list)
    memory_snapshots: list[MemorySnapshot] = field(default_factory=list)
    final_status: str = TaskStatus.FAILED
    failure_reason: Optional[str] = None


class HarnessTracer:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self._trace: Optional[HarnessTrace] = None

    def start_trace(self, task_id: str, session_id: str) -> None:
        self._trace = HarnessTrace(
            task_id=task_id,
            session_id=session_id,
            mode=self.config.mode,
            start_time=datetime.now(),
        )

    def stop_trace(self, status: str = TaskStatus.COMPLETED,
                   failure_reason: Optional[str] = None) -> HarnessTrace:
        if self._trace is None:
            raise RuntimeError("Trace not started — call start_trace() first")
        self._trace.end_time = datetime.now()
        self._trace.duration_ms = int(
            (self._trace.end_time - self._trace.start_time).total_seconds() * 1000
        )
        self._trace.final_status = status
        self._trace.failure_reason = failure_reason
        return self._trace

    def record_tool_call(self, name: str, args: dict, result: str,
                         duration_ms: int = 0) -> None:
        if self._trace is None:
            return
        self._trace.tool_calls.append(ToolCallRecord(
            timestamp=datetime.now(),
            tool_name=name,
            args=args,
            result=result,
            duration_ms=duration_ms,
        ))
        if name in ("start_policy", "change_policy"):
            skill_id = args.get("skill_id", "")
            if skill_id and skill_id not in self._trace.skill_calls:
                self._trace.skill_calls.append(skill_id)

    def record_observation(self, content: str) -> None:
        if self._trace:
            self._trace.observations.append(ObservationRecord(
                timestamp=datetime.now(), content=content
            ))

    def record_cot_decision(self, task_state: str, action_type: str,
                            action_name: str, action_args: dict,
                            reasoning: str) -> None:
        if self._trace:
            self._trace.cot_decisions.append(CoTDecisionRecord(
                timestamp=datetime.now(),
                task_state=task_state,
                action_type=action_type,
                action_name=action_name,
                action_args=action_args,
                reasoning=reasoning,
            ))

    def record_memory_snapshot(self, role: str, task_graph_summary: str,
                               current_skill: Optional[str] = None) -> None:
        if self._trace:
            self._trace.memory_snapshots.append(MemorySnapshot(
                timestamp=datetime.now(),
                role=role,
                task_graph_summary=task_graph_summary,
                current_skill=current_skill,
            ))

    def get_trace(self) -> Optional[HarnessTrace]:
        return self._trace
