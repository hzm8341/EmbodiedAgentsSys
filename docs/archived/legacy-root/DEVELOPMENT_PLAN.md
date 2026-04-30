:orphan:

# EmbodiedAgentsSys 详细开发计划

> 基于 INTEGRATION_PLAN.md v2 制定。共 7 个 Phase，29 个工作日。
> Phase F（Skill 格式）从 Day 1 与 Phase A 并行推进。

---

## 一、总体时间线

```
Week 1  (Day  1- 5): Phase A（LLM抽象层）+ Phase F 启动（并行）
Week 2  (Day  6-10): Phase B（结构化记忆）+ Phase F 收尾
Week 3  (Day 11-15): Phase C（AgentLoop + 渠道）
Week 4  (Day 16-22): Phase D（EAP）+ Phase G 启动
Week 5  (Day 23-29): Phase E（过程监督）+ Phase G 收尾

依赖关系：
  F ────────────────────────────────────── 独立并行
  A → B ─────────────────────────────────
  A → C ─────────────────────────────────
  B → D ─────────────────────────────────
  B+C → E ───────────────────────────────
  A+C → G ───────────────────────────────
```

```
Day:  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29
A:   [A1.1][A1.2][A2.1][A2.2]
B:                        [B1.1][B1.2][B2.1][B2.2][B3 ]
C:                        [C1.1][C1.2][C2.1][C2.2][C3 ]
D:                                              [D1 ][D2.1][D2.2][D3 ]
E:                                                             [E1.1][E1.2][E2 ][E3 ]
F:   [F1.1][F1.2][F2 ]
G:                                              [G1.1][G1.2][G2 ]
```

---

## 二、前置准备（Day 0，正式开发前）

### 环境确认清单

```bash
# 1. 确认 Python 版本
python3 --version   # 需要 >=3.10

# 2. 确认现有测试可以跑通
cd /media/hzm/data_disk/EmbodiedAgentsSys
python -m pytest tests/test_task_planner_standalone.py tests/test_failure_recorder.py \
                 tests/test_event_bus.py tests/test_capability_registry.py -v

# 3. 确认 RoboClaw 源码可读取
ls /media/hzm/data_disk/RoboClaw/roboclaw/providers/
ls /media/hzm/data_disk/RoboClaw/roboclaw/agent/

# 4. 创建开发分支
git checkout -b feature/roboclaw-integration
```

### 创建目录结构

```bash
mkdir -p agents/llm agents/memory agents/channels agents/data agents/training
touch agents/llm/__init__.py agents/memory/__init__.py agents/channels/__init__.py
touch agents/training/__init__.py
```

### pyproject.toml 准备

在 `[project.optional-dependencies]` 中预先添加（即使暂未安装）：
```toml
[project.optional-dependencies]
llm      = ["litellm>=1.40", "json-repair>=0.28"]
channels = ["python-telegram-bot>=21.0", "lark-oapi>=1.3",
            "pydantic>=2.0", "pydantic-settings>=2.0"]
vision   = ["opencv-python>=4.8"]
all      = ["embodied-agents-sys[llm,channels,vision]"]
```

---

## 三、Phase A：LLM 抽象层（Day 1-4）

### Day 1 — A1.1：LLMProvider ABC

**目标**：建立 `agents/llm/provider.py`，所有后续 LLM 调用都通过此接口。

**输入**：`/media/hzm/data_disk/RoboClaw/roboclaw/providers/base.py`（208行）

**输出**：`agents/llm/provider.py`

**具体任务**：

1. 复制 `base.py` 到 `agents/llm/provider.py`
2. 全局替换：
   - `from loguru import logger` → `import logging; logger = logging.getLogger(__name__)`
   - `logger.warning(...)` → `logger.warning(...)`（loguru 格式 `{}` → `%s` 风格）

   > 注意：loguru 用 `{}` 占位符，标准 logging 用 `%s`。批量替换时注意每条 log 语句。

3. 删除 RoboClaw 特有注释，保留所有逻辑不变：
   - `LLMProvider` ABC（`chat()`、`chat_with_retry()`）
   - `LLMResponse` dataclass
   - `ToolCallRequest` dataclass
   - `GenerationSettings` dataclass
   - `_sanitize_empty_content()`、`_strip_image_content()` 静态方法
   - `_CHAT_RETRY_DELAYS = (1, 2, 4)`
   - `_TRANSIENT_ERROR_MARKERS`、`_IMAGE_UNSUPPORTED_MARKERS`

**验证**：
```bash
python -c "from agents.llm.provider import LLMProvider, LLMResponse; print('OK')"
```

---

### Day 2 — A1.2：OllamaProvider 包装

**目标**：将 `OllamaClient` 现有逻辑包装为 `LLMProvider` 实现；
修改 `TaskPlanner` 和 `SemanticParser` 接入新接口。

**输入**：
- `agents/clients/ollama.py`（现有，208行）
- `agents/components/task_planner.py`（现有，224行）
- `agents/components/semantic_parser.py`（现有，171行）

**输出**：
- `agents/llm/ollama_provider.py`（新建）
- `agents/llm/__init__.py`（更新）
- `agents/components/task_planner.py`（修改）
- `agents/components/semantic_parser.py`（修改）

**具体任务**：

**`agents/llm/ollama_provider.py`**：
```python
# 接口要求：
class OllamaProvider(LLMProvider):
    def __init__(self, host="127.0.0.1", port=11434, model="qwen2.5:3b"):
        # 内部复用 OllamaClient._inference() 的 httpx 调用逻辑
        # 不引入 ollama SDK，保持现有 httpx 方式
        ...

    async def chat(self, messages, tools=None, model=None, **kwargs) -> LLMResponse:
        # 将 messages 格式转为 OllamaClient 期望的格式
        # 将响应包装为 LLMResponse
        ...

    def get_default_model(self) -> str:
        return self._model
```

**修改 `task_planner.py`**（最小改动原则）：
```python
# TaskPlanner.__init__ 新增参数：
def __init__(
    self,
    ...,
    llm_provider: Optional["LLMProvider"] = None,   # 新增
):
    self._llm_provider = llm_provider
    # 原有 _ollama_client 逻辑保持，若 llm_provider 非 None 则优先使用

# TaskPlanner.plan() 修改：
async def plan(self, instruction: str) -> TaskPlan:
    if self._llm_provider:
        return await self._plan_with_provider(instruction)
    # 原有逻辑不变（ollama SDK 或 mock）
    ...

async def _plan_with_provider(self, instruction: str) -> TaskPlan:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": self._build_prompt(instruction)},
    ]
    response = await self._llm_provider.chat_with_retry(messages)
    actions = self._parse_plan_json(response.content or "")
    ...
```

**`semantic_parser.py`** 同样模式添加 `llm_provider` 参数。

**`agents/llm/__init__.py`**：
```python
from .provider import LLMProvider, LLMResponse, GenerationSettings
from .ollama_provider import OllamaProvider
```

**验证**：
```bash
python -m pytest tests/test_task_planner_standalone.py -v  # 原有测试必须全通
python -c "
from agents.llm import OllamaProvider, LLMProvider
from agents.components.task_planner import TaskPlanner
p = OllamaProvider()
tp = TaskPlanner(llm_provider=p)
print('OllamaProvider 注入成功')
"
```

**新增测试** `tests/test_llm_provider.py` — A1 部分：
```python
# 仅 A1 范围的测试（mock 级别，无需真实 Ollama）
def test_llm_response_has_tool_calls():
def test_retry_delays_constant():
def test_sanitize_empty_content():
async def test_task_planner_with_mock_provider():
async def test_task_planner_backward_compat_mock():
```

---

### Day 3 — A2.1：ProviderRegistry + LiteLLMProvider（上）

**目标**：移植 provider registry，建立 LiteLLMProvider 框架。

**输入**：
- `/media/hzm/data_disk/RoboClaw/roboclaw/providers/registry.py`
- `/media/hzm/data_disk/RoboClaw/roboclaw/providers/litellm_provider.py`

**输出**：
- `agents/llm/registry.py`
- `agents/llm/litellm_provider.py`（框架，Chat 核心逻辑）

**具体任务**：

**`agents/llm/registry.py`**：
- 完整移植 `ProviderSpec` dataclass 和 `PROVIDERS` 列表
- 移植 `find_by_model()` 和 `find_gateway()` 函数
- 仅改 import 路径，逻辑零改动

**`agents/llm/litellm_provider.py`**（今天完成 `chat()` 方法）：
- 移植整个 `LiteLLMProvider` 类
- loguru → logging 替换
- `from roboclaw.providers.base import ...` → `from .provider import ...`
- `from roboclaw.providers.registry import ...` → `from .registry import ...`
- 依赖确认：`pip install litellm json-repair`

**验证**：
```bash
pip install litellm json-repair
python -c "from agents.llm.registry import find_by_model; print(find_by_model('claude-opus-4-5'))"
python -c "from agents.llm.litellm_provider import LiteLLMProvider; print('OK')"
```

---

### Day 4 — A2.2：LiteLLMProvider 完成 + 集成测试

**目标**：完成 `LiteLLMProvider` 所有方法，更新 `__init__.py`，写完整测试。

**具体任务**：

1. 确认 `LiteLLMProvider` 所有方法完整：
   - `_apply_cache_control()`
   - `_resolve_model()`
   - `_parse_response()`
   - `_supports_cache_control()`
   - `_apply_model_overrides()`

2. 更新 `agents/llm/__init__.py`：
```python
from .provider import LLMProvider, LLMResponse, GenerationSettings
from .ollama_provider import OllamaProvider

try:
    from .litellm_provider import LiteLLMProvider
except ImportError:
    LiteLLMProvider = None  # litellm 未安装时优雅降级
```

3. 新增配置加载器 `agents/llm/config.py`：
```python
def load_llm_provider_from_config(config_path: str | Path | None = None) -> LLMProvider:
    """从 config/llm_config.yaml 实例化对应的 LLMProvider。"""
    # 读取 yaml → 根据 provider 字段选择 OllamaProvider 或 LiteLLMProvider
    ...
```

4. 创建 `config/llm_config.yaml`：
```yaml
provider: ollama
model: qwen2.5:3b
api_key: ""
api_base: ""
max_tokens: 512
temperature: 0.1
retry_delays: [1, 2, 4]
```

**完成 `tests/test_llm_provider.py`** 全部用例：
```python
async def test_ollama_provider_chat_mock():
    """mock httpx，验证 OllamaProvider.chat() 返回 LLMResponse"""

async def test_litellm_provider_retry_429():
    """mock acompletion 抛 RateLimitError，验证重试 3 次后返回"""

async def test_litellm_provider_retry_transient():
    """mock 返回 finish_reason='error' + content='503'，验证退避"""

def test_load_config_ollama():
    """验证 llm_config.yaml provider=ollama → OllamaProvider 实例"""

def test_load_config_litellm():
    """验证 provider=litellm → LiteLLMProvider 实例"""

async def test_task_planner_with_ollama_provider():
    """端到端：OllamaProvider mock → TaskPlanner.plan() → TaskPlan"""
```

**Day 4 验收标准**：
```bash
python -m pytest tests/test_llm_provider.py -v  # 全部通过
python -m pytest tests/test_task_planner_standalone.py -v  # 原有测试不回归
```

---

## 四、Phase F：Skill 格式统一（Day 1-3，与 A 并行）

> Phase F 从 Day 1 开始，与 Phase A 并行。由不同开发者或利用碎片时间推进。

### Day 1（F1.1）— MDSkillConfig 扩展

**目标**：在 `md_skill_adapter.py` 中添加 `requires` 和 `eap` 字段解析。

**输入**：`agents/skills/md_skill_adapter.py`（现有）

**具体改动**：

1. 在 `MDSkillConfig` dataclass 中新增字段：
```python
@dataclass
class MDSkillConfig:
    # 现有字段不变 ...
    requires_bins: list[str] = field(default_factory=list)
    requires_env: list[str] = field(default_factory=list)
    always: bool = False
    # EAP 扩展字段（论文 §3.2）
    eap_has_reverse: bool = False
    eap_reverse_skill: str = ""
```

2. 在 `SKILLMDParser._parse_frontmatter()` 中解析新字段：
```python
requires = frontmatter.get("requires", {})
config.requires_bins = requires.get("bins", [])
config.requires_env  = requires.get("env", [])
config.always        = frontmatter.get("always", False)
eap = frontmatter.get("eap", {})
config.eap_has_reverse   = eap.get("has_reverse", False)
config.eap_reverse_skill = eap.get("reverse_skill", "")
```

### Day 2（F1.2）— availability 检查

**目标**：实现 `MDSkillManager.check_availability()`。

```python
def check_availability(self, skill_name: str) -> tuple[bool, list[str]]:
    """
    检查 skill 的运行时依赖是否满足。
    Returns: (is_available, missing_list)
    """
    import shutil, os
    skill = self.get_skill(skill_name)
    if skill is None:
        return False, [f"skill '{skill_name}' not found"]
    missing = []
    for bin_name in skill.requires_bins:
        if shutil.which(bin_name) is None:
            missing.append(f"bin:{bin_name}")
    for env_name in skill.requires_env:
        if not os.getenv(env_name):
            missing.append(f"env:{env_name}")
    return len(missing) == 0, missing

def discover_skills(self) -> list[dict]:
    """返回所有 skill 的元数据 + 可用性状态。"""
    results = []
    for name, cfg in self._skills.items():
        available, missing = self.check_availability(name)
        results.append({
            "name": name,
            "description": cfg.description,
            "available": available,
            "missing_deps": missing,
            "eap_has_reverse": cfg.eap_has_reverse,
            "eap_reverse_skill": cfg.eap_reverse_skill,
        })
    return results
```

### Day 3（F2）— Skill 格式测试 + 文档

**新增 `tests/test_skill_format.py`**：
```python
def test_parse_requires_bins():
def test_parse_requires_env():
def test_parse_eap_metadata():
def test_check_availability_missing_bin():
def test_check_availability_missing_env():
def test_check_availability_all_satisfied():
def test_backward_compat_no_requires():
def test_discover_skills_structure():
```

**新增 `docs/skill_format.md`**：完整 frontmatter 格式规范文档。

**验收**：
```bash
python -m pytest tests/test_skill_format.py -v  # 全部通过
```

---

## 五、Phase B：结构化机器人记忆 + CoT 规划（Day 6-10）

> 依赖：Phase A 完成（`LLMProvider` 接口可用）。

### Day 6 — B1.1：RobotMemoryState 数据结构

**目标**：实现论文 §3.1 的三层结构化记忆 m_t = (r_t, g_t, w_t)。

**输出**：`agents/memory/robot_memory.py`

**具体接口**（完整实现，非伪代码）：

```python
# agents/memory/robot_memory.py

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal, Optional


class SubtaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


@dataclass
class Subtask:
    id: str
    description: str
    skill_id: str
    status: SubtaskStatus = SubtaskStatus.PENDING
    success_criteria: str = ""
    retry_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def start(self) -> None:
        self.status = SubtaskStatus.RUNNING
        self.started_at = datetime.now().isoformat()

    def mark_done(self) -> None:
        self.status = SubtaskStatus.DONE
        self.completed_at = datetime.now().isoformat()

    def mark_failed(self) -> None:
        self.status = SubtaskStatus.FAILED
        self.retry_count += 1
        self.completed_at = datetime.now().isoformat()

    def to_prompt_line(self) -> str:
        icon = {"done":"✓","failed":"✗","running":"→","pending":"○"}[self.status]
        retry_str = f" [retry={self.retry_count}]" if self.retry_count > 0 else ""
        return f"  {icon} [{self.id}] {self.description} (skill={self.skill_id}){retry_str}"


@dataclass
class RoleIdentity:
    """r_t：当前运行模式 + 可用工具列表。"""
    mode: Literal["data_collection", "task_execution"] = "task_execution"
    robot_type: str = ""
    available_tools: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        tools_str = ", ".join(self.available_tools) if self.available_tools else "none"
        return (
            f"Mode: {self.mode}\n"
            f"Robot: {self.robot_type}\n"
            f"Available Tools: {tools_str}"
        )


@dataclass
class TaskGraph:
    """g_t：全局任务分解 + 子任务状态追踪。"""
    global_task: str = ""
    subtasks: list[Subtask] = field(default_factory=list)

    @property
    def current_subtask(self) -> Optional[Subtask]:
        for s in self.subtasks:
            if s.status in (SubtaskStatus.RUNNING, SubtaskStatus.PENDING):
                return s
        return None

    @property
    def is_complete(self) -> bool:
        return all(s.status == SubtaskStatus.DONE for s in self.subtasks)

    @property
    def has_failed(self) -> bool:
        return any(s.status == SubtaskStatus.FAILED for s in self.subtasks)

    def get_by_id(self, subtask_id: str) -> Optional[Subtask]:
        return next((s for s in self.subtasks if s.id == subtask_id), None)

    def to_prompt_block(self) -> str:
        lines = [f"Global Task: {self.global_task}", "Subtasks:"]
        lines.extend(s.to_prompt_line() for s in self.subtasks)
        done = sum(1 for s in self.subtasks if s.status == SubtaskStatus.DONE)
        lines.append(f"Progress: {done}/{len(self.subtasks)} subtasks completed")
        return "\n".join(lines)


@dataclass
class WorkingMemory:
    """w_t：当前执行的短期上下文（滚动窗口）。"""
    current_skill_id: str = ""
    tool_call_history: list[str] = field(default_factory=list)
    env_summary: str = ""
    robot_stats: dict = field(default_factory=dict)
    _MAX_HISTORY = 10

    def add_tool_call(self, tool_name: str, result_summary: str) -> None:
        entry = f"{tool_name}: {result_summary[:120]}"
        self.tool_call_history.append(entry)
        if len(self.tool_call_history) > self._MAX_HISTORY:
            self.tool_call_history = self.tool_call_history[-self._MAX_HISTORY:]

    def to_prompt_block(self) -> str:
        lines = [f"Current Skill: {self.current_skill_id or 'none'}"]
        if self.env_summary:
            lines.append(f"Env: {self.env_summary[:200]}")
        if self.robot_stats:
            lines.append(f"Robot Stats: {json.dumps(self.robot_stats, ensure_ascii=False)[:200]}")
        if self.tool_call_history:
            lines.append("Recent Actions:")
            lines.extend(f"  - {h}" for h in self.tool_call_history[-5:])
        return "\n".join(lines)


@dataclass
class RobotMemoryState:
    """m_t = (r_t, g_t, w_t)：论文 §3.1 完整结构化记忆状态。"""
    role: RoleIdentity = field(default_factory=RoleIdentity)
    task_graph: TaskGraph = field(default_factory=TaskGraph)
    working: WorkingMemory = field(default_factory=WorkingMemory)

    def to_context_block(self) -> str:
        """生成注入 VLM system prompt 的完整记忆上下文。"""
        sections = [
            "## Role Identity\n" + self.role.to_prompt_block(),
            "## Task-Level Memory\n" + self.task_graph.to_prompt_block(),
            "## Working Memory\n" + self.working.to_prompt_block(),
        ]
        return "\n\n".join(sections)
```

**验证**：
```bash
python -c "
from agents.memory.robot_memory import RobotMemoryState, TaskGraph, Subtask
m = RobotMemoryState()
m.task_graph.global_task = '把杯子放到货架上'
m.task_graph.subtasks = [
    Subtask('s1','导航到桌子','navigate'),
    Subtask('s2','抓取杯子','grasp'),
    Subtask('s3','放置杯子','place'),
]
m.task_graph.subtasks[0].start()
print(m.to_context_block())
"
```

---

### Day 7 — B1.2：failure_log + TaskPlanner 集成

**目标**：实现失败记录写入 HISTORY.md；TaskPlanner 接入结构化记忆。

**输出**：
- `agents/memory/failure_log.py`（新建）
- `agents/memory/__init__.py`（更新）
- `agents/components/task_planner.py`（修改）
- `agents/data/failure_recorder.py`（修改）

**`agents/memory/failure_log.py`**：
```python
from pathlib import Path
from agents.data.failure_recorder import FailureRecord


def append_failure(record: FailureRecord, history_file: Path) -> None:
    """追加一条失败记录到 HISTORY.md（grep 可搜索格式）。"""
    line = (
        f"[{record.timestamp[:16]}] FAILURE "
        f"skill={record.failed_step_id} "
        f"type={record.error_type} "
        f"scene={record.scene_spec.scene_type} "
        f"task={record.scene_spec.task_description[:80]}\n"
    )
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(line)


def query_failures(history_file: Path, skill_id: str, limit: int = 5) -> list[str]:
    """从 HISTORY.md 检索指定 skill 的历史失败记录。"""
    if not history_file.exists():
        return []
    matches = [
        line for line in history_file.read_text(encoding="utf-8").splitlines()
        if f"skill={skill_id}" in line
    ]
    return matches[-limit:]
```

**修改 `agents/components/task_planner.py`**：
```python
# TaskPlanner.__init__ 新增两个参数：
def __init__(
    self,
    ...,
    robot_memory: Optional["RobotMemoryState"] = None,   # 新增
    history_file: Optional[Path] = None,                  # 新增
):
    self._robot_memory = robot_memory
    self._history_file = history_file

# _build_prompt() 修改：
def _build_prompt(self, instruction: str) -> str:
    parts = [f"指令：{instruction}"]

    # 新增：注入结构化记忆上下文（论文 §3.1）
    if self._robot_memory:
        parts.insert(0, self._robot_memory.to_context_block())

    # 新增：从 HISTORY.md 检索失败历史
    if self._history_file and self._robot_memory:
        current = self._robot_memory.task_graph.current_subtask
        if current:
            failures = query_failures(self._history_file, current.skill_id)
            if failures:
                parts.append("历史失败记录（请参考避免重复）：")
                parts.extend(f"  {f}" for f in failures)

    # 原有逻辑保留 ...
    if self._semantic_map:
        parts.append(self._semantic_map.summary_for_prompt())
    ...
```

**修改 `agents/data/failure_recorder.py`**：
```python
# FailureDataRecorder.record() 新增可选参数：
async def record(
    self,
    record: FailureRecord,
    history_file: Optional[Path] = None,      # 新增
    robot_memory: Optional[Any] = None,        # 新增（RobotMemoryState）
) -> Path:
    # 原有写磁盘逻辑不变
    saved_path = await self._write_to_disk(record)

    # 新增：写入 HISTORY.md
    if history_file:
        from agents.memory.failure_log import append_failure
        append_failure(record, history_file)

    # 新增：更新 task_graph 状态
    if robot_memory and hasattr(robot_memory, "task_graph"):
        robot_memory.task_graph.get_by_id(record.failed_step_id)
        # 调用 subtask.mark_failed() 若找到

    return saved_path
```

---

### Day 8 — B2.1：CoTTaskPlanner（上）

**目标**：实现 5 步 CoT 推理规划器框架和 prompt 设计。

**输出**：`agents/components/task_planner.py`（新增 `CoTTaskPlanner` 类）

**`CoTDecision` 数据结构**：
```python
@dataclass
class CoTDecision:
    # 推理过程（论文 Fig. 2 五步）
    observation: str      # 步骤1：观察到什么
    objective: str        # 步骤2：当前子任务目标
    evaluation: Literal["satisfied", "stuck", "progressing"]  # 步骤3：状态评估
    strategy: Literal["continue", "switch_policy", "call_human"]  # 步骤4：策略选择
    # 行动决策
    subtask_id: str       # 步骤5：选择执行的子任务
    skill_id: str
    instruction: str      # 传给 VLA 策略的自然语言指令 l_t
    success_criteria: str # 本子任务的成功标准
    raw_reasoning: str = ""  # LLM 原始输出（调试用）
```

**CoT System Prompt 设计**（关键，需反复迭代）：
```python
_COT_SYSTEM_PROMPT = """\
你是一个机器人任务执行智能体，使用链式思维（CoT）进行决策。

给定当前的结构化记忆状态（m_t）和环境观察（o_t），按以下5步推理后输出决策。

【推理步骤】（必须按顺序回答）
1. 观察（Observation）：场景中有什么？物体在哪里？机器人状态如何？
2. 目标（Objective）：当前子任务是什么？成功标准是什么？
3. 评估（Evaluation）：
   - satisfied：当前状态已满足成功标准，子任务完成
   - progressing：正在执行中，继续等待
   - stuck：多次尝试未达到成功标准，需要干预
4. 策略（Strategy）：
   - continue：继续执行当前或下一个子任务
   - switch_policy：切换到备选策略（evaluation=stuck时）
   - call_human：无法自主恢复（多次switch_policy仍失败）
5. 行动（Action）：输出具体的子任务ID、技能ID和自然语言指令

【输出格式】严格JSON，不含其他文本：
{
  "reasoning": {
    "observation": "...",
    "objective": "...",
    "evaluation": "satisfied|stuck|progressing",
    "strategy": "continue|switch_policy|call_human"
  },
  "subtask_id": "s1",
  "skill_id": "manipulation.grasp",
  "instruction": "抓取桌上的红色杯子",
  "success_criteria": "杯子被稳定夹持，离开桌面超过5cm"
}
"""
```

---

### Day 9 — B2.2：CoTTaskPlanner（下）+ 解析逻辑

**目标**：完成 `CoTTaskPlanner.decide_next_action()` 的完整实现。

```python
class CoTTaskPlanner:
    def __init__(
        self,
        llm_provider: LLMProvider,
        memory: RobotMemoryState,
        model: Optional[str] = None,
    ):
        self._provider = llm_provider
        self._memory = memory
        self._model = model

    async def decide_next_action(
        self,
        observation: str,     # Env Summary 工具返回的场景描述
        robot_stats: dict,    # Fetch Robot Stats 工具返回的状态
    ) -> CoTDecision:
        # 1. 更新 working memory
        self._memory.working.env_summary = observation
        self._memory.working.robot_stats = robot_stats

        # 2. 构建消息
        messages = [
            {"role": "system", "content": _COT_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_message()},
        ]

        # 3. LLM 调用（带重试）
        response = await self._provider.chat_with_retry(
            messages=messages,
            model=self._model,
            temperature=0.1,    # CoT 规划要低温度
            max_tokens=512,
        )

        # 4. 解析 JSON
        return self._parse_decision(response.content or "")

    def _build_user_message(self) -> str:
        return (
            "当前结构化记忆状态：\n"
            + self._memory.to_context_block()
        )

    def _parse_decision(self, text: str) -> CoTDecision:
        """解析 CoT JSON，失败时返回安全的默认决策。"""
        import json, re
        # 提取 JSON（容忍 LLM 附加文本）
        match = re.search(r'\{[\s\S]*\}', text)
        if not match:
            return self._fallback_decision("JSON not found", text)
        try:
            data = json.loads(match.group())
            reasoning = data.get("reasoning", {})
            return CoTDecision(
                observation=reasoning.get("observation", ""),
                objective=reasoning.get("objective", ""),
                evaluation=reasoning.get("evaluation", "progressing"),
                strategy=reasoning.get("strategy", "continue"),
                subtask_id=data.get("subtask_id", ""),
                skill_id=data.get("skill_id", ""),
                instruction=data.get("instruction", ""),
                success_criteria=data.get("success_criteria", ""),
                raw_reasoning=text,
            )
        except (json.JSONDecodeError, KeyError) as e:
            return self._fallback_decision(str(e), text)

    def _fallback_decision(self, reason: str, raw: str) -> CoTDecision:
        """解析失败时的安全降级：返回 call_human。"""
        import logging
        logging.getLogger(__name__).warning(
            "CoT parsing failed: %s, raw=%s", reason, raw[:200]
        )
        current = self._memory.task_graph.current_subtask
        return CoTDecision(
            observation="解析失败",
            objective="",
            evaluation="stuck",
            strategy="call_human",
            subtask_id=current.id if current else "",
            skill_id=current.skill_id if current else "",
            instruction="",
            success_criteria="",
            raw_reasoning=raw,
        )
```

---

### Day 10 — B3：完整测试

**新增/完成 `tests/test_robot_memory.py`**：

```python
# 数据结构测试
def test_subtask_state_transitions():
    """pending → running → done/failed 状态机验证"""

def test_task_graph_current_subtask():
    """验证 current_subtask 返回第一个 running/pending"""

def test_task_graph_is_complete():
    """所有子任务 done → is_complete=True"""

def test_working_memory_rolling_window():
    """超过 10 条时旧记录被丢弃"""

def test_robot_memory_context_block_format():
    """to_context_block() 包含三个 section"""

# 规划器测试
async def test_cot_planner_parses_valid_json():
    """mock LLM 返回合法 CoT JSON → CoTDecision 正确解析"""

async def test_cot_planner_fallback_on_bad_json():
    """mock LLM 返回非 JSON → fallback decision (strategy=call_human)"""

async def test_cot_planner_updates_working_memory():
    """decide_next_action() 后 working.env_summary 被更新"""

# 失败记录测试
def test_append_failure_creates_file():
    """首次写入创建 HISTORY.md"""

def test_query_failures_by_skill_id():
    """写入多条，skill_id 过滤正确"""

def test_failure_recorder_writes_history(tmp_path):
    """FailureDataRecorder.record() + history_file 参数"""

async def test_task_planner_injects_memory_context():
    """TaskPlanner._build_prompt() 包含 robot_memory.to_context_block()"""

async def test_task_planner_injects_failure_history():
    """HISTORY.md 有失败记录时 prompt 包含相关历史"""
```

**Day 10 验收标准**：
```bash
python -m pytest tests/test_robot_memory.py -v        # 全部通过
python -m pytest tests/test_llm_provider.py -v         # 不回归
python -m pytest tests/test_task_planner_standalone.py -v  # 不回归
```

---

## 六、Phase C：AgentLoop + 多平台渠道（Day 11-15）

> 依赖：Phase A 完成。与 Phase B 并行，日历上安排在 Day 11 开始。

### Day 11 — C1.1：MessageBus + BaseChannel

**目标**：移植消息总线和渠道基类。

**输入**：
- `RoboClaw/roboclaw/bus/queue.py`（36行）
- `RoboClaw/roboclaw/bus/events.py`
- `RoboClaw/roboclaw/channels/base.py`

**输出**：
- `agents/channels/bus.py`
- `agents/channels/events.py`
- `agents/channels/base.py`

**`agents/channels/bus.py`**：直接复制，仅改 import 路径（3处）。

**`agents/channels/events.py`**：复制后在 `InboundMessage` 新增一个字段：
```python
robot_id: str = ""   # 目标机器人 ID（多机场景预留）
```

**`agents/channels/base.py`**：复制后改动：
- import 路径更新
- `transcribe_audio()` 的 `from roboclaw.providers.transcription` → `try/except ImportError`

**验证**：
```bash
python -c "
from agents.channels.bus import MessageBus
from agents.channels.events import InboundMessage, OutboundMessage
from agents.channels.base import BaseChannel
bus = MessageBus()
print(f'inbound_size={bus.inbound_size}')
"
```

---

### Day 12 — C1.2：AgentLoop 移植 + RobotTools

**目标**：移植 `AgentLoop`，裁剪不需要的子系统，新增机器人工具接口。

**输入**：`RoboClaw/roboclaw/agent/loop.py`（511行）

**输出**：
- `agents/channels/agent_loop.py`（移植 + 裁剪）
- `agents/channels/robot_tools.py`（新建，论文 MCP 工具接口）

**`agents/channels/agent_loop.py` 裁剪说明**：
| 保留 | 裁剪 | 原因 |
|------|------|------|
| `AgentLoop.__init__()` 核心参数 | `SubagentManager` | 当前不需要子智能体 |
| `_run_agent_loop()` | `CronTool` | 当前不需要定时任务 |
| `_process_message()` | `SpawnTool` | 当前不需要 spawn |
| `run()` 主循环 | tty_handoff | 不需要 TTY |
| `process_direct()` | MCP 相关（保留接口，lazy init）| 保留接口不删 |

新增 `_register_robot_tools()` 方法：
```python
def _register_robot_tools(
    self,
    cot_planner: Optional["CoTTaskPlanner"] = None,
    skill_registry: Optional[Any] = None,
) -> None:
    """注册机器人专用工具到 ToolRegistry。"""
    from agents.channels.robot_tools import (
        EnvSummaryTool, FetchRobotStatsTool, CallHumanTool,
    )
    self.tools.register(EnvSummaryTool())
    self.tools.register(FetchRobotStatsTool())
    self.tools.register(CallHumanTool(bus=self.bus))
    if cot_planner:
        from agents.channels.robot_tools import TaskPlannerTool
        self.tools.register(TaskPlannerTool(planner=cot_planner))
```

**`agents/channels/robot_tools.py`** — 工具接口（今天建框架，E 阶段完善）：
```python
class EnvSummaryTool:
    name = "env_summary"
    description = "获取当前环境的视觉摘要（场景中有什么物体，位置关系）"

    async def execute(self, **kwargs) -> str:
        # Phase C 先返回 mock，Phase E 对接 GroundedSAM/SemanticMap
        return "Mock env summary: table with cup at center"

class FetchRobotStatsTool:
    name = "fetch_robot_stats"
    description = "获取机器人当前关节状态和末端执行器位姿"

    async def execute(self, **kwargs) -> str:
        return "{}"  # Phase C mock，Phase E 对接 arm_adapter

class CallHumanTool:
    name = "call_human"
    description = "当自主恢复失败时，向人类操作员发送求助消息"

    def __init__(self, bus: "MessageBus"): ...

    async def execute(self, reason: str, severity: str = "warning") -> str:
        from agents.channels.events import OutboundMessage
        msg = OutboundMessage(
            channel="broadcast",
            chat_id="all",
            content=f"[{severity.upper()}] 机器人需要帮助: {reason}",
        )
        await self.bus.publish_outbound(msg)
        return f"求助消息已发送: {reason}"
```

---

### Day 13 — C2.1：Telegram 渠道

**目标**：移植 Telegram 渠道，安装 pydantic。

```bash
pip install "pydantic>=2.0" "pydantic-settings>=2.0" "python-telegram-bot>=21.0"
```

**输入**：`RoboClaw/roboclaw/channels/telegram.py`

**输出**：`agents/channels/telegram_channel.py`

**移植改动**：
1. `from roboclaw.config.schema import Base` → 本地 `pydantic.BaseModel`
2. 去掉 `from roboclaw.config.paths import get_media_dir`（暂不需要 media 路径）
3. 更新所有 import 路径

**本地 pydantic Base**（在 `agents/channels/base_config.py` 中定义）：
```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class ChannelBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

**`config/channels_config.yaml`**（创建）：
```yaml
telegram:
  enabled: false
  token: ""
  allow_from: []
  send_progress: true

feishu:
  enabled: false
  app_id: ""
  app_secret: ""
  allow_from: ["*"]
  send_progress: true
```

---

### Day 14 — C2.2：飞书渠道 + EventBus 桥接

**目标**：移植飞书渠道；修改 EventBus 实现桥接。

```bash
pip install "lark-oapi>=1.3"
```

**飞书渠道移植**：同 Telegram，改动模式一致。

**修改 `agents/events/bus.py`**：
```python
# EventBus 新增方法：
def set_outbound_bridge(
    self,
    bus: "MessageBus",
    chat_id: str,
    channel: str,
) -> None:
    """将 CRITICAL/HIGH 事件桥接到 MessageBus outbound。"""
    self._outbound_bridge = bus
    self._bridge_chat_id = chat_id
    self._bridge_channel = channel

# EventBus.publish() 修改（在现有 publish 逻辑后追加）：
async def publish(self, event: Event) -> None:
    # 原有订阅者通知逻辑 ...
    await self._notify_subscribers(event)

    # 新增：高优先级事件转发到外部渠道
    if (hasattr(self, "_outbound_bridge")
        and event.priority in (EventPriority.CRITICAL, EventPriority.HIGH)):
        from agents.channels.events import OutboundMessage
        msg = OutboundMessage(
            channel=self._bridge_channel,
            chat_id=self._bridge_chat_id,
            content=f"[{event.priority.name}] {event.type}: {event.data}",
        )
        await self._outbound_bridge.publish_outbound(msg)
```

---

### Day 15 — C3：集成测试

**新增/完成 `tests/test_channels.py`**：

```python
async def test_message_bus_publish_consume():
async def test_base_channel_allow_from_star():
async def test_base_channel_allow_from_empty_denies_all():
async def test_base_channel_allow_from_specific_id():
async def test_agent_loop_process_direct():
    """AgentLoop.process_direct() 返回非空字符串"""
async def test_call_human_tool_publishes_outbound():
async def test_eventbus_bridge_high_priority():
    """HIGH 优先级事件 → MessageBus outbound 队列"""
async def test_eventbus_bridge_low_priority_not_forwarded():
    """LOW 优先级事件不转发"""
async def test_asyncio_thread_bridge():
    """模拟 ROS2 跨线程场景：run_coroutine_threadsafe"""
```

**Day 15 验收标准**：
```bash
python -m pytest tests/test_channels.py -v              # 全部通过
python -m pytest tests/test_event_bus.py -v             # 原有测试不回归
```

---

## 七、Phase D：EAP 自主数据采集（Day 16-22）

> 依赖：Phase B（RobotMemoryState、CoTTaskPlanner 可用）。

### Day 16 — D1：EAP 数据结构

**输出**：`agents/data/eap.py`

**完整接口**：

```python
# agents/data/eap.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional
import uuid
from datetime import datetime


@dataclass
class EAPPolicy:
    policy_id: str
    direction: Literal["forward", "reverse"]
    skill_id: str
    instruction_template: str   # 支持 {task} 占位符
    success_criteria: str


@dataclass
class EAPPair:
    task_name: str
    forward: EAPPolicy
    reverse: EAPPolicy
    max_retries: int = 3
    trajectory_save_dir: Path = Path("~/.embodied_agents/datasets")

    @classmethod
    def from_skill_metadata(cls, skill_meta: dict) -> Optional["EAPPair"]:
        """从 MDSkillConfig 的 eap 字段自动构建 EAPPair。"""
        if not skill_meta.get("eap_has_reverse"):
            return None
        forward = EAPPolicy(
            policy_id=f"{skill_meta['name']}_forward",
            direction="forward",
            skill_id=skill_meta["name"],
            instruction_template=skill_meta.get("description", "执行 {task}"),
            success_criteria=skill_meta.get("success_criteria", ""),
        )
        reverse = EAPPolicy(
            policy_id=f"{skill_meta['eap_reverse_skill']}_reverse",
            direction="reverse",
            skill_id=skill_meta["eap_reverse_skill"],
            instruction_template=f"复位：{skill_meta.get('description', '')}",
            success_criteria="环境恢复到初始状态",
        )
        return cls(
            task_name=skill_meta["name"],
            forward=forward,
            reverse=reverse,
        )


@dataclass
class EAPTrajectory:
    pair_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    direction: Literal["forward", "reverse"] = "forward"
    episode_id: int = 0
    observations: list[dict] = field(default_factory=list)   # o_t
    joint_states: list[dict] = field(default_factory=list)   # q_t
    actions: list[dict] = field(default_factory=list)         # a_t
    instruction: str = ""                                     # l_t
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    failure_reason: str = ""

    def add_step(
        self,
        observation: dict,
        joint_state: dict,
        action: dict,
    ) -> None:
        self.observations.append(observation)
        self.joint_states.append(joint_state)
        self.actions.append(action)
```

---

### Day 17-18 — D2.1/D2.2：EAPOrchestrator

**输出**：`agents/data/eap_orchestrator.py`

**完整实现**（两天完成）：

```python
# agents/data/eap_orchestrator.py

import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class EAPOrchestrator:
    """
    论文 §3.2 自主数据采集编排器。
    交替执行 正向策略 → 评估 → 逆向策略 → 保存轨迹。
    """

    def __init__(
        self,
        pair: "EAPPair",
        cot_planner: "CoTTaskPlanner",
        skill_executor: Any,    # SkillRegistry or callable
        bus: "MessageBus",
        memory: "RobotMemoryState",
        trajectory_recorder: "TrajectoryRecorder",
    ):
        self._pair = pair
        self._planner = cot_planner
        self._executor = skill_executor
        self._bus = bus
        self._memory = memory
        self._recorder = trajectory_recorder
        self._stop_flag = asyncio.Event()
        self._consecutive_failures = 0

    async def run_collection_loop(
        self,
        target_trajectories: int = 50,
        on_collected: Optional[Callable] = None,
    ) -> list["EAPTrajectory"]:
        """主采集循环：持续执行 EAP 直到达到目标数量或收到停止信号。"""
        collected = []
        episode = 0

        # 切换到数据采集模式
        self._memory.role.mode = "data_collection"
        self._memory.role.available_tools = [
            "env_summary", "fetch_robot_stats", "call_human"
        ]

        logger.info(
            "EAP collection started: task=%s, target=%d",
            self._pair.task_name, target_trajectories,
        )

        while len(collected) < target_trajectories and not self._stop_flag.is_set():
            episode += 1
            logger.info("EAP episode %d/%d", episode, target_trajectories)

            # --- 正向策略 ---
            fwd_traj = EAPTrajectory(
                pair_id=self._pair.task_name,
                direction="forward",
                episode_id=episode,
                instruction=self._pair.forward.instruction_template,
            )
            self._memory.working.current_skill_id = self._pair.forward.skill_id
            fwd_success = await self._execute_policy(self._pair.forward, fwd_traj)

            # --- 评估正向结果 ---
            if not fwd_success:
                self._consecutive_failures += 1
                logger.warning(
                    "Forward policy failed (consecutive=%d)", self._consecutive_failures
                )
                if self._consecutive_failures >= self._pair.max_retries:
                    await self._escalate_to_human(
                        f"连续 {self._consecutive_failures} 次正向策略失败"
                    )
                    self._consecutive_failures = 0
                    await asyncio.sleep(5)  # 等待人工处理
                    continue

            # --- 逆向（Reset）策略 ---
            rev_traj = EAPTrajectory(
                pair_id=self._pair.task_name,
                direction="reverse",
                episode_id=episode,
                instruction=self._pair.reverse.instruction_template,
            )
            self._memory.working.current_skill_id = self._pair.reverse.skill_id
            rev_success = await self._execute_policy(self._pair.reverse, rev_traj)

            if not rev_success:
                logger.warning("Reverse policy failed, requesting human reset")
                await self._escalate_to_human("逆向 reset 策略失败，环境未能复位")
                continue

            # --- 保存轨迹对 ---
            self._consecutive_failures = 0
            fwd_path = await self._recorder.save_eap_trajectory(fwd_traj)
            rev_path = await self._recorder.save_eap_trajectory(rev_traj)
            collected.append(fwd_traj)

            if on_collected:
                await on_collected(fwd_traj, rev_traj)

            logger.info(
                "Episode %d collected: fwd=%s, rev=%s",
                episode, fwd_path, rev_path,
            )

        logger.info("EAP collection done: %d/%d collected", len(collected), target_trajectories)
        return collected

    async def _execute_policy(
        self,
        policy: "EAPPolicy",
        trajectory: "EAPTrajectory",
    ) -> bool:
        """执行单个策略，收集轨迹数据，返回是否成功。"""
        try:
            # 1. 获取环境观察
            env_obs = await self._get_env_observation()
            robot_stats = await self._get_robot_stats()

            # 2. CoT 评估（确认初始状态）
            # 此处仅在正向策略前检查，避免逆向策略也做完整 CoT
            if policy.direction == "forward":
                decision = await self._planner.decide_next_action(env_obs, robot_stats)
                if decision.strategy == "call_human":
                    return False

            # 3. 执行技能
            result = await self._executor.execute(
                skill_id=policy.skill_id,
                instruction=policy.instruction_template,
            )

            # 4. 成功判断（CoT 评估）
            final_obs = await self._get_env_observation()
            final_stats = await self._get_robot_stats()
            final_decision = await self._planner.decide_next_action(
                final_obs, final_stats
            )

            success = (final_decision.evaluation == "satisfied")
            trajectory.success = success
            if not success:
                trajectory.failure_reason = final_decision.observation
            return success

        except Exception as e:
            logger.exception("Policy execution error: %s", e)
            trajectory.success = False
            trajectory.failure_reason = str(e)
            return False

    async def _get_env_observation(self) -> str:
        """从 EnvSummaryTool 获取环境观察。"""
        from agents.channels.robot_tools import EnvSummaryTool
        return await EnvSummaryTool().execute()

    async def _get_robot_stats(self) -> dict:
        """从 FetchRobotStatsTool 获取机器人状态。"""
        import json
        from agents.channels.robot_tools import FetchRobotStatsTool
        stats_str = await FetchRobotStatsTool().execute()
        try:
            return json.loads(stats_str)
        except json.JSONDecodeError:
            return {}

    async def _escalate_to_human(self, reason: str) -> None:
        """通过 CallHumanTool 发送求助。"""
        from agents.channels.robot_tools import CallHumanTool
        tool = CallHumanTool(bus=self._bus)
        await tool.execute(reason=reason, severity="critical")

    def stop(self) -> None:
        """优雅停止采集循环。"""
        self._stop_flag.set()
```

---

### Day 19 — D3：TrajectoryRecorder

**输出**：`agents/training/trajectory_recorder.py`

```python
class TrajectoryRecorder:
    """
    将 EAPTrajectory 保存为 LeRobot dataset 兼容格式。
    格式：episode_XXXXXX/observations/ + actions/ + metadata.json
    """

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = Path(dataset_dir).expanduser()
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self._episode_counter = self._load_counter()

    def _load_counter(self) -> int:
        counter_file = self.dataset_dir / ".episode_counter"
        if counter_file.exists():
            return int(counter_file.read_text())
        return 0

    def _save_counter(self) -> None:
        (self.dataset_dir / ".episode_counter").write_text(str(self._episode_counter))

    async def save_eap_trajectory(self, traj: "EAPTrajectory") -> Path:
        """保存 EAP 轨迹（正向或逆向均可）。"""
        import json
        import asyncio

        self._episode_counter += 1
        ep_dir = self.dataset_dir / f"episode_{self._episode_counter:06d}"
        ep_dir.mkdir(parents=True, exist_ok=True)

        # metadata.json
        metadata = {
            "episode_id": self._episode_counter,
            "pair_id": traj.pair_id,
            "direction": traj.direction,
            "instruction": traj.instruction,
            "success": traj.success,
            "timestamp": traj.timestamp,
            "num_steps": len(traj.actions),
            "failure_reason": traj.failure_reason,
        }
        await asyncio.to_thread(
            (ep_dir / "metadata.json").write_text,
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # observations.json
        await asyncio.to_thread(
            (ep_dir / "observations.json").write_text,
            json.dumps(traj.observations, ensure_ascii=False),
            encoding="utf-8",
        )

        # actions.json
        await asyncio.to_thread(
            (ep_dir / "actions.json").write_text,
            json.dumps(traj.actions, ensure_ascii=False),
            encoding="utf-8",
        )

        self._save_counter()
        return ep_dir

    async def save_deployment_trajectory(
        self,
        skill_id: str,
        observations: list,
        actions: list,
        success: bool,
        instruction: str = "",
    ) -> Path:
        """将部署时执行轨迹（论文 §3.3）回流训练集。"""
        traj = EAPTrajectory(
            direction="forward",
            observations=observations,
            actions=actions,
            instruction=instruction,
            success=success,
        )
        traj.pair_id = f"deployment_{skill_id}"
        return await self.save_eap_trajectory(traj)
```

---

**`tests/test_eap.py`** 完整：
```python
def test_eap_pair_from_skill_metadata():
def test_eap_pair_no_reverse_returns_none():
def test_eap_trajectory_add_step():
async def test_orchestrator_single_successful_cycle():
    """mock executor 和 cot_planner，验证完整正向-逆向循环"""
async def test_orchestrator_forward_failure_increments_counter():
async def test_orchestrator_escalates_after_max_retries():
    """连续失败 >= max_retries → call_human 被调用"""
async def test_orchestrator_stop_flag():
    """调用 stop() 后 run_collection_loop 优雅退出"""
async def test_trajectory_recorder_save_format(tmp_path):
    """验证 episode_000001/ 目录结构正确"""
async def test_trajectory_recorder_counter_persistence(tmp_path):
    """两次 recorder 实例，episode 编号连续"""
async def test_deployment_trajectory_metadata(tmp_path):
    """save_deployment_trajectory() 的 metadata.direction='forward'"""
```

---

## 八、Phase E：部署时过程监督（Day 23-26）

> 依赖：Phase B（CoTTaskPlanner）+ Phase C（robot_tools）。

### Day 23-24 — E1：SubtaskMonitor

**输出**：`agents/components/subtask_monitor.py`

```python
# agents/components/subtask_monitor.py

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

logger = logging.getLogger(__name__)


class SubtaskResult(str, Enum):
    SUCCESS  = "success"
    FAILED   = "failed"
    STUCK    = "stuck"
    SWITCHED = "switched"    # 切换策略后成功


@dataclass
class MonitorCheckResult:
    evaluation: Literal["satisfied", "stuck", "progressing"]
    strategy: Literal["continue", "switch_policy", "call_human"]
    env_summary: str
    robot_stats: dict


class SubtaskMonitor:
    """
    论文 §3.3 部署时过程监督。
    并发运行：技能执行 + 周期状态监控。
    """

    def __init__(
        self,
        cot_planner: "CoTTaskPlanner",
        memory: "RobotMemoryState",
        trajectory_recorder: Optional["TrajectoryRecorder"] = None,
        check_interval_sec: float = 2.0,
        stuck_threshold: int = 3,
    ):
        self._planner = cot_planner
        self._memory = memory
        self._recorder = trajectory_recorder
        self._check_interval = check_interval_sec
        self._stuck_threshold = stuck_threshold

    async def monitor_subtask(
        self,
        subtask: "Subtask",
        skill_execution_coro,
        on_stuck: Optional[callable] = None,
    ) -> SubtaskResult:
        """
        并发运行：技能执行协程 + 监控循环。
        技能完成或 stuck 时结束。
        """
        subtask.start()
        self._memory.working.current_skill_id = subtask.skill_id
        self._memory.task_graph.get_by_id(subtask.id)

        # 收集轨迹数据（用于回流训练）
        observations, actions = [], []
        stuck_count = 0

        exec_task = asyncio.create_task(skill_execution_coro)
        monitor_task = asyncio.create_task(
            self._monitor_loop(subtask, stuck_count, observations, actions)
        )

        try:
            # 等待任意一个先完成
            done, pending = await asyncio.wait(
                [exec_task, monitor_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 取消另一个
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 判断结果
            if exec_task in done:
                exec_result = exec_task.result()
                success = bool(exec_result)
            else:
                # monitor 先完成，说明发生了 stuck 或 call_human
                success = False

        except Exception as e:
            logger.exception("SubtaskMonitor error for %s: %s", subtask.id, e)
            success = False

        # 回流轨迹
        if self._recorder and (observations or actions):
            await self._recorder.save_deployment_trajectory(
                skill_id=subtask.skill_id,
                observations=observations,
                actions=actions,
                success=success,
                instruction=subtask.description,
            )

        if success:
            subtask.mark_done()
            return SubtaskResult.SUCCESS
        else:
            subtask.mark_failed()
            return SubtaskResult.FAILED

    async def _monitor_loop(
        self,
        subtask: "Subtask",
        stuck_count: int,
        observations: list,
        actions: list,
    ) -> None:
        """周期监控循环：查询状态 → CoT 评估 → 更新 working memory。"""
        from agents.channels.robot_tools import EnvSummaryTool, FetchRobotStatsTool
        env_tool = EnvSummaryTool()
        stats_tool = FetchRobotStatsTool()

        while True:
            await asyncio.sleep(self._check_interval)

            # 获取环境观察
            env_summary = await env_tool.execute()
            stats_str = await stats_tool.execute()
            import json
            try:
                robot_stats = json.loads(stats_str)
            except json.JSONDecodeError:
                robot_stats = {}

            # 记录到 working memory
            self._memory.working.env_summary = env_summary
            self._memory.working.robot_stats = robot_stats
            self._memory.working.add_tool_call("env_summary", env_summary[:50])

            # CoT 评估
            decision = await self._planner.decide_next_action(env_summary, robot_stats)

            logger.debug(
                "Monitor check: subtask=%s evaluation=%s strategy=%s",
                subtask.id, decision.evaluation, decision.strategy,
            )

            if decision.evaluation == "satisfied":
                logger.info("Subtask %s satisfied by monitor", subtask.id)
                return  # 触发 exec_task 的取消

            if decision.evaluation == "stuck":
                stuck_count += 1
                logger.warning(
                    "Subtask %s stuck (%d/%d)",
                    subtask.id, stuck_count, self._stuck_threshold,
                )

                if stuck_count >= self._stuck_threshold:
                    if decision.strategy == "switch_policy":
                        logger.info("Switching policy for %s", subtask.id)
                        # 触发策略切换（通知 exec_task）
                        return
                    elif decision.strategy == "call_human":
                        from agents.channels.robot_tools import CallHumanTool
                        # bus 通过 memory 间接获取（简化处理）
                        logger.critical(
                            "Calling human for subtask %s: %s",
                            subtask.id, decision.observation,
                        )
                        return
```

---

### Day 25 — E2：策略切换逻辑 + CallHuman 完善

**具体任务**：

1. **完善 `agents/channels/robot_tools.py`**：

```python
class ChangePolicy:
    """切换到备选策略。"""
    name = "change_policy"
    description = "当当前策略多次失败时，切换到备选策略"

    def __init__(self, capability_registry: "RobotCapabilityRegistry"): ...

    async def execute(self, skill_id: str, robot_type: str) -> str:
        """从 capability_registry 查找同类备选技能。"""
        # 查找同一 skill 类别中可用的备选
        ...
```

2. **完善 `EnvSummaryTool`**（接入真实感知）：
```python
class EnvSummaryTool:
    def __init__(self, semantic_map: Optional["SemanticMap"] = None):
        self._map = semantic_map

    async def execute(self, **kwargs) -> str:
        if self._map:
            return self._map.summary_for_prompt()
        return "No semantic map available"
```

3. **完善 `FetchRobotStatsTool`**（接入 arm_adapter）：
```python
class FetchRobotStatsTool:
    def __init__(self, arm_adapter=None):
        self._adapter = arm_adapter

    async def execute(self, **kwargs) -> str:
        if self._adapter:
            state = await self._adapter.get_state()
            return json.dumps(state)
        return "{}"
```

---

### Day 26 — E3：完整测试

**`tests/test_subtask_monitor.py`**：
```python
async def test_monitor_success_path():
    """技能成功执行 → monitor 返回 SUCCESS"""

async def test_monitor_stuck_triggers_switch():
    """连续 3 次 stuck 且 strategy=switch_policy → 返回"""

async def test_monitor_calls_human_on_repeated_stuck():
    """strategy=call_human → call_human 工具被调用"""

async def test_monitor_cancels_exec_on_satisfied():
    """monitor 检测到 satisfied → exec_task 被取消"""

async def test_monitor_saves_deployment_trajectory():
    """监控结束后，轨迹写入 TrajectoryRecorder"""

async def test_env_summary_tool_with_mock_map():
    """SemanticMap mock → EnvSummaryTool 返回 map.summary_for_prompt()"""

async def test_fetch_robot_stats_with_mock_adapter():
async def test_change_policy_queries_registry():
```

---

## 九、Phase G：对话式 Onboarding（Day 17-19，与 D 并行）

> 依赖：Phase A（LLMProvider）+ Phase C（AgentLoop/MessageBus）。

### Day 17（G1.1）— SceneSpec 扩展

**修改 `agents/components/scene_spec.py`**：

```python
@classmethod
def from_partial(cls, d: dict) -> "SceneSpec":
    """从部分字段构建，缺失字段设为默认值（允许不完整）。"""
    return cls(
        scene_type=d.get("scene_type", ""),
        environment=d.get("environment", ""),
        robot_type=d.get("robot_type", ""),
        task_description=d.get("task_description", ""),
        objects=list(d.get("objects") or []),
        constraints=list(d.get("constraints") or []),
        success_criteria=list(d.get("success_criteria") or []),
        metadata=dict(d.get("metadata") or {}),
    )

def is_complete(self) -> bool:
    """所有 required 字段非空。"""
    return all(
        bool(getattr(self, f)) for f in _REQUIRED_FIELDS
    )

def missing_fields(self) -> list[str]:
    """返回缺失的 required 字段名列表。"""
    return [f for f in _REQUIRED_FIELDS if not bool(getattr(self, f))]
```

### Day 18（G1.2）— ConversationalSceneAgent

**修改 `agents/components/voice_template_agent.py`**（新增类，不改现有代码）：

```python
_EXTRACT_PROMPT = """\
从以下自然语言描述中提取结构化字段，输出 JSON。
字段说明：
- scene_type: 场景类型（warehouse_pick/assembly/inspection/household）
- environment: 环境描述（自由文本）
- robot_type: 机器人类型（arm/mobile/mobile_arm）
- task_description: 任务目标（自然语言）
- objects: 涉及的物体列表（数组）

只输出能确认的字段，不确定的留空。
格式：{"scene_type": "...", "environment": "...", ...}
"""

class ConversationalSceneAgent:
    _RULE_PATTERNS = {
        "arm":    ["机械臂", "arm", "关节"],
        "mobile": ["移动", "导航", "小车"],
        "mobile_arm": ["移动机械臂", "mobile arm"],
    }
    _SCENE_KEYWORDS = {
        "warehouse_pick": ["仓库", "货架", "拣选", "warehouse"],
        "assembly":       ["装配", "安装", "组装", "assembly"],
        "inspection":     ["检测", "检查", "巡检", "inspection"],
        "household":      ["家庭", "桌子", "杯子", "household"],
    }

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        self._provider = llm_provider

    def _rule_extract(self, utterance: str) -> dict:
        """快速规则提取，无 LLM 依赖。"""
        result = {"task_description": utterance}
        u_lower = utterance.lower()
        for robot_type, keywords in self._RULE_PATTERNS.items():
            if any(kw in u_lower for kw in keywords):
                result["robot_type"] = robot_type
                break
        for scene_type, keywords in self._SCENE_KEYWORDS.items():
            if any(kw in u_lower for kw in keywords):
                result["scene_type"] = scene_type
                break
        return result

    async def _llm_extract(self, utterance: str) -> dict:
        """LLM 精确提取（仅在有 provider 时调用）。"""
        if not self._provider:
            return {}
        messages = [
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": utterance},
        ]
        response = await self._provider.chat_with_retry(
            messages=messages, temperature=0.1, max_tokens=256
        )
        import json, re
        match = re.search(r'\{[\s\S]*?\}', response.content or "")
        if not match:
            return {}
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {}

    async def fill_from_utterance(
        self,
        utterance: str,
        send_fn,    # async fn(str) → None
        recv_fn,    # async fn() → str
    ) -> "SceneSpec":
        from agents.components.scene_spec import SceneSpec

        # 1. 规则提取
        partial = self._rule_extract(utterance)

        # 2. LLM 补充（若有 provider）
        if self._provider:
            llm_result = await self._llm_extract(utterance)
            partial = {**llm_result, **partial}  # 规则优先

        spec = SceneSpec.from_partial(partial)

        # 3. 对缺失字段逐一追问
        field_prompts = {
            "scene_type":        "请问这是什么类型的场景？（例如：仓库拣选、装配、家庭整理）",
            "environment":       "能描述一下当前环境吗？（例如：工厂流水线、家庭厨房）",
            "robot_type":        "使用的是哪种机器人？（arm/mobile/mobile_arm）",
            "task_description":  "请用一句话描述任务目标：",
        }
        for field in spec.missing_fields():
            await send_fn(field_prompts.get(field, f"请提供 {field}："))
            answer = await recv_fn()
            setattr(spec, field, answer.strip())

        return spec
```

### Day 19（G2）— HardwareScanner

**新增 `agents/hardware/scanner.py`**：

```python
import glob, os, logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class HardwareScanner:
    """扫描串口/摄像头并注册到 RobotCapabilityRegistry + 持久化配置。"""

    async def scan_serial_ports(self) -> list[dict]:
        """扫描 /dev/serial/by-id 和 by-path，返回稳定路径。"""
        import asyncio
        return await asyncio.to_thread(self._scan_serial_sync)

    def _scan_serial_sync(self) -> list[dict]:
        results = []
        by_id_dir   = Path("/dev/serial/by-id")
        by_path_dir = Path("/dev/serial/by-path")
        by_id   = self._read_symlinks(by_id_dir)
        by_path = self._read_symlinks(by_path_dir)
        all_devs = set(by_id.keys()) | set(by_path.keys())
        for real_dev in sorted(all_devs):
            if not os.path.exists(real_dev):
                continue
            results.append({
                "dev": real_dev,
                "by_id":   by_id.get(real_dev, ""),
                "by_path": by_path.get(real_dev, ""),
            })
        return results

    def _read_symlinks(self, directory: Path) -> dict[str, str]:
        if not directory.exists():
            return {}
        result = {}
        for entry in directory.iterdir():
            if entry.is_symlink():
                target = os.path.realpath(str(entry))
                result[target] = str(entry)
        return result

    async def scan_cameras(self) -> list[dict]:
        try:
            import cv2
        except ImportError:
            logger.warning("opencv-python not installed, skipping camera scan")
            return []
        import asyncio
        return await asyncio.to_thread(self._scan_cameras_sync, cv2)

    def _scan_cameras_sync(self, cv2) -> list[dict]:
        cameras = []
        for dev in sorted(glob.glob("/dev/video*")):
            import re
            m = re.match(r"/dev/video(\d+)$", dev)
            if not m:
                continue
            cap = cv2.VideoCapture(int(m.group(1)))
            try:
                if not cap.isOpened():
                    continue
                cameras.append({
                    "dev": dev,
                    "index": int(m.group(1)),
                    "width":  int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                })
            finally:
                cap.release()
        return cameras

    async def scan_and_register(
        self,
        registry: "RobotCapabilityRegistry",
        config_path: Optional[Path] = None,
        send_fn: Optional[Callable] = None,
    ) -> dict:
        ports   = await self.scan_serial_ports()
        cameras = await self.scan_cameras()

        report = {
            "serial_ports": ports,
            "cameras": cameras,
        }

        if send_fn:
            msg = (
                f"扫描完成：发现 {len(ports)} 个串口设备，{len(cameras)} 个摄像头\n"
                + "\n".join(f"  串口: {p['by_id'] or p['dev']}" for p in ports)
                + "\n"
                + "\n".join(f"  摄像头: {c['dev']} ({c['width']}x{c['height']})" for c in cameras)
            )
            await send_fn(msg)

        # 持久化到配置文件
        if config_path:
            import json
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return report
```

---

## 十、验收与集成测试（Day 27-29）

### Day 27 — 端到端冒烟测试

**`tests/test_integration_e2e.py`**：
```python
async def test_full_task_execution_pipeline():
    """
    模拟完整任务执行流程（全 mock，无真实硬件）：
    1. 创建 RobotMemoryState
    2. CoTTaskPlanner 生成决策
    3. AgentLoop 处理 InboundMessage
    4. SubtaskMonitor 监控执行
    5. FailureDataRecorder 记录失败
    6. TrajectoryRecorder 保存轨迹
    """

async def test_eap_collection_pipeline():
    """
    模拟 EAP 数据采集（全 mock）：
    EAPOrchestrator → 2次正向-逆向循环 → TrajectoryRecorder
    """

async def test_telegram_message_triggers_task():
    """（可选，需 Telegram token）通过 Telegram 发消息触发任务"""
```

### Day 28 — 性能与健壮性测试

```python
async def test_cot_planner_with_real_ollama():
    """需要本地 Ollama + qwen2.5:3b，验证 CoT 输出格式"""

async def test_monitor_timeout_handling():
    """技能执行超时（60s），SubtaskMonitor 应优雅处理"""

async def test_asyncio_ros2_thread_bridge():
    """模拟 ROS2 节点线程 + AgentLoop asyncio 线程并发"""

def test_memory_state_with_large_working_memory():
    """WorkingMemory 超过 10 条时，旧条目被正确丢弃"""
```

### Day 29 — 文档 + git tag

```bash
# 运行全量测试
python -m pytest tests/ -v --ignore=tests/attn_residuals_train.py

# 统计测试覆盖率
python -m pytest tests/ --cov=agents --cov-report=term-missing

# 打里程碑 tag
git add -A
git commit -m "feat: RoboClaw integration v1.0 - LLM abstraction, structured memory, EAP, process supervision"
git tag v1.0-roboclaw-integration
```

---

## 十一、关键接口速查

### LLMProvider 使用方式

```python
# 方式1：从配置文件加载
from agents.llm.config import load_llm_provider_from_config
provider = load_llm_provider_from_config("config/llm_config.yaml")

# 方式2：直接实例化
from agents.llm import OllamaProvider
provider = OllamaProvider(model="qwen2.5:3b")

# 使用
response = await provider.chat_with_retry([
    {"role": "user", "content": "你好"}
])
print(response.content)
```

### 结构化记忆使用方式

```python
from agents.memory.robot_memory import RobotMemoryState, TaskGraph, Subtask, RoleIdentity

memory = RobotMemoryState()
memory.role.mode = "task_execution"
memory.role.robot_type = "arm"
memory.task_graph.global_task = "把书放到书架上"
memory.task_graph.subtasks = [
    Subtask("s1", "导航到书桌", "navigate"),
    Subtask("s2", "抓取书本", "grasp"),
    Subtask("s3", "导航到书架", "navigate"),
    Subtask("s4", "放置书本", "place"),
]

# 注入 TaskPlanner
planner = TaskPlanner(robot_memory=memory, history_file=Path("~/.embodied_agents/memory/HISTORY.md"))
plan = await planner.plan("把书放到书架上")
```

### CoT 规划使用方式

```python
from agents.components.task_planner import CoTTaskPlanner

cot_planner = CoTTaskPlanner(llm_provider=provider, memory=memory)
decision = await cot_planner.decide_next_action(
    observation="桌上有一本红色的书，书架在右侧1米处",
    robot_stats={"joint_angles": [0.1, 0.2, 0.3], "gripper_open": True},
)
print(decision.skill_id)       # "manipulation.grasp"
print(decision.instruction)    # "抓取桌上的红色书本"
print(decision.evaluation)     # "progressing"
```

### EAP 采集使用方式

```python
from agents.data.eap import EAPPair, EAPPolicy
from agents.data.eap_orchestrator import EAPOrchestrator
from agents.training.trajectory_recorder import TrajectoryRecorder

pair = EAPPair(
    task_name="grasp_cup",
    forward=EAPPolicy("grasp_fwd", "forward", "manipulation.grasp",
                      "抓取桌上的杯子", "杯子离开桌面超过5cm"),
    reverse=EAPPolicy("grasp_rev", "reverse", "manipulation.place",
                      "将杯子放回桌上原位", "杯子稳定放置在桌上"),
    max_retries=3,
)

recorder = TrajectoryRecorder(Path("~/.embodied_agents/datasets"))
orch = EAPOrchestrator(pair, cot_planner, skill_executor, bus, memory, recorder)
trajectories = await orch.run_collection_loop(target_trajectories=50)
print(f"采集完成：{len(trajectories)} 条轨迹")
```

---

## 十二、每日验收 Checklist

| 天 | 完成标准 |
|----|---------|
| 1 | `from agents.llm.provider import LLMProvider` 无报错 |
| 2 | `TaskPlanner(llm_provider=OllamaProvider())` 可实例化；旧测试不回归 |
| 3 | `from agents.llm.litellm_provider import LiteLLMProvider` 无报错 |
| 4 | `test_llm_provider.py` 全绿；`test_task_planner_standalone.py` 全绿 |
| F3 | `test_skill_format.py` 全绿 |
| 6 | `RobotMemoryState().to_context_block()` 输出三段结构 |
| 7 | `test_failure_recorder.py` 不回归；`append_failure()` 写入正确格式 |
| 9 | `CoTTaskPlanner._parse_decision()` 通过 JSON mock 测试 |
| 10 | `test_robot_memory.py` 全绿 |
| 11 | `MessageBus` + `BaseChannel` 实例化无报错 |
| 13 | Telegram channel 可启动（token 为空时不崩溃） |
| 15 | `test_channels.py` 全绿；`test_event_bus.py` 不回归 |
| 16 | `EAPPair.from_skill_metadata()` 解析正确 |
| 19 | `test_eap.py` 全绿 |
| 26 | `test_subtask_monitor.py` 全绿 |
| 29 | 全量 pytest 通过率 > 90%；打 v1.0 tag |
