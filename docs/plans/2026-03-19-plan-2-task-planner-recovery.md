:orphan:

# Task Planner with Error Recovery & Semantic Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `TaskPlanner`（带历史错误恢复的分层任务规划器）和 `SemanticMap`（YAML 持久化语义地图），让 LLM 能基于失败历史重新规划，并用地点名称代替坐标进行任务描述。

**Architecture:** `TaskPlanner` 封装 Ollama/OpenAI 调用，维护失败历史列表，输出结构化 `[{"action": "go_to"|"pick"|"place", "target": str, "location": str}]` JSON 序列；`SemanticMap` 负责 YAML 读写，将地点名称映射到坐标，供 `TaskPlanner` 在规划 prompt 中使用。两个类完全独立，互不依赖。

**Tech Stack:** Python 3.10, `ollama` (已安装), `pyyaml`, `pytest`

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `agents/components/task_planner.py` | TaskPlanner：LLM 分层规划 + 错误恢复 |
| Create | `agents/components/semantic_map.py` | SemanticMap：YAML 地图读写 |
| Modify | `agents/components/__init__.py` | 导出新组件 |
| Create | `tests/test_task_planner_component.py` | TaskPlanner 单元测试 |
| Create | `tests/test_semantic_map.py` | SemanticMap 单元测试 |

---

### Task 1: 实现 SemanticMap（语义地图 YAML 持久化）

**Files:**
- Create: `agents/components/semantic_map.py`
- Test: `tests/test_semantic_map.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_semantic_map.py
import pytest
import tempfile
from pathlib import Path
from agents.components.semantic_map import SemanticMap

def test_add_and_get_location():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("desk", x=1.2, y=0.5, theta=0.0)
    loc = sm.get_location("desk")
    assert loc == {"x": 1.2, "y": 0.5, "theta": 0.0}

def test_add_and_get_object():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("table", x=3.1, y=-0.8, theta=1.57)
    sm.add_object("cup", location="table", pos_3d=[3.1, -0.8, 0.85])
    obj = sm.get_object("cup")
    assert obj["location"] == "table"

def test_persist_and_reload():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm1 = SemanticMap(map_path=map_path)
    sm1.add_location("shelf", x=2.0, y=1.0, theta=0.5)
    sm1.save()
    sm2 = SemanticMap(map_path=map_path)
    sm2.load()
    assert sm2.get_location("shelf") is not None

def test_list_locations():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        map_path = f.name
    sm = SemanticMap(map_path=map_path)
    sm.add_location("desk", x=1.0, y=0.0, theta=0.0)
    sm.add_location("table", x=2.0, y=0.0, theta=0.0)
    assert set(sm.list_locations()) == {"desk", "table"}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/test_semantic_map.py -v
```
期望：`FAILED` with `ModuleNotFoundError`

- [ ] **Step 3: 实现 SemanticMap**

```python
# agents/components/semantic_map.py
"""语义地图 — 地点与对象的 YAML 持久化存储。"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


class SemanticMap:
    """
    维护地点坐标和对象位置的持久化地图。

    YAML 格式：
        locations:
          desk: {x: 1.2, y: 0.5, theta: 0.0}
        objects:
          cup: {location: desk, pos_3d: [1.2, 0.5, 0.85]}
    """

    def __init__(self, map_path: str = "config/semantic_map.yaml"):
        self._path = Path(map_path)
        self._data: Dict[str, Any] = {"locations": {}, "objects": {}}
        if self._path.exists():
            self.load()

    # ---------- 地点 ----------

    def add_location(self, name: str, x: float, y: float, theta: float) -> None:
        """添加或更新命名地点。"""
        self._data["locations"][name] = {"x": x, "y": y, "theta": theta}

    def get_location(self, name: str) -> Optional[Dict[str, float]]:
        """获取地点坐标，不存在返回 None。"""
        return self._data["locations"].get(name)

    def list_locations(self) -> List[str]:
        """返回所有已知地点名称。"""
        return list(self._data["locations"].keys())

    # ---------- 对象 ----------

    def add_object(
        self,
        name: str,
        location: str,
        pos_3d: Optional[List[float]] = None,
    ) -> None:
        """记录对象的语义位置。"""
        self._data["objects"][name] = {
            "location": location,
            "pos_3d": pos_3d or [],
        }

    def get_object(self, name: str) -> Optional[Dict[str, Any]]:
        """获取对象信息，不存在返回 None。"""
        return self._data["objects"].get(name)

    def list_objects(self) -> List[str]:
        """返回所有已知对象名称。"""
        return list(self._data["objects"].keys())

    # ---------- 持久化 ----------

    def save(self) -> None:
        """保存地图到 YAML 文件。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def load(self) -> None:
        """从 YAML 文件加载地图。"""
        with open(self._path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        self._data["locations"] = loaded.get("locations", {})
        self._data["objects"] = loaded.get("objects", {})

    def summary_for_prompt(self) -> str:
        """生成供 LLM prompt 使用的地图摘要字符串。"""
        lines = ["已知地点:"]
        for name, coord in self._data["locations"].items():
            lines.append(f"  {name}: ({coord['x']:.1f}, {coord['y']:.1f})")
        if self._data["objects"]:
            lines.append("已知对象:")
            for name, info in self._data["objects"].items():
                lines.append(f"  {name} 在 {info['location']}")
        return "\n".join(lines)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_semantic_map.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/semantic_map.py tests/test_semantic_map.py
git commit -m "feat: add SemanticMap with YAML persistence for LLM planning"
```

---

### Task 2: 实现 TaskPlanner（分层任务规划 + 错误恢复）

**Files:**
- Create: `agents/components/task_planner.py`
- Test: `tests/test_task_planner_component.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_task_planner_component.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from agents.components.task_planner import TaskPlanner, TaskAction, TaskPlan

def test_task_action_fields():
    action = TaskAction(action="pick", target="cup", location="desk")
    assert action.action == "pick"
    assert action.target == "cup"

def test_task_plan_empty():
    plan = TaskPlan(actions=[], instruction="test")
    assert len(plan.actions) == 0
    assert plan.success is True  # 空计划默认成功

@pytest.fixture
def planner():
    return TaskPlanner(
        ollama_model="qwen2.5:3b",
        backend="mock",  # 测试用 mock 后端
    )

def test_planner_parse_valid_json(planner):
    json_str = '[{"action": "go_to", "target": "desk", "location": "desk"}]'
    actions = planner._parse_plan_json(json_str)
    assert len(actions) == 1
    assert actions[0].action == "go_to"

def test_planner_parse_invalid_json_returns_empty(planner):
    actions = planner._parse_plan_json("not json")
    assert actions == []

def test_planner_record_failure(planner):
    planner.record_failure(target="cup", location="desk", reason="not found")
    history = planner.get_failure_history()
    assert len(history) == 1
    assert "cup" in history[0]

def test_planner_clear_history(planner):
    planner.record_failure(target="cup", location="desk", reason="not found")
    planner.clear_history()
    assert planner.get_failure_history() == []

def test_planner_plan_sync_mock(planner):
    """mock 后端同步规划测试。"""
    plan = asyncio.run(planner.plan("拿起桌上的杯子"))
    assert isinstance(plan, TaskPlan)
    assert len(plan.actions) >= 1

def test_planner_replan_with_history(planner):
    """加入失败历史后重规划，历史应出现在 prompt 中。"""
    planner.record_failure(target="flower", location="desk", reason="not found")
    prompt = planner._build_prompt("拿起花")
    assert "flower" in prompt
    assert "desk" in prompt
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_task_planner_component.py -v
```
期望：`FAILED` with `ModuleNotFoundError`

- [ ] **Step 3: 实现 TaskPlanner**

```python
# agents/components/task_planner.py
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
        try:
            from ollama import Client
            self._ollama_client = Client(host="http://127.0.0.1:11434")
        except Exception:
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
            response = await asyncio.get_event_loop().run_in_executor(
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_task_planner_component.py -v
```
期望：全部 `PASSED`

- [ ] **Step 5: 提交**

```bash
git add agents/components/task_planner.py tests/test_task_planner_component.py
git commit -m "feat: add TaskPlanner with LLM-based planning and failure history recovery"
```

---

### Task 3: 集成测试 — TaskPlanner 使用 SemanticMap

**Files:**
- Test: `tests/test_task_planner_component.py`

- [ ] **Step 1: 写集成测试**

```python
# 追加到 tests/test_task_planner_component.py
import tempfile
from agents.components.semantic_map import SemanticMap

def test_planner_uses_semantic_map_in_prompt(planner, tmp_path):
    """规划 prompt 应包含语义地图中的地点信息。"""
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("实验台", x=1.5, y=0.0, theta=0.0)
    sm.add_object("烧杯", location="实验台")

    planner._semantic_map = sm
    prompt = planner._build_prompt("拿起烧杯")
    assert "实验台" in prompt
    assert "烧杯" in prompt

def test_full_replan_cycle(tmp_path):
    """完整重规划循环：规划 → 记录失败 → 重规划。"""
    map_path = tmp_path / "map.yaml"
    sm = SemanticMap(map_path=str(map_path))
    sm.add_location("桌子", x=1.0, y=0.0, theta=0.0)

    planner = TaskPlanner(backend="mock", semantic_map=sm)
    # 第一次规划
    plan1 = asyncio.run(planner.plan("拿起花"))
    assert plan1.success

    # 模拟失败
    planner.record_failure(target="花", location="桌子", reason="not found")

    # 重规划，历史应出现在 prompt
    prompt = planner._build_prompt("拿起花")
    assert "失败" in prompt
    assert "花" in prompt
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/test_task_planner_component.py -v
```
期望：全部 `PASSED`

- [ ] **Step 3: 导出到 `__init__.py`**

在 `agents/components/__init__.py` 追加：

```python
from .task_planner import TaskPlanner, TaskAction, TaskPlan
from .semantic_map import SemanticMap
```

- [ ] **Step 4: 运行全套测试验证无回归**

```bash
pytest tests/ -v --ignore=tests/__pycache__ -x -q 2>&1 | tail -20
```

- [ ] **Step 5: 提交**

```bash
git add agents/components/__init__.py tests/test_task_planner_component.py
git commit -m "feat: integrate TaskPlanner with SemanticMap for context-aware replanning"
```

---

## 验收标准

- [ ] `pytest tests/test_semantic_map.py -v` 全部通过
- [ ] `pytest tests/test_task_planner_component.py -v` 全部通过
- [ ] `TaskPlanner._build_prompt()` 在有失败历史时输出包含失败信息
- [ ] `SemanticMap.save()` + `SemanticMap.load()` 数据往返一致
- [ ] 不影响现有 `test_task_planner.py` 和 `test_semantic_parser.py`
