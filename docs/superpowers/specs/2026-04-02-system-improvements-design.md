# EmbodiedAgentsSys 系统改进设计文档

**日期**: 2026-04-02
**状态**: 已批准
**参考**: Claude Code CLI (`/media/hzm/data_disk/claude_code_cli`) 对比分析

---

## 目标

为 EmbodiedAgentsSys 补全 8 个工程基础模块，对齐 Claude Code CLI 的工程实践：统一错误层次、缓存机制、层级取消、插件系统、MCP 协议、上下文压缩、长期结构化记忆、测试基础设施。

---

## 整体架构

### 新增模块布局

```
agents/
├── exceptions.py          # Stream 1：统一错误层次
├── cache.py               # Stream 1：LRU缓存 + TTL装饰器
├── abort.py               # Stream 1：层级取消控制器
├── memory/
│   ├── robot_memory.py    # 已有：会话内存 (r_t, g_t, w_t)
│   ├── failure_log.py     # 已有：持久化失败记录
│   └── longterm/          # Stream 2：跨会话长期记忆
│       ├── __init__.py
│       ├── types.py       # MemoryType enum + frontmatter解析
│       ├── store.py       # 文件读写 + MEMORY.md索引维护
│       ├── retrieval.py   # find_relevant_memories() LLM语义检索
│       └── manager.py     # LongTermMemoryManager 统一入口
├── plugins/               # Stream 2：builtin plugin架构
│   ├── __init__.py
│   ├── base.py            # Plugin ABC + Hook/Tool类型
│   ├── registry.py        # 注册表 + 启用/禁用持久化
│   └── builtin/           # 内置插件（VLA/LLM/sensor）
│       ├── __init__.py
│       ├── vla_plugin.py
│       ├── llm_plugin.py
│       └── sensor_plugin.py
├── mcp/                   # Stream 2：完整MCP客户端+服务端
│   ├── __init__.py
│   ├── client.py
│   ├── server_manager.py
│   ├── config.py
│   ├── auth.py
│   └── protocol.py
├── context/               # Stream 2：Token预算 + 自动压缩
│   ├── __init__.py
│   ├── budget.py
│   ├── compressor.py
│   └── manager.py
tests/
├── conftest.py            # 增强（全局fixtures）
├── fixtures/              # mock工厂
│   ├── __init__.py
│   ├── mock_vla.py
│   ├── mock_arm.py
│   ├── mock_llm.py
│   └── mock_events.py
├── helpers/
│   ├── __init__.py
│   ├── async_helpers.py
│   └── assertion_helpers.py
├── unit/                  # 现有测试按模块迁移
│   └── (现有 test_*.py 按领域分组)
└── integration/           # 跨模块测试
    ├── test_harness_full.py  (从根目录迁移)
    └── test_agent_loop.py
```

### 依赖关系

```
exceptions ─┐
cache      ─┼─→ plugins, mcp, context, memory/longterm, testing
abort      ─┘
```

Stream 1（exceptions + cache + abort）无相互依赖，可并行开发。
Stream 2 统一基于 Stream 1 构建，Stream 1 完成后并行推进（共 5 个模块）。

---

## Stream 1：基础层

### 1. `agents/exceptions.py`

对齐 Claude Code `utils/errors.ts` 的错误层次。

**错误类层次：**

```python
AgentError(Exception)               # 基类
├── AbortError(AgentError)          # 主动取消
│   └── OperationCancelledError     # asyncio.CancelledError 包装
├── VLAActionError(AgentError)      # VLA 推理/执行失败
├── HardwareError(AgentError)       # 机械臂/传感器通信失败
├── PlanningError(AgentError)       # CoT 规划失败
├── ConfigParseError(AgentError)    # 配置解析错误（含 file_path 字段）
└── TelemetrySafeError(AgentError)  # 可安全上报（不含路径/代码）
```

**ErrorKind 枚举：**

```python
class ErrorKind(str, Enum):
    ABORT = "abort"
    VLA_ACTION = "vla_action"
    HARDWARE = "hardware"
    PLANNING = "planning"
    CONFIG = "config"
    UNKNOWN = "unknown"
```

**工具函数：**

- `is_abort_error(e: Any) -> bool`：识别 AbortError、OperationCancelledError、asyncio.CancelledError
- `classify_error(e: Exception) -> ErrorKind`：按类型分类，未知返回 UNKNOWN
- `short_error_stack(e: Any, max_frames: int = 5) -> str`：截断过长调用栈，非 Exception 返回 str(e)

**集成点：** `agents/__init__.py` 导出所有异常类；现有代码逐步迁移（不强制一次性改）。

---

### 2. `agents/cache.py`

参考 Claude Code `context.ts` 的 `memoize` 模式，提供两种缓存机制。

**同步 LRU 缓存（纯函数）：**

```python
@lru_cache(maxsize=128)
def get_robot_capabilities(robot_type: str) -> RobotCapabilities: ...

@lru_cache(maxsize=64)
def get_skill_metadata(skill_name: str) -> SkillMetadata: ...
```

**异步 TTL 缓存（有时效的 IO）：**

```python
@cached(ttl=300)  # 5分钟
async def get_git_status() -> str: ...

@cached(ttl=60)
async def get_ros_topics() -> list[str]: ...
```

**CacheRegistry：**

- `register(name, cache_obj)`：注册缓存实例
- `invalidate(name)`：按名称失效
- `invalidate_all()`：清空所有缓存
- `get_stats() -> dict`：命中率统计

实现细节：`@cached` 用 `asyncio.Lock` 防止并发重复计算（thundering herd），key 由函数名 + args 构成。

---

### 3. `agents/abort.py`

对齐 Claude Code 的层级 AbortController 树。

**AbortController：**

```python
class AbortController:
    def abort(self, reason: str = "", exc: type[Exception] = AbortError) -> None
    def create_child(self) -> "AbortController"
    def add_done_callback(self, cb: Callable[[], None]) -> None
    @property
    def is_aborted(self) -> bool
    @property
    def abort_reason(self) -> str | None
    @property
    def signal(self) -> "AbortSignal"  # 只读视图，供下游消费
```

**AbortScope（async context manager）：**

```python
async with AbortScope(controller) as ctrl:
    await long_running_task()
# 退出时自动检查 ctrl.is_aborted，若是则 raise AbortError
```

**级联语义：** 父 controller abort → 所有子 controller 自动 abort。子 abort 不影响父。

**使用示例：**

```python
root = AbortController()
skill_ctrl = root.create_child()
vla_ctrl = skill_ctrl.create_child()

root.abort("user cancelled")  # 级联取消 skill_ctrl 和 vla_ctrl
```

---

## Stream 2：应用层

### 4. `agents/memory/longterm/`

对齐 Claude Code `memdir/` 的完整实现，适配机器人领域。

**记忆类型（`types.py`）：**

| 类型 | 对应 Claude Code | 机器人场景 |
|------|----------------|----------|
| `robot_config` | `user` | 机器人型号偏好、操作习惯、传感器配置 |
| `feedback` | `feedback` | 操作反馈：哪种 policy 在特定场景下失败 |
| `mission` | `project` | 当前任务上下文、工位布局、时间节点 |
| `reference` | `reference` | ROS topic 路径、标定文件位置、外部服务地址 |

frontmatter 格式（对齐 Claude Code）：
```markdown
---
name: vla-transparency-failure
description: VLA 在透明物体抓取中成功率低，需切换 policy
type: feedback
---
抓取透明物体时 VLA 成功率约 30%，需切换到 force-control policy。
**Why:** 透明物体无法被 RGB 相机可靠检测。
**How to apply:** 当 skill=manipulation.grasp 且 object.material=transparent 时触发。
```

**存储结构：**
```
~/.embodied_agents/memory/     # 全局记忆（跨项目）
  MEMORY.md                    # 索引文件（≤200行，≤25KB）
  robot_config_arm_type.md
  feedback_vla_transparency.md
  ...

./.embodied_agents/memory/     # 项目级记忆（当前工作目录）
  MEMORY.md
  mission_assembly_line_a.md
  reference_ros_topics.md
  ...
```

**`store.py` — 文件读写 + 索引维护：**
- `save_memory(name, type, description, body, scope)` → 写入 `.md` 文件，更新 `MEMORY.md`
- `delete_memory(name, scope)` → 删除文件，从索引移除
- `load_memory(name, scope) -> str` → 读取完整内容
- `scan_memory_files(memory_dir) -> list[MemoryHeader]` → 扫描所有 `.md`，解析 frontmatter，按 mtime 排序（上限 200 条）
- `truncate_entrypoint(raw) -> str` → MEMORY.md 超过 200 行或 25KB 时截断并附警告

**`retrieval.py` — 语义检索（对齐 `findRelevantMemories`）：**
```python
async def find_relevant_memories(
    query: str,
    memory_dirs: list[Path],
    provider: LLMProvider,
    recent_tools: list[str] = [],
    already_surfaced: set[str] = set(),
    max_results: int = 5,
) -> list[RelevantMemory]
```
- 扫描所有 memory 目录，读取 frontmatter（仅前 30 行，避免全量读取）
- 用 LLMProvider 从索引中选出最相关的 ≤5 条（system prompt 指示只选"确定有用"的）
- 已注入过的记忆通过 `already_surfaced` 过滤，避免重复
- `recent_tools` 传入时跳过工具用法类记忆（活跃使用中不需要提示用法）

**`manager.py` — 统一入口：**
```python
class LongTermMemoryManager:
    def __init__(self, global_dir: Path, project_dir: Path, provider: LLMProvider)

    async def recall(self, query: str, recent_tools: list[str] = []) -> list[str]
    # 返回相关记忆正文列表，注入 RobotAgentLoop context

    def remember(self, name: str, type: MemoryType,
                 description: str, body: str, scope: str = "project") -> None

    def forget(self, name: str, scope: str = "project") -> None

    def get_index(self, scope: str = "both") -> str
    # 返回 MEMORY.md 内容，供 system prompt 注入
```

**与 RobotAgentLoop 集成：**
- `recall()` 在每次任务开始时调用，相关记忆注入 system prompt
- `remember()` 在任务结束或用户明确要求时调用
- 记忆漂移检测：推荐记忆中涉及文件路径/ROS topic 的条目，先验证存在再使用

---

### 5. `agents/plugins/`

对齐 Claude Code `plugins/builtinPlugins.ts` + `types/plugin.ts` 模式。

**Plugin ABC：**

```python
class Plugin(ABC):
    name: str                    # 唯一标识符
    version: str
    description: str

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
    def get_tools(self) -> list[Tool]: ...        # 注册到 RobotToolRegistry
    def get_skills(self) -> list[SkillConfig]: ...# 注册到 SkillRegistry
    def get_hooks(self) -> list[Hook]: ...        # 生命周期钩子
```

**PluginRegistry：**

- `register(plugin: Plugin) -> None`
- `enable(name: str) -> None` / `disable(name: str) -> None`（持久化到 config.yaml）
- `get_enabled() -> list[Plugin]`
- `initialize_all() -> None`：启动时并发初始化所有已启用插件

**内置插件（`builtin/`）：**

| 插件 | 封装现有模块 | 提供 |
|------|------------|------|
| VLAPlugin | VLAAdapterBase | start_policy, change_policy tools |
| LLMPlugin | LLMProvider | llm_query tool |
| SensorPlugin | hardware adapters | env_summary tool |

**外部插件加载：** 通过 Python `importlib` + entry_points 机制，插件声明 `embodied_agents.plugins` entry point 即可被发现。

---

### 5. `agents/mcp/`

完整对齐 Claude Code `services/mcp/` 实现。

**MCPClient（`client.py`）：**

```python
class MCPClient:
    async def connect(self, config: MCPConfig) -> ConnectionResult
    async def disconnect(self) -> None
    async def list_tools(self) -> list[MCPTool]
    async def call_tool(self, name: str, arguments: dict) -> ToolResult
    async def list_resources(self) -> list[Resource]
    async def read_resource(self, uri: str) -> ResourceContent
    async def health_check(self) -> HealthStatus  # connected/needs-auth/failed
```

**MCPConfig（`config.py`）：**

```python
@dataclass
class MCPConfig:
    name: str
    command: str           # e.g., "npx", "python"
    args: list[str]
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    scope: Literal["global", "project"] = "project"
```

**MCPServerManager（`server_manager.py`）：**

- `add_server(config: MCPConfig) -> str`：返回 server_id
- `remove_server(server_id: str) -> None`
- `get_server(server_id: str) -> MCPClient`
- `list_servers() -> list[MCPServerStatus]`：含连接健康状态
- `check_all_health() -> dict[str, HealthStatus]`：并发检查

**auth.py：** token 存储在 `~/.config/embodied_agents/mcp_tokens.json`，`save_token(server_id, token)` / `read_token(server_id)` / `clear_token(server_id)`。

**EmbodiedAgentsSys 作为 MCP server：** `RobotToolRegistry` 内注册的工具通过 MCP server 暴露，外部可通过 `mcp serve` 命令启动。

---

### 6. `agents/context/`

对齐 Claude Code `autoCompact` + `microcompactMessages` 模式。

**ContextBudget（`budget.py`）：**

```python
class ContextBudget:
    MAX_TOKENS: int = 100_000
    WARNING_THRESHOLD: float = 0.80   # 80% → 警告
    CRITICAL_THRESHOLD: float = 0.95  # 95% → 触发压缩

    def estimate_tokens(self, messages: list[Message]) -> int
    def check_budget(self, messages: list[Message]) -> BudgetStatus
    def should_warn(self, messages: list[Message]) -> bool
    def should_compress(self, messages: list[Message]) -> bool
```

Token 估算：`len(content) // 4`（快速近似），可配置替换为精确 tokenizer。

**MicroCompressor（`compressor.py`）：**

- `compress_message(msg) -> Message`：组合多种压缩策略
- `strip_images(msg) -> Message`：移除 base64 图片内容
- `truncate_long_content(msg, max_chars=2000) -> Message`：截断超长文本

**AutoCompactor（`compressor.py`）：**

```python
class AutoCompactor:
    async def compact_if_needed(self, messages: list[Message]) -> list[Message]
    async def summarize_and_replace(self, messages, start, end) -> list[Message]
    def get_stats(self) -> CompactionStats
```

压缩策略：优先 MicroCompress 旧消息，若仍超阈值则 LLM 摘要替换最旧一段。

**ContextManager（`manager.py`）：** 统一入口，持有 Budget + Compactor，`RobotAgentLoop` 调用 `manager.process(messages)` 即可。

---

### 7. `tests/` 重组

**目录迁移规则：**

| 现有文件模式 | 迁移目标 |
|------------|---------|
| `test_harness_*.py` | `integration/` |
| `test_agent_loop.py`, `test_full_integration.py` | `integration/` |
| 其余 `test_*.py` | `unit/<domain>/`（按 agents/ 子目录对应） |

**`fixtures/` mock 工厂：**

```python
# mock_vla.py
@pytest.fixture
def mock_vla_factory():
    def _make(success_rate=1.0, action_noise=False, **overrides):
        ...
    return _make

# mock_llm.py
@pytest.fixture
def mock_llm_provider():
    class MockLLMProvider(LLMProvider):
        responses: list[str] = []
        async def complete(self, messages) -> str:
            return self.responses.pop(0) if self.responses else "mock response"
    return MockLLMProvider()
```

**`helpers/async_helpers.py`：**

- `run_async(coro)` — 在测试中运行协程
- `assert_eventually(condition, timeout=5.0, interval=0.1)` — 等待异步状态
- `AsyncMockContext` — 模拟 async context manager

**`helpers/assertion_helpers.py`：**

- `assert_skill_called(tracer, skill_id)` — 验证 skill 被调用
- `assert_no_abort(tracer)` — 验证无异常中止
- `assert_error_kind(exc, kind: ErrorKind)` — 验证错误分类

**覆盖率门槛：** 新增模块（exceptions, cache, abort, plugins, mcp, context）≥ 80%，通过 `pytest-cov --fail-under=80` 在 CI 中强制执行。

---

## 实施策略

### Stream 1（并行，无依赖）
- `exceptions.py` — 独立实现
- `cache.py` — 独立实现
- `abort.py` — 独立实现

### Stream 2（Stream 1 完成后并行推进）
- `memory/longterm/` — 依赖 exceptions, cache（LLM 检索用现有 LLMProvider）
- `plugins/` — 依赖 exceptions, cache
- `mcp/` — 依赖 exceptions
- `context/` — 依赖 exceptions, cache
- `tests/` 重组 — 依赖所有上层模块

### 不做的事（YAGNI）
- 不引入 message broker 或分布式追踪
- 不实现插件市场 UI
- MCP streaming 协议暂不实现（call_tool 返回完整结果）
- Context 压缩不使用精确 tokenizer（近似估算足够）
- Long-term memory 不实现 team/private 双作用域（仅 global + project 两级）
- Long-term memory 不实现自动写入（只在任务结束或用户明确要求时写入）

---

*文档生成时间: 2026-04-02*
