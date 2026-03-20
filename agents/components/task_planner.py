"""分层任务规划器 — 支持基于失败历史的 LLM 重规划。"""

import json
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Literal

from .semantic_map import SemanticMap


@dataclass
class TaskAction:
    """单个任务动作。"""
    action: Literal["go_to", "pick", "place", "inspect"]
    target: str          # 目标对象或地点名称
    location: str = ""   # 执行动作的地点名称

    def __str__(self) -> str:
        return f"{self.action}({self.target} @ {self.location})"


@dataclass
class TaskPlan:
    """任务执行计划。"""
    actions: List[TaskAction]
    instruction: str
    success: bool = True
    error: str = ""

    def __str__(self) -> str:
        return " -> ".join(str(a) for a in self.actions)


_SYSTEM_PROMPT = """你是一个机器人任务规划器。将用户指令分解为一系列原子动作。

允许的动作类型：
- go_to: 导航到指定地点
- pick: 抓取指定对象
- place: 放置对象到指定地点
- inspect: 检查指定目标

输出格式（严格 JSON 数组，不包含其他内容）：
[
  {"action": "go_to", "target": "desk", "location": "desk"},
  {"action": "pick",  "target": "cup",  "location": "desk"},
  {"action": "go_to", "target": "table","location": "table"},
  {"action": "place", "target": "cup",  "location": "table"}
]"""


class TaskPlanner:
    """
    基于 LLM 的分层任务规划器，支持失败历史驱动的重规划。

    Args:
        ollama_model: Ollama 模型名称（默认 qwen2.5:3b）
        backend: "ollama" | "mock"（测试用）
        semantic_map: 可选语义地图，用于 prompt 上下文
    """

    def __init__(
        self,
        ollama_model: str = "qwen2.5:3b",
        backend: Literal["ollama", "mock"] = "ollama",
        semantic_map: Optional[SemanticMap] = None,
    ):
        self._model = ollama_model
        self._backend = backend
        self._semantic_map = semantic_map
        self._failure_history: List[str] = []
        self._ollama_client = None

        if backend == "ollama":
            self._init_ollama()

    def _init_ollama(self) -> None:
        """初始化 Ollama 客户端。"""
        import logging
        try:
            from ollama import Client
            self._ollama_client = Client(host="http://127.0.0.1:11434")
        except ImportError:
            self._backend = "mock"
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Ollama client init failed (%s), falling back to mock backend", exc
            )
            self._backend = "mock"

    # ---------- 失败历史 ----------

    def record_failure(self, target: str, location: str, reason: str) -> None:
        """记录一次执行失败，供下次规划时使用。"""
        self._failure_history.append(
            f"失败：在 {location} 未找到/无法操作 {target}（原因：{reason}）"
        )

    def get_failure_history(self) -> List[str]:
        """返回当前失败历史列表（副本）。"""
        return list(self._failure_history)

    def clear_history(self) -> None:
        """清空失败历史（任务成功完成后调用）。"""
        self._failure_history.clear()

    # ---------- Prompt 构建 ----------

    def _build_prompt(self, instruction: str) -> str:
        """构建包含历史和地图上下文的 prompt。"""
        parts = [f"指令：{instruction}"]

        if self._semantic_map:
            parts.append(self._semantic_map.summary_for_prompt())

        if self._failure_history:
            parts.append("之前的失败记录（规划时请避免重复）：")
            parts.extend(f"  {h}" for h in self._failure_history[-5:])  # 最多 5 条

        parts.append("请输出执行计划（JSON 数组）：")
        return "\n".join(parts)

    # ---------- 规划 ----------

    def _parse_plan_json(self, text: str) -> List[TaskAction]:
        """从 LLM 输出中解析 JSON 动作列表。"""
        text = text.strip()
        # 提取 JSON 数组（处理 LLM 可能附加的额外文本）
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            raw = json.loads(text[start : end + 1])
            return [
                TaskAction(
                    action=item["action"],
                    target=item.get("target", ""),
                    location=item.get("location", ""),
                )
                for item in raw
                if item.get("action") in {"go_to", "pick", "place", "inspect"}
            ]
        except (json.JSONDecodeError, KeyError):
            return []

    async def plan(self, instruction: str) -> TaskPlan:
        """
        为给定指令生成执行计划。

        Args:
            instruction: 自然语言任务指令

        Returns:
            TaskPlan（若 LLM 失败返回空计划并标记 success=False）
        """
        prompt = self._build_prompt(instruction)

        if self._backend == "mock":
            actions = self._mock_plan(instruction)
            return TaskPlan(actions=actions, instruction=instruction)

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._ollama_client.generate(
                    model=self._model,
                    system=_SYSTEM_PROMPT,
                    prompt=prompt,
                    options={"num_predict": 512, "temperature": 0.1},
                ),
            )
            text = response.get("response", "")
            actions = self._parse_plan_json(text)
            if not actions:
                return TaskPlan(
                    actions=[],
                    instruction=instruction,
                    success=False,
                    error=f"LLM 输出无法解析为动作列表: {text[:200]}",
                )
            return TaskPlan(actions=actions, instruction=instruction)
        except Exception as e:
            return TaskPlan(
                actions=[],
                instruction=instruction,
                success=False,
                error=str(e),
            )

    def _mock_plan(self, instruction: str) -> List[TaskAction]:
        """Mock 规划器，用于测试。返回固定的单动作计划。"""
        return [TaskAction(action="inspect", target="target", location="base")]
