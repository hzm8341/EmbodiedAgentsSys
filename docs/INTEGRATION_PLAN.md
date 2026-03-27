# EmbodiedAgentsSys × RoboClaw 融合开发计划

> 目标：将 RoboClaw 的 LLM 多 Provider、Memory、多平台通信、对话式 Onboarding 能力
> 移植/集成到 EmbodiedAgentsSys，同时保留其 ROS2 机器人能力底座。

---

## 现状速查（基于代码阅读）

| 模块 | EmbodiedAgentsSys 现状 | RoboClaw 可借鉴 |
|------|----------------------|----------------|
| LLM 客户端 | `OllamaClient` 硬编码，无 retry | `LLMProvider` ABC + `LiteLLMProvider`（15+ provider，指数退避） |
| 任务规划 | `TaskPlanner` 直接 `import ollama`，fallback 到 mock | 需接入 `LLMProvider` 抽象 |
| Memory | `FailureDataRecorder` 写磁盘，无跨会话检索 | `MemoryStore`（MEMORY.md + HISTORY.md + LLM consolidation） |
| 人机交互 | `VoiceTemplateAgent` 问卷式 Q&A，无多轮对话 | `BaseChannel` + `MessageBus`（14 平台） |
| Skill 格式 | `md_skill_adapter.py` + `openclaw_adapter.py` 已有 MD 格式，但与 RoboClaw 不兼容 | YAML frontmatter + `requires.bins/env` 依赖检查 |
| Onboarding | 无硬件自动扫描 | `scan.py` + `identify.py`（串口/摄像头自动发现） |

---

## 阶段划分

```
Phase A（2周）：LLM 抽象层 + Memory 系统        ← 优先级最高，无硬件依赖
Phase B（2周）：多平台通信渠道                   ← 依赖 Phase A
Phase C（1周）：对话式 Onboarding 升级           ← 依赖 Phase A + B
Phase D（1周）：Skill Markdown 格式统一          ← 可并行
```

---

## Phase A：LLM 抽象层 + Memory 系统

### A1 — 引入 `LLMProvider` 抽象（3天）

**目标**：让 `TaskPlanner`、`SemanticParser` 等组件与具体 LLM 解耦。

#### 新增文件

**`agents/llm/provider.py`**
```
从 RoboClaw 移植 LLMProvider ABC + LLMResponse + ToolCallRequest + GenerationSettings。
改动：
- 去掉 roboclaw 命名空间依赖
- 保留 chat_with_retry()、_sanitize_empty_content()、_strip_image_content() 完整逻辑
- 保留 _CHAT_RETRY_DELAYS = (1, 2, 4) 和 _TRANSIENT_ERROR_MARKERS
```

**`agents/llm/litellm_provider.py`**
```
从 RoboClaw 移植 LiteLLMProvider。
改动：
- 去掉 roboclaw.providers.registry 依赖，改为简化版 provider 检测
- 保留 _apply_cache_control()、_resolve_model()、_parse_response() 完整逻辑
- 依赖：pip install litellm json-repair loguru
```

**`agents/llm/ollama_provider.py`**
```
将现有 OllamaClient._inference() 逻辑包装为 LLMProvider 实现。
保持向后兼容：OllamaClient 继续存在，但内部委托给 OllamaProvider。
```

**`agents/llm/__init__.py`**
```python
from .provider import LLMProvider, LLMResponse
from .litellm_provider import LiteLLMProvider
from .ollama_provider import OllamaProvider
```

#### 修改文件

**`agents/components/task_planner.py`**
```
修改 TaskPlanner.__init__：
  - 新增参数 llm_provider: Optional[LLMProvider] = None
  - 若传入 llm_provider，使用它替代 ollama.Client 直接调用
  - 保留 backend="ollama"|"mock" 向后兼容
修改 TaskPlanner.plan()：
  - 若 self._llm_provider，调用 await self._llm_provider.chat_with_retry(messages)
  - 解析 LLMResponse.content 替代 response["response"]
```

**`agents/components/semantic_parser.py`**
```
同上模式，新增 llm_provider 参数，替代直接 ollama 调用。
```

#### 配置

**`config/llm_config.yaml`**（新增）
```yaml
provider: litellm          # litellm | ollama
model: qwen2.5:3b          # 默认模型
api_key: ""                # 留空则读环境变量
api_base: ""               # 自定义 endpoint
max_tokens: 512
temperature: 0.1
retry_delays: [1, 2, 4]
```

#### 测试

**`tests/test_llm_provider.py`**
```
- test_ollama_provider_chat：mock ollama.Client，验证 LLMResponse 格式
- test_litellm_provider_retry：mock acompletion 抛 429，验证重试 3 次
- test_task_planner_with_provider：传入 mock LLMProvider，验证 plan() 输出
- test_task_planner_backward_compat：不传 provider，backend="mock"，验证不回归
```

---

### A2 — Memory 系统（3天）

**目标**：让失败历史、用户偏好跨会话持久化，TaskPlanner 规划前自动检索。

#### 新增文件

**`agents/memory/store.py`**
```
从 RoboClaw 移植 MemoryStore。
改动：
- 去掉 roboclaw.utils.helpers 依赖，内联 ensure_dir()
- 保留 consolidate()、_fail_or_raw_archive()、_raw_archive() 完整逻辑
- 保留 _SAVE_MEMORY_TOOL 定义（LLM tool calling 格式）
- workspace 默认路径：~/.embodied_agents/memory/
```

**`agents/memory/robot_memory.py`**（新增，EmbodiedAgentsSys 特有）
```python
class RobotMemoryBridge:
    """将 FailureRecord 写入 MemoryStore，供 TaskPlanner 检索。"""

    def __init__(self, store: MemoryStore):
        self._store = store

    async def record_failure(self, record: FailureRecord) -> None:
        """将失败记录追加到 HISTORY.md（grep 可搜索格式）。"""
        entry = (
            f"[{record.timestamp[:16]}] FAILURE skill={record.failed_step_id} "
            f"type={record.error_type} scene={record.scene_spec.scene_type} "
            f"task={record.scene_spec.task_description[:80]}"
        )
        self._store.append_history(entry)

    def query_failures(self, skill_id: str, limit: int = 5) -> list[str]:
        """从 HISTORY.md 检索指定 skill 的历史失败记录。"""
        if not self._store.history_file.exists():
            return []
        lines = self._store.history_file.read_text().splitlines()
        matches = [l for l in lines if f"skill={skill_id}" in l]
        return matches[-limit:]

    def get_context_for_planner(self) -> str:
        """返回供 TaskPlanner prompt 使用的记忆上下文。"""
        long_term = self._store.read_long_term()
        return long_term if long_term else ""
```

**`agents/memory/__init__.py`**

#### 修改文件

**`agents/components/task_planner.py`**
```
修改 TaskPlanner.__init__：
  - 新增参数 memory_bridge: Optional[RobotMemoryBridge] = None
修改 TaskPlanner._build_prompt()：
  - 若 self._memory_bridge，prepend get_context_for_planner() 到 prompt
  - 替代现有 self._failure_history 列表（两者并存，memory_bridge 优先）
```

**`agents/data/failure_recorder.py`**
```
修改 FailureDataRecorder.record()：
  - 新增可选参数 memory_bridge: Optional[RobotMemoryBridge] = None
  - 若传入，在写磁盘后调用 await memory_bridge.record_failure(record)
```

#### 测试

**`tests/test_memory_system.py`**
```
- test_store_append_and_read：写入 history，验证可读取
- test_robot_memory_bridge_record：FailureRecord → HISTORY.md 格式验证
- test_query_failures_by_skill：写入多条，按 skill_id 过滤
- test_planner_uses_memory_context：mock memory_bridge，验证 prompt 包含历史
- test_consolidation_on_overflow：模拟 context 超限，验证 LLM consolidation 调用
```

---

## Phase B：多平台通信渠道

### B1 — MessageBus + BaseChannel 移植（2天）

**目标**：引入解耦的消息总线，让外部平台可以向机器人发送任务、接收状态。

#### 新增文件

**`agents/channels/bus.py`**
```
从 RoboClaw 移植 MessageBus（roboclaw/bus/queue.py）。
改动：
- 去掉 roboclaw 命名空间
- 保留 publish_inbound()、subscribe_outbound()、get_inbound() 异步接口
```

**`agents/channels/events.py`**
```
从 RoboClaw 移植 InboundMessage + OutboundMessage dataclass。
新增字段：
  InboundMessage.robot_id: str = ""   # 目标机器人 ID（多机场景）
```

**`agents/channels/base.py`**
```
从 RoboClaw 移植 BaseChannel ABC。
改动：
- 去掉 roboclaw.providers.transcription 依赖（可选功能，后续补充）
- 保留 is_allowed()、_handle_message() 完整逻辑
- 保留 transcribe_audio() 但改为可选（无 groq 时返回空字符串）
```

**`agents/channels/__init__.py`**

#### 新增渠道实现

**`agents/channels/telegram_channel.py`**
```
从 RoboClaw roboclaw/channels/telegram.py 移植。
改动：
- 依赖：pip install python-telegram-bot
- 接收文本指令 → InboundMessage → MessageBus
- 发送执行状态、失败报告（含截图）→ OutboundMessage
```

**`agents/channels/feishu_channel.py`**
```
从 RoboClaw roboclaw/channels/feishu.py 移植。
改动：
- 依赖：pip install lark-oapi
- 支持飞书卡片消息（执行计划展示）
```

#### 新增文件

**`agents/channels/robot_agent_loop.py`**
```python
class RobotAgentLoop:
    """
    连接 MessageBus 与机器人执行管线的主循环。

    收到 InboundMessage → 解析指令 → 调用 TaskPlanner → 执行 Skills
    → 发送 OutboundMessage（进度/结果/失败报告）
    """

    def __init__(
        self,
        bus: MessageBus,
        task_planner: TaskPlanner,
        skill_registry: SkillRegistry,
        memory_bridge: Optional[RobotMemoryBridge] = None,
    ): ...

    async def run(self) -> None:
        """主循环：持续消费 inbound 消息。"""
        ...

    async def _handle_task(self, msg: InboundMessage) -> None:
        """解析指令 → 规划 → 执行 → 回复。"""
        ...

    async def _send_progress(self, chat_id: str, channel: str, text: str) -> None:
        ...

    async def _send_failure_report(
        self, chat_id: str, channel: str, record: FailureRecord
    ) -> None:
        """发送失败报告，包含 scene_spec 摘要和错误类型。"""
        ...
```

#### 配置

**`config/channels_config.yaml`**（新增）
```yaml
telegram:
  enabled: false
  token: ""
  allow_from: []          # telegram user_id 白名单
  send_progress: true

feishu:
  enabled: false
  app_id: ""
  app_secret: ""
  allow_from: ["*"]
  send_progress: true
```

#### 测试

**`tests/test_channels.py`**
```
- test_message_bus_inbound_outbound：发布 inbound，消费验证
- test_base_channel_allow_from：空列表拒绝，"*" 允许，指定 ID 过滤
- test_robot_agent_loop_task_flow：mock TaskPlanner + SkillRegistry，验证完整流程
- test_failure_report_format：FailureRecord → OutboundMessage 内容验证
```

---

### B2 — EventBus 与 MessageBus 桥接（1天）

**目标**：机器人内部事件（EventBus）自动转发到外部渠道（MessageBus）。

#### 修改文件

**`agents/events/bus.py`**
```
新增 EventBus.set_outbound_bridge(bus: MessageBus, chat_id: str, channel: str)
在 publish() 中，对 CRITICAL/HIGH 优先级事件，同步推送到 MessageBus outbound 队列。
事件类型映射：
  robot.status.error    → 发送错误通知
  execution.failed      → 发送失败报告
  skill.completed       → 发送完成通知（可配置开关）
```

---

## Phase C：对话式 Onboarding 升级

### C1 — VoiceTemplateAgent 多轮对话化（2天）

**目标**：将问卷式 Q&A 升级为 LLM 驱动的自然语言对话，用户可以用一句话描述任务。

#### 修改文件

**`agents/components/voice_template_agent.py`**
```
新增 ConversationalSceneAgent 类（保留原 VoiceTemplateAgent 不变）：

class ConversationalSceneAgent:
    """
    LLM 驱动的多轮对话式 SceneSpec 填写。
    用户可以说"帮我把桌上的红色杯子放到货架上"，
    Agent 自动提取字段，对缺失字段追问。
    """

    def __init__(self, llm_provider: LLMProvider): ...

    async def fill_from_utterance(
        self,
        utterance: str,
        send_fn: Callable[[str], Coroutine],
        recv_fn: Callable[[], Coroutine[Any, Any, str]],
    ) -> SceneSpec:
        """
        从自然语言描述开始，多轮对话补全 SceneSpec。
        1. LLM 从 utterance 提取已知字段（JSON tool call）
        2. 对缺失的 required 字段逐一追问
        3. 返回完整 SceneSpec
        """
        ...

    def _build_extraction_prompt(self, utterance: str) -> list[dict]:
        """构建字段提取 prompt，使用 tool calling 格式。"""
        ...

    def _missing_required(self, partial: dict) -> list[str]:
        """返回缺失的必填字段列表。"""
        ...
```

**`agents/components/scene_spec.py`**
```
新增 SceneSpec.from_partial(data: dict) -> SceneSpec
  允许部分字段，缺失字段设为空字符串/空列表。
新增 SceneSpec.is_complete() -> bool
  检查所有 required 字段非空。
```

#### 测试

**`tests/test_conversational_onboarding.py`**
```
- test_extract_from_single_utterance：一句话提取 scene_type + task_description
- test_multi_turn_fill_missing：第一轮缺 robot_type，第二轮补充
- test_backward_compat_voice_template：原 VoiceTemplateAgent 不受影响
```

---

### C2 — 硬件自动扫描（1天）

**目标**：参考 RoboClaw scan.py，实现串口/摄像头自动发现，注册到 RobotCapabilityRegistry。

#### 新增文件

**`agents/hardware/scanner.py`**
```python
class HardwareScanner:
    """自动扫描可用硬件并注册到 CapabilityRegistry。"""

    async def scan_serial_ports(self) -> list[str]:
        """扫描可用串口（/dev/ttyUSB*, /dev/ttyACM*, CAN 接口）。"""
        ...

    async def scan_cameras(self) -> list[dict]:
        """扫描可用摄像头（/dev/video*）。"""
        ...

    async def scan_and_register(
        self,
        registry: RobotCapabilityRegistry,
        send_fn: Optional[Callable] = None,
    ) -> dict:
        """
        扫描所有硬件，通过 send_fn 向用户报告发现结果。
        返回 setup dict（兼容 RoboClaw setup.json 格式）。
        """
        ...
```

---

## Phase D：Skill Markdown 格式统一

### D1 — 对齐 RoboClaw Skill 格式（2天）

**目标**：让 EmbodiedAgentsSys 的 MD Skill 与 RoboClaw 格式兼容，支持 `requires.bins/env` 依赖检查。

#### 现状分析

EmbodiedAgentsSys 已有：
- `md_skill_adapter.py`：通用 MD Skill 框架（`MDSkillConfig`、`SKILLMDParser`）
- `openclaw_adapter.py`：OpenClaw 格式解析（`OpenClawSkillParser`）

两者 frontmatter 格式不同，且缺少 `requires` 依赖检查。

#### 修改文件

**`agents/skills/md_skill_adapter.py`**
```
修改 MDSkillConfig，新增字段：
  requires_bins: list[str] = []    # 需要的 CLI 工具
  requires_env: list[str] = []     # 需要的环境变量
  always: bool = False             # 是否始终加载

修改 SKILLMDParser._parse_frontmatter()：
  解析 frontmatter 中的 requires.bins / requires.env / always 字段。

新增 MDSkillManager.check_availability(skill_name: str) -> tuple[bool, list[str]]:
  检查 requires_bins（shutil.which）和 requires_env（os.getenv）。
  返回 (is_available, missing_list)。

修改 MDSkillManager.discover_skills()：
  返回 list[dict]，包含 name + available + missing_deps。
```

**统一 frontmatter 格式**（新增文档 `docs/skill_format.md`）
```yaml
---
name: manipulation.grasp
description: "抓取指定物体"
requires:
  bins: ["lerobot"]          # CLI 工具依赖
  env: ["LEROBOT_HOST"]      # 环境变量依赖
always: false                # 是否始终加载到 context
metadata:
  tags: [manipulation, vla]
  robot_types: [arm, mobile_arm]
---
```

#### 测试

**`tests/test_skill_format.py`**
```
- test_parse_requires_bins：frontmatter 含 requires.bins，验证解析
- test_check_availability_missing_bin：shutil.which 返回 None，验证 available=False
- test_check_availability_missing_env：os.getenv 返回 None，验证 available=False
- test_backward_compat_no_requires：无 requires 字段，默认 available=True
```

---

## 依赖变更汇总

**新增 Python 依赖**（追加到 `pyproject.toml`）：
```toml
[project.optional-dependencies]
llm = ["litellm>=1.40", "json-repair>=0.28", "loguru>=0.7"]
channels = ["python-telegram-bot>=21.0", "lark-oapi>=1.3"]
all = ["embodied-agents[llm,channels]"]
```

**不引入的依赖**（刻意排除）：
- `roboclaw` 包本身（只移植代码，不引入包依赖）
- `prompt_toolkit`（CLI 交互，非必需）
- `pydantic`（已有 attrs，不混用）

---

## 文件变更总览

```
agents/
├── llm/                          # 新增
│   ├── __init__.py
│   ├── provider.py               # LLMProvider ABC（移植自 RoboClaw）
│   ├── litellm_provider.py       # LiteLLMProvider（移植自 RoboClaw）
│   └── ollama_provider.py        # OllamaProvider（包装现有 OllamaClient）
├── memory/                       # 新增
│   ├── __init__.py
│   ├── store.py                  # MemoryStore（移植自 RoboClaw）
│   └── robot_memory.py           # RobotMemoryBridge（新增）
├── channels/                     # 新增
│   ├── __init__.py
│   ├── bus.py                    # MessageBus（移植自 RoboClaw）
│   ├── events.py                 # InboundMessage/OutboundMessage（移植）
│   ├── base.py                   # BaseChannel ABC（移植自 RoboClaw）
│   ├── telegram_channel.py       # Telegram 渠道（移植自 RoboClaw）
│   ├── feishu_channel.py         # 飞书渠道（移植自 RoboClaw）
│   └── robot_agent_loop.py       # 主循环（新增）
├── hardware/
│   └── scanner.py                # HardwareScanner（新增，参考 RoboClaw）
├── components/
│   ├── task_planner.py           # 修改：接入 LLMProvider + RobotMemoryBridge
│   ├── semantic_parser.py        # 修改：接入 LLMProvider
│   ├── voice_template_agent.py   # 修改：新增 ConversationalSceneAgent
│   └── scene_spec.py             # 修改：from_partial() + is_complete()
├── data/
│   └── failure_recorder.py       # 修改：可选写入 RobotMemoryBridge
├── events/
│   └── bus.py                    # 修改：新增 set_outbound_bridge()
└── skills/
    └── md_skill_adapter.py       # 修改：requires 依赖检查

config/
├── llm_config.yaml               # 新增
└── channels_config.yaml          # 新增

tests/
├── test_llm_provider.py          # 新增
├── test_memory_system.py         # 新增
├── test_channels.py              # 新增
├── test_conversational_onboarding.py  # 新增
└── test_skill_format.py          # 新增
```

---

## 里程碑与验收标准

| 里程碑 | 时间 | 验收标准 |
|--------|------|---------|
| A1 完成 | 第 3 天 | `TaskPlanner` 可用 Claude/GPT/Ollama 任意 provider 规划任务，retry 测试通过 |
| A2 完成 | 第 6 天 | 失败记录写入 HISTORY.md，下次规划 prompt 包含历史，consolidation 测试通过 |
| B1 完成 | 第 10 天 | Telegram 发送"抓取红色杯子"→ 机器人执行→ 回复结果，端到端测试通过 |
| B2 完成 | 第 11 天 | `execution.failed` 事件自动推送到 Telegram |
| C1 完成 | 第 13 天 | 一句话描述任务，Agent 自动补全 SceneSpec，缺失字段追问 |
| C2 完成 | 第 14 天 | 新机械臂接入：扫描串口→ 对话确认→ 注册到 CapabilityRegistry |
| D1 完成 | 第 16 天 | 所有 MD Skill 支持 requires 检查，`discover_skills()` 返回可用性状态 |

---

## 风险与缓解

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| litellm 与现有 ollama 包冲突 | 低 | optional dependency，不强制安装 |
| ROS2 环境中 asyncio 事件循环冲突 | 中 | MessageBus 使用独立线程的 asyncio loop，通过 `run_coroutine_threadsafe` 桥接 |
| Telegram/飞书 在机器人部署环境无网络 | 中 | channels 全部 optional，无渠道时退化为 CLI |
| LLM consolidation 调用增加延迟 | 低 | consolidation 在后台异步执行，不阻塞规划主路径 |
