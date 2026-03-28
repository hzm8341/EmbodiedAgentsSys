"""Chain-of-Thought task planner.

Implements the 5-step CoT decision process from the paper §3.1:
  Step 1: Observe — summarize current observation
  Step 2: Objective — state the current goal
  Step 3: Success criteria — define what task completion looks like
  Step 4: Evaluate — judge if the task is satisfied / stuck / progressing
  Step 5: Action decision — pick next action (skill call or MCP tool)

The planner is provider-agnostic: it receives an LLMProvider instance,
allowing it to work with Ollama, LiteLLM, or any other backend.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.llm.provider import LLMProvider, LLMResponse
from agents.memory.robot_memory import RobotMemoryState, SubtaskStatus

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    """Task execution state — output of CoT Step 4 (Evaluate)."""
    SATISFIED = "satisfied"    # task complete
    PROGRESSING = "progressing"  # making progress, continue
    STUCK = "stuck"            # not progressing, may need replanning or human help


@dataclass
class CoTDecision:
    """Result of one CoT reasoning cycle.

    action_type: "skill" | "mcp_tool" | "call_human" | "complete"
    action_name: skill_id or MCP tool name
    action_args: arguments for the action
    task_state: evaluation from Step 4
    reasoning: full CoT reasoning text (for logging / audit)
    """
    action_type: str
    action_name: str
    action_args: dict[str, Any] = field(default_factory=dict)
    task_state: TaskState = TaskState.PROGRESSING
    reasoning: str = ""


_COT_SYSTEM_PROMPT = """You are a robot task planner that reasons step-by-step before every action.

You will receive:
1. Current robot memory state (role, task graph, working memory)
2. Current observation from the environment

Respond using EXACTLY this format — no extra text:

## Step 1: Observe
<summarize what you observe in the environment right now>

## Step 2: Objective
<state the current goal / subtask to accomplish>

## Step 3: Success criteria
<define concretely what success looks like for the current subtask>

## Step 4: Evaluate
State: <SATISFIED | PROGRESSING | STUCK>
Reason: <one sentence explaining your evaluation>

## Step 5: Action decision
Action type: <skill | mcp_tool | call_human | complete>
Action name: <skill_id or tool_name>
Action args: <JSON object with arguments, or {}>
"""


class CoTTaskPlanner:
    """Chain-of-Thought task planner powered by any LLMProvider.

    Usage:
        planner = CoTTaskPlanner(provider=OllamaProvider())
        decision = await planner.decide_next_action(
            memory=memory_state,
            observation="The cup is on the left side of the table",
            robot_stats={"joint_errors": [], "gripper_force": 0.0},
        )
    """

    def __init__(
        self,
        provider: LLMProvider,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ):
        self._provider = provider
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def decompose_task(
        self,
        task_description: str,
        robot_type: str = "unknown",
        available_skills: list[str] | None = None,
    ) -> list[str]:
        """Decompose a high-level task into ordered subtask descriptions.

        Returns a list of subtask description strings.
        """
        skills_str = ", ".join(available_skills) if available_skills else "(any)"
        messages = [
            {"role": "system", "content": (
                "You are a robot task decomposer. Break down the task into 3-8 ordered subtasks. "
                "Output ONLY a JSON array of strings, e.g.: "
                '[\"subtask 1\", \"subtask 2\"]'
            )},
            {"role": "user", "content": (
                f"Robot: {robot_type}\n"
                f"Available skills: {skills_str}\n"
                f"Task: {task_description}\n\n"
                "Output subtask list as JSON array:"
            )},
        ]

        response = await self._provider.chat_with_retry(
            messages=messages,
            model=self._model,
            max_tokens=512,
            temperature=0.2,
        )

        return self._parse_subtask_list(response.content or "")

    @staticmethod
    def _parse_subtask_list(text: str) -> list[str]:
        """Extract JSON array of strings from LLM output."""
        text = text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            items = json.loads(text[start:end + 1])
            return [str(item) for item in items if item]
        except (json.JSONDecodeError, ValueError):
            return []

    async def decide_next_action(
        self,
        memory: RobotMemoryState,
        observation: str,
        robot_stats: dict[str, Any] | None = None,
    ) -> CoTDecision:
        """Run one CoT cycle and return the next action to take.

        Args:
            memory: Current structured robot memory state m_t.
            observation: Latest environment observation string.
            robot_stats: Optional robot health metrics (joint errors, etc.)

        Returns:
            CoTDecision with action to execute and task state evaluation.
        """
        context = self._build_context(memory, observation, robot_stats)

        messages = [
            {"role": "system", "content": _COT_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]

        response = await self._provider.chat_with_retry(
            messages=messages,
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

        if response.finish_reason == "error":
            logger.warning("CoT planner LLM error: %s", response.content)
            return CoTDecision(
                action_type="call_human",
                action_name="call_human",
                action_args={"reason": f"LLM error: {response.content}"},
                task_state=TaskState.STUCK,
                reasoning=response.content or "",
            )

        return self._parse_cot_response(response.content or "")

    def _build_context(
        self,
        memory: RobotMemoryState,
        observation: str,
        robot_stats: dict[str, Any] | None,
    ) -> str:
        """Build the user-turn context string from memory + observation."""
        parts = [memory.to_context_block()]
        parts.append(f"\n[Current Observation]\n{observation}")
        if robot_stats:
            stats_str = json.dumps(robot_stats, ensure_ascii=False, indent=2)
            parts.append(f"\n[Robot Stats]\n{stats_str}")
        return "\n".join(parts)

    @staticmethod
    def _parse_cot_response(text: str) -> CoTDecision:
        """Parse CoT formatted LLM response into a CoTDecision."""
        # Extract task state from Step 4
        state = TaskState.PROGRESSING
        state_match = re.search(r"State:\s*(SATISFIED|PROGRESSING|STUCK)", text, re.IGNORECASE)
        if state_match:
            state_str = state_match.group(1).upper()
            state = TaskState(state_str.lower())

        # Extract action type
        action_type = "mcp_tool"
        type_match = re.search(
            r"Action type:\s*(skill|mcp_tool|call_human|complete)",
            text, re.IGNORECASE,
        )
        if type_match:
            action_type = type_match.group(1).lower()

        # Extract action name
        action_name = ""
        name_match = re.search(r"Action name:\s*(\S+)", text)
        if name_match:
            action_name = name_match.group(1).strip()

        # Extract action args (JSON object)
        action_args: dict[str, Any] = {}
        args_match = re.search(r"Action args:\s*(\{[^}]*\}|\{\})", text, re.DOTALL)
        if args_match:
            try:
                action_args = json.loads(args_match.group(1))
            except json.JSONDecodeError:
                pass

        # Handle SATISFIED → complete action
        if state == TaskState.SATISFIED:
            action_type = "complete"
            action_name = "complete"

        return CoTDecision(
            action_type=action_type,
            action_name=action_name,
            action_args=action_args,
            task_state=state,
            reasoning=text,
        )
