:orphan:

# EmbodiedAgentsSys × RoboClaw 融合开发计划（修订版 v2）

> **目标（修订后）**：分两条主线推进——
> 1. **基础设施移植**：从 RoboClaw 代码仓库移植 LLM 多 Provider、
>    AgentLoop、多平台通信渠道，替换现有硬编码 Ollama 调用。
> 2. **论文功能实现**：参照《RoboClaw: An Agentic Framework for
>    Scalable Long-Horizon Robotic Tasks》，实现结构化机器人记忆、
>    EAP 自主数据采集、部署时过程监督三个核心贡献。

---

## 修订说明（相对 v1 的关键变更）

| 问题 | v1 方案 | v2 修订 |
|------|---------|---------|
| MemoryStore 概念错用 | 用 LLM 对话记忆系统存储 FailureRecord | 仅用 `append_history()` 做失败记录；新建论文的结构化机器人记忆 |
| RobotAgentLoop 重复造轮 | 新写一个简化版 AgentLoop | 直接复用 RoboClaw `AgentLoop`，将 TaskPlanner/Skill 注册为工具 |
| Pydantic 依赖矛盾 | 说"不引入 pydantic"但 Telegram 必须用 | 明确引入 `pydantic>=2.0` 为 optional 依赖 |
| LiteLLMProvider registry 依赖 | "简化版 provider 检测"（未说明怎么做） | 先只移植 OllamaProvider；LiteLLMProvider 连同 registry 整体移植 |
| 论文核心贡献缺失 | 完全不涉及 EAP、结构化记忆、过程监督 | 新增 Phase D（EAP）、Phase E（过程监督）；Phase B 实现论文结构化记忆 |
| Phase D 可并行 | 放在最后 | 提前到 Day 1 并行 |

---

## 现状速查（基于代码精读）

| 模块 | EmbodiedAgentsSys 现状 | RoboClaw / 论文可借鉴 |
|------|----------------------|----------------------|
| LLM 客户端 | `OllamaClient`（httpx 直接调用）；`TaskPlanner`/`SemanticParser` 各自 `from ollama import Client` | `LLMProvider` ABC + `LiteLLMProvider`（15+ provider，指数退避）|
| 记忆系统 | `FailureDataRecorder` 写磁盘，无跨会话检索 | 代码：`MemoryStore`（MEMORY.md + HISTORY.md）；**论文：m_t=(r_t,g_t,w_t) 三层结构化记忆** |
| 任务规划 | `TaskPlanner` 单次 LLM 调用，无 CoT | 论文：5 步 CoT 推理链（观察→目标→成功标准→评估→行动） |
| 人机交互 | `VoiceTemplateAgent` 问卷式 Q&A | `AgentLoop` + `MessageBus`（14 平台渠道） |
| 数据采集 | 手动 demonstration，无自动 reset | **论文 EAP：正向策略 + 逆向 reset 策略，自动闭环采集** |
| 执行监督 | 无运行时状态监控 | **论文：过程监督，定期查询环境摘要/机器人状态，自动切换策略或求助人类** |
| Skill 格式 | `MDSkillConfig` + `OpenClawSkillParser`，无依赖检查 | RoboClaw SKILL.md：`requires.bins/env`、`always` 字段 |
| 硬件发现 | 无自动扫描 | `scan.py`（串口/摄像头）+ `setup.py`（持久化到 setup.json）|

---

## 阶段划分总览

```
Phase A（4天）：LLM 抽象层                 ← 无硬件依赖，最高优先级
Phase B（5天）：结构化机器人记忆 + CoT 规划 ← 依赖 Phase A；论文 §3.1
Phase C（5天）：AgentLoop + 多平台渠道      ← 依赖 Phase A；修复 v1 架构问题
Phase D（5天）：EAP 自主数据采集           ← 依赖 Phase B；论文 §3.2（新增）
Phase E（4天）：部署时过程监督             ← 依赖 Phase B+C；论文 §3.3（新增）
Phase F（3天）：Skill 格式统一             ← Day 1 并行启动，不依赖其他
Phase G（3天）：对话式 Onboarding         ← 依赖 Phase A+C

并行关系：
  Day 1 起：F 并行
  Phase A 完成后：B、C 并行
  Phase B+C 完成后：D、E 并行
```

---

## Phase A：LLM 抽象层（4天）

### A1 — `LLMProvider` ABC + `OllamaProvider`（2天）

**目标**：解耦 TaskPlanner/SemanticParser 与具体 LLM，先用 Ollama 接口验证。

#### 新增文件

**`agents/llm/provider.py`**
```
整体移植自 roboclaw/providers/base.py。
改动：
  - 去掉 loguru 依赖，改为 import logging; logger = logging.getLogger(__name__)
  - 保留 LLMProvider ABC、LLMResponse、ToolCallRequest、GenerationSettings 完整定义
  - 保留 chat_with_retry()、_sanitize_empty_content()、_strip_image_content() 完整逻辑
  - 保留 _CHAT_RETRY_DELAYS = (1, 2, 4) 和 _TRANSIENT_ERROR_MARKERS
```

**`agents/llm/ollama_provider.py`**
```
将 agents/clients/ollama.py 的 OllamaClient._inference() 逻辑包装为 LLMProvider 实现。
注意：OllamaClient 使用 httpx 直接调用，非 ollama SDK，保留此方式。
向后兼容：OllamaClient 继续存在，内部委托给 OllamaProvider。
```

**`agents/llm/__init__.py`**
```python
from .provider import LLMProvider, LLMResponse, GenerationSettings
from .ollama_provider import OllamaProvider
```

#### 修改文件

**`agents/components/task_planner.py`**
```
修改 TaskPlanner.__init__：
  - 新增 llm_provider: Optional[LLMProvider] = None
  - 若传入，替代 ollama.Client 直接调用
  - 保留 backend="ollama"|"mock" 向后兼容路径
```

**`agents/components/semantic_parser.py`**
```
同上模式，新增 llm_provider 参数。
```

#### 测试

**`tests/test_llm_provider.py`**
```
- test_ollama_provider_chat：mock httpx，验证 LLMResponse 格式
- test_retry_on_transient_error：mock 返回 "429"，验证重试 3 次
- test_task_planner_with_provider：传入 mock LLMProvider，验证 plan() 输出
- test_backward_compat：不传 provider，backend="mock"，验证不回归
```

---

### A2 — `LiteLLMProvider` 完整移植（2天）

**目标**：支持 Claude/GPT/Gemini 等云端 LLM，与论文实验（使用 VLM 作为 meta-controller）对齐。

**注意**：`LiteLLMProvider` 依赖 `roboclaw/providers/registry.py`，**必须连同 registry 整体移植**，不可简化。

#### 新增文件

**`agents/llm/registry.py`**
```
整体移植自 roboclaw/providers/registry.py（ProviderSpec + PROVIDERS 列表）。
改动：仅去掉 roboclaw 命名空间，保留所有 provider 配置不变。
```

**`agents/llm/litellm_provider.py`**
```
整体移植自 roboclaw/providers/litellm_provider.py。
改动：
  - from .registry import find_by_model, find_gateway（路径修改）
  - loguru → logging（同 A1）
  - 依赖：pip install litellm>=1.40 json-repair>=0.28
```

**`config/llm_config.yaml`**（新增）
```yaml
provider: ollama          # ollama | litellm
model: qwen2.5:3b
api_key: ""               # 留空则读环境变量
api_base: ""
max_tokens: 512
temperature: 0.1
retry_delays: [1, 2, 4]
```

#### 依赖声明

**`pyproject.toml`** 新增：
```toml
[project.optional-dependencies]
llm = ["litellm>=1.40", "json-repair>=0.28"]
channels = ["python-telegram-bot>=21.0", "lark-oapi>=1.3", "pydantic>=2.0", "pydantic-settings>=2.0"]
all = ["embodied-agents-sys[llm,channels]"]
```

> **关于 pydantic**：Telegram/飞书渠道的配置类继承自 pydantic `Base`，必须引入。
> pydantic 与 EmbodiedAgentsSys 现有 attrs/dataclass 代码**不冲突**，仅在渠道层使用。

---

## Phase B：结构化机器人记忆 + CoT 规划（5天）

> **论文依据**：§3.1。论文核心贡献之一：用 m_t = (r_t, g_t, w_t) 三层结构化记忆
> 替代简单的 prompt 上下文，使 VLM 能跨越长时序任务做一致的状态追踪。

### B1 — 结构化机器人记忆 `m_t`（2天）

这是**新功能**，非 RoboClaw 代码移植，完全来自论文设计。

#### 新增文件

**`agents/memory/robot_memory.py`**
```python
from dataclasses import dataclass, field
from typing import Literal
from enum import Enum


class SubtaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Subtask:
    """子任务节点（对应论文 g_t 中的一条记录）。"""
    id: str
    description: str
    skill_id: str          # 对应哪个 Skill
    status: SubtaskStatus = SubtaskStatus.PENDING
    success_criteria: str = ""
    retry_count: int = 0


@dataclass
class RoleIdentity:
    """r_t：当前运行模式 + 可用工具列表。"""
    mode: Literal["data_collection", "task_execution"] = "task_execution"
    available_tools: list[str] = field(default_factory=list)
    robot_type: str = ""


@dataclass
class TaskGraph:
    """g_t：全局任务 + 子任务树 + 执行状态。"""
    global_task: str = ""
    subtasks: list[Subtask] = field(default_factory=list)

    @property
    def current_subtask(self) -> Subtask | None:
        """返回第一个 RUNNING 或 PENDING 子任务。"""
        for s in self.subtasks:
            if s.status in (SubtaskStatus.RUNNING, SubtaskStatus.PENDING):
                return s
        return None

    def mark_done(self, subtask_id: str) -> None:
        for s in self.subtasks:
            if s.id == subtask_id:
                s.status = SubtaskStatus.DONE

    def mark_failed(self, subtask_id: str) -> None:
        for s in self.subtasks:
            if s.id == subtask_id:
                s.status = SubtaskStatus.FAILED
                s.retry_count += 1

    def to_prompt_block(self) -> str:
        """生成注入 TaskPlanner prompt 的文本块。"""
        lines = [f"Global Task: {self.global_task}", "Subtasks:"]
        for s in self.subtasks:
            mark = {"done": "✓", "failed": "✗", "running": "→", "pending": "○"}[s.status]
            lines.append(f"  {mark} [{s.id}] {s.description} (skill={s.skill_id})")
        return "\n".join(lines)


@dataclass
class WorkingMemory:
    """w_t：当前执行的短期上下文。"""
    current_skill_id: str = ""
    tool_call_history: list[str] = field(default_factory=list)
    env_summary: str = ""          # 最近一次环境摘要
    robot_stats: dict = field(default_factory=dict)  # 最近一次机器人状态

    def add_tool_call(self, tool_name: str, result_summary: str) -> None:
        entry = f"{tool_name}: {result_summary[:120]}"
        self.tool_call_history.append(entry)
        if len(self.tool_call_history) > 10:      # 滚动窗口，保留最近 10 条
            self.tool_call_history.pop(0)

    def to_prompt_block(self) -> str:
        lines = [f"Current Skill: {self.current_skill_id}"]
        if self.env_summary:
            lines.append(f"Env Summary: {self.env_summary}")
        if self.tool_call_history:
            lines.append("Recent Tool Calls:")
            lines.extend(f"  - {h}" for h in self.tool_call_history[-5:])
        return "\n".join(lines)


@dataclass
class RobotMemoryState:
    """
    m_t = (r_t, g_t, w_t)：论文 §3.1 定义的完整结构化记忆状态。
    在每个决策步更新，注入到 VLM 的 system prompt。
    """
    role: RoleIdentity = field(default_factory=RoleIdentity)
    task_graph: TaskGraph = field(default_factory=TaskGraph)
    working: WorkingMemory = field(default_factory=WorkingMemory)

    def to_context_block(self) -> str:
        """生成完整记忆上下文，注入 TaskPlanner prompt。"""
        return "\n\n".join([
            f"## Role Identity\nMode: {self.role.mode}\n"
            f"Robot: {self.role.robot_type}\n"
            f"Tools: {', '.join(self.role.available_tools)}",
            f"## Task-Level Memory\n{self.task_graph.to_prompt_block()}",
            f"## Working Memory\n{self.working.to_prompt_block()}",
        ])
```

**`agents/memory/failure_log.py`**
```python
"""失败记录写入 HISTORY.md（仅使用 MemoryStore.append_history，不使用 consolidate）。"""
from pathlib import Path
from agents.data.failure_recorder import FailureRecord


def append_failure_to_history(record: FailureRecord, history_file: Path) -> None:
    """将 FailureRecord 追加到 HISTORY.md（grep 可搜索格式）。"""
    entry = (
        f"[{record.timestamp[:16]}] FAILURE "
        f"skill={record.failed_step_id} "
        f"type={record.error_type} "
        f"scene={record.scene_spec.scene_type} "
        f"task={record.scene_spec.task_description[:80]}\n"
    )
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(entry)


def query_failures(history_file: Path, skill_id: str, limit: int = 5) -> list[str]:
    """从 HISTORY.md 检索指定 skill 的历史失败记录。"""
    if not history_file.exists():
        return []
    lines = history_file.read_text(encoding="utf-8").splitlines()
    matches = [l for l in lines if f"skill={skill_id}" in l]
    return matches[-limit:]
```

**`agents/memory/__init__.py`**

#### 修改文件

**`agents/components/task_planner.py`**
```
修改 TaskPlanner.__init__：
  - 新增 robot_memory: Optional[RobotMemoryState] = None
  - 新增 history_file: Optional[Path] = None（HISTORY.md 路径）
修改 TaskPlanner._build_prompt()：
  - 若 self.robot_memory，将 robot_memory.to_context_block() prepend 到 prompt
  - 若 self.history_file，查询当前 skill 的历史失败，加入 prompt
```

---

### B2 — CoT 五步推理规划（2天）

> **论文依据**：Fig. 2 中 CoT Planning 的 5 个问题链。
> 将 TaskPlanner 从"单次 LLM → JSON 解析"升级为"结构化 CoT → 行动决策"。

#### 修改文件

**`agents/components/task_planner.py`**

新增 `CoTTaskPlanner` 类（保留原 `TaskPlanner` 不变）：

```python
_COT_SYSTEM_PROMPT = """你是一个机器人任务执行智能体。
在每个决策步，你必须按以下 5 个问题依次思考，然后输出行动决策。

推理结构（必须遵循）：
1. 观察：我在场景中观察到了什么？（物体位置、状态）
2. 目标：我当前的子任务是什么？成功标准是什么？
3. 评估：当前状态是否满足成功标准？我是否卡住了？
4. 策略：基于评估，我应该继续、切换策略还是请求帮助？
5. 行动：下一步具体执行哪个技能/动作？

输出格式（严格 JSON）：
{
  "reasoning": {
    "observation": "...",
    "objective": "...",
    "evaluation": "satisfied|stuck|progressing",
    "strategy": "continue|switch_policy|call_human",
    "action": "skill_id"
  },
  "subtask_id": "...",
  "skill_id": "...",
  "instruction": "...",
  "success_criteria": "..."
}
"""

class CoTTaskPlanner:
    """
    论文 §3.1 的 CoT 规划器。
    在每个决策步，用 5 步推理链选择下一个子任务和技能。
    维护 RobotMemoryState 并在每步后更新。
    """
    def __init__(
        self,
        llm_provider: LLMProvider,
        memory: RobotMemoryState,
    ): ...

    async def decide_next_action(
        self,
        observation: str,        # 来自 Env Summary 工具
        robot_stats: dict,       # 来自 Fetch Robot Stats 工具
    ) -> CoTDecision: ...
```

---

### B3 — FailureDataRecorder 集成（1天）

#### 修改文件

**`agents/data/failure_recorder.py`**
```
修改 FailureDataRecorder.record()：
  - 新增可选参数 history_file: Optional[Path] = None
  - 若传入，在写磁盘后调用 append_failure_to_history(record, history_file)
  - 同时更新 task_graph.mark_failed(record.failed_step_id)（若传入 memory）
```

#### 测试

**`tests/test_robot_memory.py`**
```
- test_robot_memory_state_context_block：验证 to_context_block() 格式
- test_task_graph_state_transitions：pending→running→done/failed 状态机
- test_cot_planner_decision：mock LLM 返回 CoT JSON，验证解析
- test_failure_log_append_and_query：写入 HISTORY.md，按 skill_id 过滤
- test_planner_uses_memory_context：验证 task_graph 状态注入 prompt
```

---

## Phase C：AgentLoop + 多平台渠道（5天）

> **架构修正**：v1 计划新写 `RobotAgentLoop`，实际是在重复实现
> `roboclaw/agent/loop.py` 的 `AgentLoop`。修订方案：**直接复用 AgentLoop**，
> 将 TaskPlanner 和 Skill 执行包装为 `ToolRegistry` 中的工具。

### C1 — MessageBus + AgentLoop 移植（2天）

#### 新增文件

**`agents/channels/bus.py`**
```
整体移植自 roboclaw/bus/queue.py（仅 36 行）。
改动：去掉 roboclaw 命名空间，无其他改动。
```

**`agents/channels/events.py`**
```
整体移植自 roboclaw/bus/events.py（InboundMessage + OutboundMessage）。
新增字段：
  InboundMessage.robot_id: str = ""   # 目标机器人 ID（多机场景预留）
```

**`agents/channels/base.py`**
```
整体移植自 roboclaw/channels/base.py。
改动：
  - 去掉 roboclaw 命名空间
  - transcribe_audio() 保留但标记为 optional（无 groq 时返回空字符串）
```

**`agents/channels/agent_loop.py`**
```
整体移植自 roboclaw/agent/loop.py（AgentLoop）。
改动：
  - 去掉 roboclaw 命名空间引用
  - 去掉 SubagentManager（当前不需要子智能体）
  - 去掉 CronTool（当前不需要定时任务）
  - 新增 _register_robot_tools()：
      注册 TaskPlannerTool、SkillExecutionTool、EnvSummaryTool、
      FetchRobotStatsTool、CallHumanTool
  - MCP 相关保留接口但标记为 optional
```

**`agents/channels/robot_tools.py`**（新增，论文 §3.1 MCP Tool 接口）
```python
"""
论文 Fig. 2 中的 MCP Tools：
  - start_policy(skill_id, instruction) → 启动 VLA 策略
  - terminate_policy() → 停止当前策略
  - change_policy(new_skill_id) → 切换策略
  - env_summary() → 返回当前环境视觉摘要
  - fetch_robot_stats() → 返回机器人关节状态
  - call_human(reason) → 通过 MessageBus 发送求助消息
"""

class TaskPlannerTool:
    """封装 CoTTaskPlanner 为 AgentLoop ToolRegistry 工具。"""
    name = "plan_task"
    description = "使用 CoT 规划器决定下一个子任务和技能"
    ...

class SkillExecutionTool:
    """封装 SkillRegistry.execute() 为工具。"""
    name = "execute_skill"
    description = "执行指定技能（grasp/place/navigate/inspect）"
    ...

class EnvSummaryTool:
    """查询当前场景的视觉摘要（对接 GroundedSAM/SemanticMap）。"""
    name = "env_summary"
    description = "获取当前环境场景摘要"
    ...

class FetchRobotStatsTool:
    """查询机器人关节状态和末端执行器位姿。"""
    name = "fetch_robot_stats"
    description = "获取机器人当前状态（关节角、末端位姿）"
    ...

class CallHumanTool:
    """通过 MessageBus 向外部渠道发送人工求助消息。"""
    name = "call_human"
    description = "当自主恢复失败时，向人类操作员发送求助"
    ...
```

---

### C2 — 渠道实现（2天）

**`agents/channels/telegram_channel.py`**
```
整体移植自 roboclaw/channels/telegram.py。
改动：
  - from roboclaw.config.schema import Base → 本地 pydantic Base（渠道层专用）
  - 新增 robot_id 白名单过滤
  - 发送执行进度、CoT 推理摘要、失败报告
```

**`agents/channels/feishu_channel.py`**
```
整体移植自 roboclaw/channels/feishu.py。
改动：支持飞书卡片消息（展示 TaskGraph 状态）
```

**`config/channels_config.yaml`**（新增）
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

### C3 — EventBus → MessageBus 桥接（1天）

#### 修改文件

**`agents/events/bus.py`**
```
新增 EventBus.set_outbound_bridge(bus: MessageBus, chat_id: str, channel: str)
在 publish() 中，对 CRITICAL/HIGH 优先级事件同步推送到 MessageBus outbound。
事件类型映射：
  robot.status.error      → 发送错误通知（含错误类型、子任务 ID）
  execution.failed        → 发送失败报告 + task_graph 当前状态
  skill.completed         → 发送完成通知（可配置开关）
  subtask.stuck           → 触发 change_policy 或 call_human（Phase E）
```

> **关于 asyncio + ROS2 的冲突**：
> ROS2 节点通常在独立线程中 spin，而 `AgentLoop.run()` 需要 asyncio 事件循环。
> 实施方案：AgentLoop 在独立线程中运行自己的 asyncio loop，
> EventBus 通过 `asyncio.run_coroutine_threadsafe(bus.publish_inbound(...), loop)` 桥接。
> MessageBus 的 `asyncio.Queue` 不跨 loop，需在同一 loop 内访问。

#### 测试

**`tests/test_channels.py`**
```
- test_message_bus_inbound_outbound：发布/消费验证
- test_base_channel_allow_from：权限过滤
- test_agent_loop_tool_registration：验证 robot_tools 正确注册
- test_eventbus_bridge：HIGH 事件自动推送到 MessageBus
- test_asyncio_ros2_bridge：模拟跨线程的 run_coroutine_threadsafe 调用
```

---

## Phase D：EAP 自主数据采集（5天）

> **论文依据**：§3.2《Self-Resetting Data Collection via Entangled Action Pairs》。
> **核心贡献**：为每个技能 k 同时学习正向策略 π_θk→ 和逆向 reset 策略 π_φk←，
> 形成 EAP 对 τ_k = (τ_k→, τ_k←)，使机器人无需人工 reset 即可持续采集数据。
>
> 论文实验结果：人工干预降低 8.04×，人工时间降低 2.16×。

### D1 — EAP 数据结构（1天）

#### 新增文件

**`agents/data/eap.py`**
```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class EAPPolicy:
    """EAP 中的单个策略（正向或逆向）。"""
    policy_id: str
    direction: Literal["forward", "reverse"]
    skill_id: str                          # 对应 EmbodiedAgentsSys Skill
    instruction_template: str             # 生成 l_t 时使用的指令模板
    success_criteria: str                 # 触发切换到下一阶段的条件描述


@dataclass
class EAPPair:
    """
    一个 EAP 对：τ_k = (τ_k→, τ_k←)。
    正向策略执行任务，逆向策略恢复环境。
    """
    task_name: str
    forward: EAPPolicy
    reverse: EAPPolicy
    max_retries: int = 3                  # 连续失败超过此数请求人工干预
    trajectory_save_dir: Path = Path("~/.embodied_agents/datasets")


@dataclass
class EAPTrajectory:
    """单次 EAP 执行收集的轨迹数据。"""
    pair_id: str
    direction: Literal["forward", "reverse"]
    observations: list[dict] = field(default_factory=list)   # o_t 序列
    joint_states: list[dict] = field(default_factory=list)   # q_t 序列
    actions: list[dict] = field(default_factory=list)         # a_t 序列
    instruction: str = ""                                     # l_t
    success: bool = False
    timestamp: str = ""
```

---

### D2 — EAP 执行编排器（3天）

#### 新增文件

**`agents/data/eap_orchestrator.py`**
```python
class EAPOrchestrator:
    """
    论文 §3.2 的自主数据采集编排器。

    执行流程：
    1. 加载 EAPPair 配置
    2. 循环执行：
       a. 运行正向策略 → 采集轨迹 τ_k→
       b. 用 CoTTaskPlanner 评估成功标准
       c. 运行逆向 reset 策略 → 采集轨迹 τ_k←
       d. 将 (τ_k→, τ_k←) 保存到数据集
       e. 若连续失败 > max_retries，通过 CallHumanTool 求助
    3. 持续循环直到收到停止信号
    """

    def __init__(
        self,
        pair: EAPPair,
        cot_planner: CoTTaskPlanner,
        skill_registry: Any,             # 现有 SkillRegistry/CapabilityRegistry
        bus: MessageBus,
        memory: RobotMemoryState,
    ): ...

    async def run_collection_loop(
        self,
        target_trajectories: int = 50,
        on_trajectory_collected: Callable | None = None,
    ) -> list[EAPTrajectory]:
        """主采集循环：无限交替执行正向-逆向策略。"""
        ...

    async def _execute_policy(
        self,
        policy: EAPPolicy,
        trajectory: EAPTrajectory,
    ) -> bool:
        """执行单个策略，收集轨迹数据，返回是否成功。"""
        ...

    async def _evaluate_success(
        self,
        policy: EAPPolicy,
        env_obs: str,
    ) -> bool:
        """用 CoTTaskPlanner 的评估步判断策略是否成功完成。"""
        ...

    async def _save_trajectory(self, trajectory: EAPTrajectory) -> None:
        """将轨迹保存为 LeRobot 兼容格式。"""
        ...
```

---

### D3 — 轨迹回流训练管线（1天）

#### 新增文件

**`agents/training/trajectory_recorder.py`**
```python
class TrajectoryRecorder:
    """
    将 EAPTrajectory 保存为 LeRobot dataset 兼容格式。

    论文 §3.3：部署时生成的轨迹同样录入训练集，
    实现"deployment as data collection"的闭环学习。
    """

    def __init__(self, dataset_dir: Path): ...

    def save_eap_trajectory(self, traj: EAPTrajectory) -> Path:
        """写入 episode_XXXXXX/ 目录，含 observations/ actions/ metadata.json。"""
        ...

    def save_deployment_trajectory(
        self,
        skill_id: str,
        observations: list,
        actions: list,
        success: bool,
    ) -> Path:
        """将部署时的执行轨迹（不论成功失败）写入数据集。"""
        ...
```

#### 测试

**`tests/test_eap.py`**
```
- test_eap_pair_forward_reverse：验证 EAPPair 数据结构
- test_orchestrator_single_cycle：mock skill_registry，验证一次正向-逆向循环
- test_orchestrator_retry_on_failure：模拟连续失败，验证求助触发
- test_trajectory_recorder_format：验证保存格式与 LeRobot 兼容
- test_collection_loop_stop_signal：验证收到停止信号时优雅退出
```

---

## Phase E：部署时过程监督（4天）

> **论文依据**：§3.3《Deployment-time Process Supervision and Skill Scheduling》。
> **核心贡献**：VLM 不只是任务开始时规划一次，而是在执行中**持续监督**每个子任务，
> 定期查询环境状态，评估成功标准，动态切换策略或升级求助人类。
>
> 论文实验结果：长时序任务成功率提升 25%。

### E1 — SubtaskMonitor（2天）

#### 新增文件

**`agents/components/subtask_monitor.py`**
```python
class SubtaskMonitor:
    """
    论文 §3.3 的过程监督器。

    在技能执行期间，周期性地：
      1. 调用 EnvSummaryTool 获取场景观察 o_t
      2. 调用 FetchRobotStatsTool 获取机器人状态 q_t
      3. 将信息写入 WorkingMemory w_t
      4. 用 CoTTaskPlanner 的"评估步"判断子任务是否完成
      5. 若 stuck（连续 N 次评估为失败），触发策略切换

    与 EAPOrchestrator 的区别：
      SubtaskMonitor 用于部署时（task execution mode）
      EAPOrchestrator 用于数据采集时（data collection mode）
    """

    def __init__(
        self,
        cot_planner: CoTTaskPlanner,
        memory: RobotMemoryState,
        env_summary_tool: EnvSummaryTool,
        robot_stats_tool: FetchRobotStatsTool,
        check_interval_sec: float = 2.0,
        stuck_threshold: int = 3,      # 连续几次评估为 stuck 触发切换
    ): ...

    async def monitor_subtask(
        self,
        subtask: Subtask,
        skill_execution_coro: Coroutine,   # 并发运行的技能执行协程
    ) -> SubtaskResult:
        """
        并发运行：skill_execution_coro（执行）+ 周期监控循环。
        返回 SubtaskResult（success/failed/stuck/switched）。
        """
        ...

    async def _check_cycle(self, subtask: Subtask) -> SubtaskCheckResult:
        """单次检查：查询状态 → 更新 w_t → CoT 评估 → 返回结论。"""
        ...
```

---

### E2 — 策略切换 + 人工升级（1天）

#### 修改文件

**`agents/channels/robot_tools.py`**（在 C1 的基础上补充）
```
完善 change_policy 工具：
  - 参数：new_skill_id（从同类 Skill 中选择备选策略）
  - 更新 working_memory.current_skill_id
  - 通过 EventBus 发布 policy.switched 事件

完善 call_human 工具（论文 Fig. 2 中 "Call Human" 按钮）：
  - 参数：reason（str），severity（"warning"|"critical"）
  - 通过 MessageBus 向所有启用渠道发送求助消息
  - 消息包含：当前子任务、失败原因、task_graph 状态截图
  - 记录人工干预时间（用于论文指标：人工时间比例）
```

---

### E3 — 部署轨迹回流（1天）

**在技能执行完成后（成功或失败），自动调用 `TrajectoryRecorder.save_deployment_trajectory()`。**

论文明确指出：部署时的执行轨迹（包含真实分布的状态数据）回流训练集，
可以进一步改善 VLA 策略在真实环境中的表现。

#### 测试

**`tests/test_subtask_monitor.py`**
```
- test_monitor_success_path：技能成功，monitor 正常退出
- test_monitor_stuck_detection：连续 3 次 stuck，触发 change_policy
- test_monitor_calls_human：recovery 失败后，验证 call_human 被调用
- test_cot_evaluation_in_monitor：验证 CoT 评估步的 JSON 解析
- test_deployment_trajectory_saved：验证执行后轨迹自动写入数据集
```

---

## Phase F：Skill 格式统一（3天，Day 1 并行启动）

> 此阶段与 A/B/C/D/E 完全独立，从第 1 天开始并行推进。

### F1 — 对齐 RoboClaw Skill 格式（2天）

#### 修改文件

**`agents/skills/md_skill_adapter.py`**
```
修改 MDSkillConfig，新增字段：
  requires_bins: list[str] = []    # CLI 工具依赖
  requires_env: list[str] = []     # 环境变量依赖
  always: bool = False             # 是否始终加载到 context

修改 SKILLMDParser._parse_frontmatter()：
  解析 requires.bins / requires.env / always 字段。

新增 MDSkillManager.check_availability(skill_name) -> tuple[bool, list[str]]:
  检查 requires_bins（shutil.which）和 requires_env（os.getenv）。

修改 MDSkillManager.discover_skills()：
  返回 list[dict]，包含 name + available + missing_deps。
```

#### 统一 Skill frontmatter 格式（新增文档 `docs/skill_format.md`）

```yaml
---
name: manipulation.grasp
description: "抓取指定物体"
requires:
  bins: ["lerobot"]
  env: ["LEROBOT_HOST"]
always: false
metadata:
  tags: [manipulation, vla]
  robot_types: [arm, mobile_arm]
  # EAP 扩展字段（论文 §3.2）
  eap:
    has_reverse: true                 # 是否存在配对的 reset 策略
    reverse_skill: "manipulation.reverse_grasp"
---
```

> `eap.has_reverse` 和 `eap.reverse_skill` 是新增字段，
> 让 `EAPOrchestrator` 可以从 Skill 元数据自动发现 EAP 对。

### F2 — Skill 格式测试（1天）

**`tests/test_skill_format.py`**
```
- test_parse_requires_bins：frontmatter 含 requires.bins，验证解析
- test_check_availability_missing：验证 available=False + missing_deps 列表
- test_backward_compat_no_requires：无 requires 字段，默认 available=True
- test_eap_metadata_parsing：验证 eap.has_reverse + eap.reverse_skill 解析
- test_discover_skills_with_availability：验证 discover_skills() 返回结构
```

---

## Phase G：对话式 Onboarding（3天）

### G1 — ConversationalSceneAgent（2天）

> **降低风险**：优先用规则提取，LLM 作为增强而非唯一路径。

#### 修改文件

**`agents/components/voice_template_agent.py`**
```
新增 ConversationalSceneAgent 类（保留原 VoiceTemplateAgent 不变）：

class ConversationalSceneAgent:
    """
    LLM 驱动的多轮对话式 SceneSpec 填写。
    策略：先用规则快速提取，缺失字段用 LLM 精确追问。
    """

    _RULE_PATTERNS = {
        "pick": ["抓", "拿", "取", "拾"],
        "place": ["放", "置", "摆"],
        "navigate": ["去", "移动到", "前往"],
    }

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,   # 可选，无 LLM 时退化为规则
    ): ...

    async def fill_from_utterance(
        self,
        utterance: str,
        send_fn: Callable,
        recv_fn: Callable,
    ) -> SceneSpec:
        """
        1. 规则提取：从 utterance 匹配 _RULE_PATTERNS
        2. LLM 补充（若配置了 llm_provider）：提取剩余字段
        3. 对缺失的 required 字段逐一追问
        4. 返回完整 SceneSpec
        """
        ...
```

**`agents/components/scene_spec.py`**
```
新增 SceneSpec.from_partial(data: dict) -> SceneSpec：
  允许部分字段，缺失 required 字段设为空字符串/空列表。
新增 SceneSpec.is_complete() -> bool：
  检查所有 _REQUIRED_FIELDS 非空。
新增 SceneSpec.missing_fields() -> list[str]：
  返回缺失的 required 字段名列表。
```

### G2 — 硬件自动扫描（1天）

#### 新增文件

**`agents/hardware/scanner.py`**
```python
"""
参考 roboclaw/embodied/scan.py 和 setup.py 实现。
注意：scan.py 只发现设备，setup.py 负责持久化。
两者都需要移植。
"""

class HardwareScanner:
    """扫描串口/摄像头，注册到 RobotCapabilityRegistry，并持久化配置。"""

    async def scan_serial_ports(self) -> list[dict]:
        """
        扫描 /dev/serial/by-path 和 /dev/serial/by-id，
        返回含稳定路径的设备列表（使用 by_id 路径而非 /dev/ttyUSBN）。
        """
        ...

    async def scan_cameras(self) -> list[dict]:
        """扫描 /dev/video*，用 cv2 验证可用性，返回含分辨率的设备列表。"""
        ...

    async def scan_and_register(
        self,
        registry: RobotCapabilityRegistry,
        config_path: Optional[Path] = None,  # 持久化到 setup.json
        send_fn: Optional[Callable] = None,
    ) -> dict:
        """
        完整流程：扫描 → 汇报发现 → 注册到 registry → 持久化到 config_path。
        send_fn 用于向用户报告（Telegram/飞书/CLI）。
        """
        ...
```

---

## 依赖变更汇总

**新增到 `pyproject.toml`**：
```toml
[project.optional-dependencies]
llm = [
    "litellm>=1.40",
    "json-repair>=0.28",
]
channels = [
    "python-telegram-bot>=21.0",
    "lark-oapi>=1.3",
    "pydantic>=2.0",          # Telegram/飞书 channel config 必需
    "pydantic-settings>=2.0",
]
vision = [
    "opencv-python>=4.8",     # 摄像头扫描
]
all = ["embodied-agents-sys[llm,channels,vision]"]
```

**不引入的依赖**（刻意排除）：
- `loguru`：改用标准 `logging`，统一日志风格
- `roboclaw` 包本身：只移植代码，不引入包依赖
- `prompt_toolkit`：CLI 交互，非必需

---

## 文件变更总览

```
agents/
├── llm/                              # 新增（Phase A）
│   ├── __init__.py
│   ├── provider.py                   # LLMProvider ABC（移植，loguru→logging）
│   ├── registry.py                   # ProviderSpec 注册表（整体移植）
│   ├── litellm_provider.py           # LiteLLMProvider（整体移植）
│   └── ollama_provider.py            # OllamaProvider（包装现有 OllamaClient）
├── memory/                           # 新增（Phase B）
│   ├── __init__.py
│   ├── robot_memory.py               # m_t=(r_t,g_t,w_t) 结构化记忆（论文新增）
│   └── failure_log.py                # HISTORY.md 失败记录（仅用 append，非 consolidate）
├── channels/                         # 新增（Phase C）
│   ├── __init__.py
│   ├── bus.py                        # MessageBus（移植，36行）
│   ├── events.py                     # InboundMessage/OutboundMessage（移植）
│   ├── base.py                       # BaseChannel ABC（移植）
│   ├── agent_loop.py                 # AgentLoop（移植，裁剪子智能体/定时任务）
│   ├── robot_tools.py                # MCP Tools（论文 §3.1 新增）
│   ├── telegram_channel.py           # Telegram 渠道（移植）
│   └── feishu_channel.py             # 飞书渠道（移植）
├── data/                             # 修改（Phase D）
│   ├── failure_recorder.py           # 修改：可选写 HISTORY.md
│   └── eap.py                        # EAPPair 数据结构（论文新增）
├── training/                         # 新增（Phase D/E）
│   └── trajectory_recorder.py        # EAP + 部署轨迹回流
├── components/                       # 修改（Phase B/G）
│   ├── task_planner.py               # 修改：接入 LLMProvider + RobotMemoryState
│   ├── semantic_parser.py            # 修改：接入 LLMProvider
│   ├── subtask_monitor.py            # 过程监督器（论文新增）
│   ├── voice_template_agent.py       # 修改：新增 ConversationalSceneAgent
│   └── scene_spec.py                 # 修改：from_partial/is_complete/missing_fields
├── hardware/
│   └── scanner.py                    # HardwareScanner（新增）
├── events/
│   └── bus.py                        # 修改：set_outbound_bridge()
└── skills/
    └── md_skill_adapter.py           # 修改：requires + eap 字段（Phase F）

config/
├── llm_config.yaml                   # 新增
└── channels_config.yaml              # 新增

docs/
└── skill_format.md                   # 新增（Skill frontmatter 规范）

tests/
├── test_llm_provider.py              # 新增（Phase A）
├── test_robot_memory.py              # 新增（Phase B）
├── test_channels.py                  # 新增（Phase C）
├── test_eap.py                       # 新增（Phase D）
├── test_subtask_monitor.py           # 新增（Phase E）
├── test_skill_format.py              # 新增（Phase F）
└── test_conversational_onboarding.py # 新增（Phase G）
```

---

## 里程碑与验收标准

| 里程碑 | 完成天 | 验收标准 |
|--------|--------|---------|
| A1 OllamaProvider | 第 2 天 | TaskPlanner 通过 LLMProvider 接口调用 Ollama，retry 测试通过 |
| A2 LiteLLMProvider | 第 4 天 | 可用 Claude/GPT 替换 Ollama，429 重试测试通过 |
| F1 Skill 格式 | 第 4 天（并行） | requires 解析 + availability 检查测试全通 |
| B1 结构化记忆 | 第 9 天 | RobotMemoryState 注入 TaskPlanner prompt，状态机测试通过 |
| B2 CoT 规划 | 第 11 天 | CoTTaskPlanner 输出合法 CoT JSON，5 步推理结构验证通过 |
| C1 AgentLoop | 第 13 天 | AgentLoop 通过 MessageBus 收发指令，robot_tools 工具注册验证 |
| C2 Telegram | 第 15 天 | 通过 Telegram 发"抓取红色杯子"→ AgentLoop 规划→ 回复结果 |
| D1 EAP | 第 20 天 | EAPOrchestrator 完成一次完整正向-逆向循环，轨迹保存验证 |
| D2 轨迹回流 | 第 22 天 | 数据格式与 LeRobot dataset 兼容，training 脚本可读取 |
| E1 过程监督 | 第 26 天 | SubtaskMonitor 检测到 stuck 后自动切换策略，3 次失败后 call_human |
| G Onboarding | 第 29 天 | 一句话任务描述→ 自动补全 SceneSpec；串口/摄像头扫描→ 注册成功 |

---

## 风险与缓解（修订）

| 风险 | 概率 | 严重度 | 缓解措施 |
|------|------|--------|---------|
| LiteLLM registry 移植工作量超估 | 中 | 中 | A2 可先跳过 LiteLLM，仅用 OllamaProvider 验证后续所有 Phase |
| asyncio + ROS2 事件循环冲突 | 中 | 高 | 独立线程运行 AgentLoop，`run_coroutine_threadsafe` 桥接；E1 阶段专项测试 |
| CoT 输出格式不稳定（小模型） | 高 | 中 | 加 JSON schema 约束；实现 fallback 到规则规划；B2 验收要求 qwen2.5:3b 通过 |
| EAP 逆向 reset 策略不存在 | 高 | 高 | 初期允许人工 reset（仅保存正向轨迹）；逐步训练逆向策略；配置 `max_retries=0` 等价于旧模式 |
| Telegram/飞书无网络 | 中 | 低 | channels 全部 optional，无渠道时退化 CLI；影响 E2 的 call_human，可降级为 EventBus 告警 |
| 部署轨迹质量低影响训练 | 中 | 中 | TrajectoryRecorder 记录 success 标志；训练时按 success=True 过滤；Phase E 完成前不回流失败轨迹 |

---

## 论文功能对照表

| 论文贡献 | 对应实现 Phase | 实现状态 |
|---------|--------------|---------|
| 结构化记忆 m_t=(r_t,g_t,w_t) | Phase B1 | 新增 |
| CoT 五步推理规划 | Phase B2 | 新增 |
| EAP 自主数据采集 | Phase D | 新增 |
| 过程监督 + 策略切换 | Phase E | 新增 |
| Call Human 升级机制 | Phase E2 | 新增 |
| 部署轨迹回流训练 | Phase D3 + E3 | 新增 |
| 多平台消息渠道 | Phase C2 | 移植 |
| LLM 多 Provider | Phase A | 移植 |
| 硬件自动扫描 | Phase G2 | 移植 |

> **未实现**（超出工程边界）：
> - VLA 策略训练（π_0.5 flow matching，论文 Eq. 5）：属于 ML 训练工程，
>   依赖大规模 GPU 集群，建议单独规划
> - 论文实验的 Agibot G01 平台适配：硬件特定，需平台方支持
