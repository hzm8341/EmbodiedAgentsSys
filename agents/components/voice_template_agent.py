"""VoiceTemplateAgent — guides user through Q&A to fill a SceneSpec."""
from __future__ import annotations

from typing import Any, Callable, Coroutine

from .scene_spec import SceneSpec

# Each tuple: (field_name, question_text, is_list_field)
_QUESTIONS: list[tuple[str, str, bool]] = [
    ("scene_type",       "场景类型？(warehouse_pick / assembly / inspection / other)", False),
    ("environment",      "描述当前环境（货架、机器人位置、空间大小等）：", False),
    ("robot_type",       "机器人类型？(arm / mobile / mobile_arm)", False),
    ("task_description", "用一句话描述任务目标：", False),
    ("objects",          "涉及的对象有哪些？（逗号分隔，如: red_box, shelf_A）", True),
    ("constraints",      "有哪些约束条件？（逗号分隔，或直接回车跳过）", True),
    ("success_criteria", "成功标准是什么？（逗号分隔，或直接回车跳过）", True),
]

_REQUIRED = {"scene_type", "environment", "robot_type", "task_description"}


def _parse_list(text: str) -> list[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


class VoiceTemplateAgent:
    """Fills a SceneSpec via guided Q&A, either programmatically or interactively."""

    QUESTIONS = _QUESTIONS

    async def fill_from_answers(self, answers: dict[str, Any]) -> SceneSpec:
        """Build SceneSpec from a pre-filled answer dict.

        For list fields, values may be comma-separated strings or lists.
        Raises KeyError if any required field is missing.
        """
        for req_field in _REQUIRED:
            if req_field not in answers or not answers[req_field]:
                raise KeyError(f"Required field missing: '{req_field}'")

        def _to_list(val: Any) -> list[str]:
            if isinstance(val, list):
                return val
            return _parse_list(str(val)) if val else []

        return SceneSpec(
            scene_type=str(answers["scene_type"]).strip(),
            environment=str(answers["environment"]).strip(),
            robot_type=str(answers["robot_type"]).strip(),
            task_description=str(answers["task_description"]).strip(),
            objects=_to_list(answers.get("objects", [])),
            constraints=_to_list(answers.get("constraints", [])),
            success_criteria=_to_list(answers.get("success_criteria", [])),
        )

    async def interactive_fill(
        self,
        input_fn: Callable[[str], Coroutine[Any, Any, str]],
        output_fn: Callable[[str], Coroutine[Any, Any, None]],
    ) -> SceneSpec:
        """Interactively fill SceneSpec by calling input_fn for each question.

        Args:
            input_fn: async callable(prompt) → str
            output_fn: async callable(text) → None (for displaying prompts)
        """
        answers: dict[str, Any] = {}
        for field_name, question, is_list in _QUESTIONS:
            await output_fn(f"\n❓ {question}")
            response = await input_fn(question)
            # For list fields, parse comma-separated input into a list immediately
            answers[field_name] = _parse_list(response) if is_list else response
        return await self.fill_from_answers(answers)
