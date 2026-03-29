"""VoiceTemplateAgent — guides user through Q&A to fill a SceneSpec."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Coroutine, Optional, Awaitable

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


logger = logging.getLogger(__name__)


class ConversationalSceneAgent:
    """LLM 驱动的多轮对话式 SceneSpec 填写。

    支持两种模式：
    1. 有 llm_provider：规则提取 + LLM 补充
    2. 无 llm_provider：仅规则提取 + 追问
    """

    _RULE_PATTERNS = {
        "pick":     ["抓", "拿", "取", "拾", "pick", "grab", "grasp"],
        "place":    ["放", "置", "摆", "place", "put", "set"],
        "navigate": ["去", "移动到", "前往", "navigate", "go to", "move to"],
        "inspect":  ["检查", "观察", "看", "inspect", "check", "look"],
    }

    _ROBOT_TYPE_KEYWORDS = {
        "arm":        ["机械臂", "arm", "manipulator"],
        "mobile":     ["移动机器人", "mobile", "agv", "amr"],
        "mobile_arm": ["移动+机械臂", "mobile arm", "mobile_arm"],
    }

    def __init__(
        self,
        llm_provider: Optional[Any] = None,   # LLMProvider（可选）
    ):
        self._llm_provider = llm_provider

    def _extract_by_rules(self, utterance: str) -> dict:
        """规则提取：从单句描述中快速推断 scene_type 和 task_description。"""
        result = {"task_description": utterance.strip()}

        # 推断 scene_type
        for action, keywords in self._RULE_PATTERNS.items():
            if any(kw in utterance for kw in keywords):
                result["scene_type"] = action
                break

        # 推断 robot_type
        for rtype, keywords in self._ROBOT_TYPE_KEYWORDS.items():
            if any(kw in utterance for kw in keywords):
                result["robot_type"] = rtype
                break

        return result

    async def _ask_llm(self, utterance: str, missing: list[str]) -> dict:
        """用 LLM 从 utterance 中提取缺失字段。"""
        if self._llm_provider is None:
            return {}

        field_desc = {
            "scene_type": "任务类型(pick/place/navigate/inspect/other)",
            "environment": "环境描述(如:仓库/装配线/室内等)",
            "robot_type": "机器人类型(arm/mobile/mobile_arm)",
        }

        fields_str = "\n".join(
            f"- {f}: {field_desc.get(f, f)}" for f in missing if f != "task_description"
        )
        if not fields_str:
            return {}

        prompt = f"""从以下机器人任务描述中提取信息，输出严格 JSON：
描述：{utterance}
需要提取的字段：
{fields_str}
仅输出 JSON，不含其他文字。"""

        try:
            response = await self._llm_provider.chat_with_retry(
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content or ""
            # 提取 JSON
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception as exc:
            logger.warning("LLM extraction failed: %s", exc)
        return {}

    async def fill_from_utterance(
        self,
        utterance: str,
        send_fn: Callable[[str], Awaitable[None]],
        recv_fn: Callable[[], Awaitable[str]],
    ) -> "SceneSpec":
        """主入口：从一句话描述填充 SceneSpec。

        Args:
            utterance: 用户输入的任务描述
            send_fn: 向用户发送消息的异步函数
            recv_fn: 接收用户回复的异步函数

        Returns:
            填充完整的 SceneSpec
        """
        from agents.components.scene_spec import SceneSpec

        # Step 1: 规则提取
        extracted = self._extract_by_rules(utterance)
        spec = SceneSpec.from_partial(extracted)

        # Step 2: LLM 补充（若配置）
        if self._llm_provider and not spec.is_complete():
            llm_data = await self._ask_llm(utterance, spec.missing_fields())
            # 用 from_partial 重新构造以合并
            merged = extracted.copy()
            merged.update(llm_data)
            spec = SceneSpec.from_partial(merged)

        # Step 3: 逐一追问缺失的必填字段
        field_questions = {
            "scene_type":       "场景类型？(pick / place / navigate / inspect / other)",
            "environment":      "描述当前环境（如：仓库货架区、装配台、室内桌面）：",
            "robot_type":       "机器人类型？(arm / mobile / mobile_arm)",
            "task_description": "用一句话描述任务目标：",
        }

        data = {
            "scene_type": spec.scene_type,
            "environment": spec.environment,
            "robot_type": spec.robot_type,
            "task_description": spec.task_description,
            "objects": spec.objects,
            "constraints": spec.constraints,
            "success_criteria": spec.success_criteria,
        }

        for field_name in spec.missing_fields():
            question = field_questions.get(field_name, f"请提供 {field_name}：")
            await send_fn(question)
            answer = await recv_fn()
            data[field_name] = answer.strip()

        return SceneSpec.from_partial(data)
