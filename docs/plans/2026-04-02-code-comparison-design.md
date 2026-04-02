# Claude Code vs EmbodiedAgentsSys 代码对比分析

**日期**: 2026-04-02
**目的**: 对比两个代码库的架构设计，为 EmbodiedAgentsSys 改进提供参考

---

## 1. 概述

| 维度 | Claude Code (`/media/hzm/Data/src/src`) | EmbodiedAgentsSys |
|------|---------------------------------------|-------------------|
| **语言** | TypeScript (Bun runtime) | Python |
| **类型** | CLI 工具 | 机器人代理系统 |
| **领域** | AI 编程助手 | 具身智能机器人 |
| **规模** | 800KB+ main.tsx, 200+ 组件 | 模块化 Python 包 |

---

## 2. 架构与设计模式

### 2.1 架构风格

| 项目 | 架构风格 | 特点 |
|------|---------|------|
| Claude Code | 单体式 | 单入口 main.tsx，Feature Flags 条件编译 |
| EmbodiedAgentsSys | 模块化 | 按领域分目录 (clients/, components/, hardware/) |

### 2.2 核心设计模式

**Claude Code**:
- **Observable Store**: 自定义 `createStore<T>` 订阅模式
- **Dependency Injection**: `QueryDeps` 类型注入便于测试
- **Feature Flags**: `feature()` 条件编译去除死代码
- **Streaming Executor**: 工具流式并发执行

**EmbodiedAgentsSys**:
- **Adapter Pattern**: VLA 模型可插拔 (`VLAAdapterBase`)
- **Observer Pattern**: `EventBus` pub/sub 解耦
- **Factory Pattern**: `HarnessEnvironment` 创建
- **Registry Pattern**: `SkillRegistry`, `LLMRegistry` 服务发现

### 2.3 通信机制

**Claude Code**:
```
Query Engine → Tools (直接调用)
           ↓
Event/Message Broadcasting
           ↓
React Context / Subscriptions
```

**EmbodiedAgentsSys**:
```
MessageBus (外部通信)
    ↓
RobotAgentLoop → CoTTaskPlanner
    ↓
EventBus (内部 pub/sub)
    ↓
Components (ROS2 Topics)
```

---

## 3. 代码组织

| 维度 | Claude Code | EmbodiedAgentsSys |
|------|-------------|-------------------|
| **目录结构** | 扁平 (~2-3层) | 深层 (~3-4层) |
| **组织方式** | 按功能 (commands/, tools/, services/) | 按领域 (clients/, components/) |
| **模块粒度** | 命令级 (~80个) | 组件级 |
| **入口点** | 单入口 (main.tsx) | 多入口 (ROS2 节点) |

---

## 4. 扩展性

| 维度 | Claude Code | EmbodiedAgentsSys |
|------|-------------|-------------------|
| **插件系统** | ✅ 完善 (Plugins + Skills) | ❌ 基础 Registry |
| **MCP 集成** | ✅ 完整实现 | ❌ 无 |
| **工具扩展** | 30+ 内置 + MCP 服务器 | VLA Adapter 可扩展 |
| **配置驱动** | YAML + Settings 文件 | YAML 配置驱动 |

**Claude Code 插件架构**:
```
plugins/
  ├── builtinPlugins.ts
  ├── bundled/
skills/
  ├── skill-management/
  └── ...
tools/
  ├── AgentTool/
  ├── BashTool/
  ├── MCPTool/
  └── ...
```

---

## 5. 状态管理

### 5.1 Claude Code - Observable Store

```typescript
export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}
```

特点：
- 同步订阅模式
- 记忆化 Context (`getSystemContext()`, `getUserContext()`)
- 自动压缩上下文

### 5.2 EmbodiedAgentsSys - 双层事件

```
MessageBus (asyncio.Queue)
├── inbound:  Channel → Agent
└── outbound: Agent → Channel

EventBus (pub/sub)
├── HIGH/CRITICAL → MessageBus 桥接
└── Components 订阅
```

结构化 Memory:
- `r_t`: RoleIdentity (当前模式, 机器人类型)
- `g_t`: TaskGraph (子任务 DAG)
- `w_t`: WorkingMemory (当前技能, 工具历史)

---

## 6. 错误处理

### 6.1 Claude Code - 丰富的错误层次

```typescript
// 核心错误类
ClaudeError, AbortError, ShellError
ConfigParseError, TeleportOperationError
TelemetrySafeError_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS

// 工具函数
isAbortError(e) → boolean
classifyAxiosError(e) → AxiosErrorKind
isENOENT(e), isFsInaccessible(e)
shortErrorStack(e, maxFrames)
```

特点：
- 隐私安全的遥测错误
- 错误分类统一处理
- Abort 信号层级树

### 6.2 EmbodiedAgentsSys - Python 标准异常

- Python 内置 Exception
- Harness Mock 失败场景
- 缺少统一错误抽象

---

## 7. 测试策略

| 维度 | Claude Code | EmbodiedAgentsSys |
|------|-------------|-------------------|
| **测试框架** | 未发现测试目录 | pytest + conftest.py |
| **测试数量** | ❌ 不明确 | 50+ 测试文件 |
| **Mock 策略** | QueryDeps 注入 | test_mocks.py |
| **覆盖范围** | ❌ 不明确 | 完整 (harness, skills, clients) |

**EmbodiedAgentsSys conftest.py 特点**:
- 模块路径修复机制
- 预加载 pure-Python 子模块
- 解决 `sys.modules` 残留问题

---

## 8. 性能优化

| 特性 | Claude Code | EmbodiedAgentsSys |
|------|-------------|-------------------|
| **预取策略** | ✅ MDM, Keychain, Context | ❌ 无 |
| **记忆化** | `memoize()` 缓存 | ❌ 无 |
| **自动压缩** | AutoCompact + MicroCompact | ❌ 无 |
| **Token 控制** | Budget Tracker | ❌ 无 |
| **Abort 级联** | Hierarchical AbortController | asyncio.CancelledError |

**Claude Code 优化机制**:
```typescript
// 记忆化
export const getSystemContext = memoize(async () => {...})
export const getUserContext = memoize(async () => {...})

// Token 预算
createBudgetTracker, checkTokenBudget

// 自动压缩
autoCompactIfNeeded()
microcompactMessages()
```

---

## 9. 独特设计亮点

### Claude Code
1. **Side-effect Imports**: 模块加载时预取资源
2. **Settings Path Hashing**: 内容哈希避免缓存失效
3. **Coordinator Mode**: 多 Agent 编排
4. **Permission Modes**: ask/bypass/auto 权限模式
5. **零侵入遥测**: 隐私安全的错误上报

### EmbodiedAgentsSys
1. **EAP (Entangled Action Pairs)**: 自主数据收集
2. **Zero-Invasive Harness**: 无侵入式测试框架
3. **YAML Capability Registry**: 声明式硬件能力
4. **CoT Task Planner**: 5步推理可审计
5. **ROS2 生命周期**: 组件化管理

---

## 10. 优缺点对比

### Claude Code

| 优点 | 缺点 |
|------|------|
| 成熟的 CLI 工程化实践 | 单体代码 (800KB+ main.tsx) |
| 完善的错误处理与遥测 | TypeScript 动态性风险 |
| 自动上下文压缩优化 | 缺乏可见的测试目录 |
| 强大的插件/MCP 生态 | Feature flags 复杂度 |
| 多 Agent 编排支持 | - |

### EmbodiedAgentsSys

| 优点 | 缺点 |
|------|------|
| 清晰的领域驱动设计 | 缺少通用插件系统 |
| 事件驱动解耦 | 无缓存/记忆化机制 |
| 完善的评估框架 (Harness) | 错误抽象不足 |
| VLA Adapter 可插拔 | Token/性能优化缺失 |
| ROS2 生态集成 | - |

---

## 11. EmbodiedAgentsSys 改进建议

基于与 Claude Code 的对比分析，提出以下改进建议：

### 11.1 优先级矩阵

| 改进项 | 优先级 | 工作量 | 影响 |
|--------|--------|--------|------|
| 错误处理系统 | ⭐⭐⭐ | 中 | 高 |
| 缓存机制 | ⭐⭐⭐ | 低 | 高 |
| 测试改进 | ⭐⭐⭐ | 中 | 高 |
| 插件系统 | ⭐⭐ | 高 | 中 |
| MCP 支持 | ⭐⭐ | 高 | 中 |
| 上下文压缩 | ⭐⭐ | 中 | 中 |
| 分层 Abort | ⭐ | 低 | 低 |

---

### 11.2 错误处理系统 ⭐⭐⭐ 高优先级

**现状**: 仅使用 Python 标准异常
**建议**: 参照 Claude Code 建立错误层次

```python
# agents/exceptions.py
class AgentError(Exception):
    """基础异常类"""
    pass

class AbortError(AgentError):
    """可取消操作的 abort 信号"""
    pass

class VLAActionError(AgentError):
    """VLA 执行失败"""
    pass

class HardwareError(AgentError):
    """硬件通信错误"""
    pass

class TelemetrySafeError(AgentError):
    """可安全上报的遥测错误"""
    pass

# 工具函数
def is_abort_error(e) -> bool: ...
def classify_error(e) -> ErrorKind: ...
def short_error_stack(e, max_frames=5) -> str: ...
```

**理由**: 机器人系统需要精确的错误分类和恢复策略

---

### 11.3 缓存/记忆化机制 ⭐⭐⭐ 高优先级

**现状**: 无缓存，每次重新计算
**建议**: 添加 LRU 缓存和记忆化

```python
from functools import lru_cache
from typing import Optional

# agents/cache.py

# Capability 查询缓存
@lru_cache(maxsize=128)
def get_robot_capabilities(robot_type: str) -> RobotCapabilities:
    ...

# System context 缓存
class SystemContextCache:
    @lru_cache(maxsize=1)
    def get_git_status(self) -> GitStatus: ...

    @lru_cache(maxsize=1)
    def get_ros_topics(self) -> list[str]: ...

# 使用装饰器
@cached(ttl=300)
async def get_skill_metadata(skill_name: str) -> SkillMetadata: ...
```

**理由**: 减少重复计算，提升响应速度

---

### 11.4 插件系统 ⭐⭐ 中优先级

**现状**: 仅 SkillRegistry，扩展性有限
**建议**: 参照 Claude Code 的 Plugins + Skills 架构

```
agents/plugins/
  ├── __init__.py
  ├── base.py          # Plugin 基类
  ├── registry.py      # 插件注册表
  └── builtin/
      ├── vla/         # VLA 插件
      ├── llm/         # LLM 插件
      └── sensors/     # 传感器插件

agents/plugin_skills/   # 插件提供的 Skills
```

**Plugin 基类示例**:
```python
# agents/plugins/base.py
from abc import ABC, abstractmethod

class Plugin(ABC):
    """插件基类"""
    name: str
    version: str

    @abstractmethod
    async def initialize(self) -> None: ...
    @abstractmethod
    async def shutdown(self) -> None: ...

    def get_tools(self) -> list[Tool]: ...
    def get_skills(self) -> list[VLASkill]: ...
    def get_hooks(self) -> list[Hook]: ...
```

**理由**: 支持第三方扩展，构建生态

---

### 11.5 MCP 协议支持 ⭐⭐ 中优先级

**现状**: 无 MCP 支持
**建议**: 实现 Model Context Protocol 客户端

```python
# agents/mcp/
# ├── __init__.py
# ├── client.py        # MCP 客户端
# ├── server_manager.py # 服务器管理
# ├── protocol.py      # 协议实现
# └── tools.py         # MCP 工具适配

class MCPClient:
    """MCP 协议客户端"""
    async def connect(self, server_config: MCPConfig) -> None: ...
    async def disconnect(self) -> None: ...
    async def list_tools(self) -> list[MCPTool]: ...
    async def call_tool(self, name: str, arguments: dict) -> ToolResult: ...
    async def list_resources(self) -> list[Resource]: ...
    async def read_resource(self, uri: str) -> ResourceContent: ...

class MCPServerManager:
    """MCP 服务器管理器"""
    async def add_server(self, config: MCPConfig) -> str: ...
    async def remove_server(self, server_id: str) -> None: ...
    async def get_server(self, server_id: str) -> MCPClient: ...
```

**MCPConfig 示例**:
```python
# agents/mcp/config.py
@dataclass
class MCPConfig:
    name: str
    command: str  # e.g., "npx", "python"
    args: list[str]
    env: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
```

**理由**: 与 Claude Code 工具生态兼容

---

### 11.6 自动上下文压缩 ⭐⭐ 中优先级

**现状**: 无自动压缩
**建议**: 实现 Token 预算和自动压缩

```python
# agents/context/
# ├── __init__.py
# ├── budget.py        # Token 预算管理
# ├── compressor.py    # 压缩算法
# └── manager.py       # 上下文管理器

class ContextBudget:
    """上下文 Token 预算"""
    MAX_TOKENS: int = 100_000
    WARNING_THRESHOLD: float = 0.8
    CRITICAL_THRESHOLD: float = 0.95

    def check_budget(self, messages: list[Message]) -> BudgetStatus: ...
    def should_warn(self) -> bool: ...
    def should_compress(self) -> bool: ...

class MicroCompressor:
    """单条消息精简"""
    def compress_message(self, msg: Message) -> Message: ...
    def strip_images(self, msg: Message) -> Message: ...
    def truncate_long_content(self, msg: Message, max_chars: int) -> Message: ...

class AutoCompactor:
    """自动压缩触发器"""
    def __init__(self, budget: ContextBudget, compressor: MicroCompressor): ...
    async def compact_if_needed(self, messages: list[Message]) -> list[Message]: ...
    def get_compression_stats(self) -> CompressionStats: ...

# 消息历史整理
class MessageHistory:
    """可审计的消息历史"""
    async def archive_old_messages(self, before_index: int) -> None: ...
    async def summarize_and_replace(self, start: int, end: int) -> Message: ...
```

**理由**: 防止上下文溢出，保持系统稳定

---

### 11.7 分层 Abort 机制 ⭐ 常规优先级

**现状**: asyncio.CancelledError 无层次
**建议**: 实现层级取消信号

```python
# agents/abort.py

class AbortController:
    """层级取消控制器"""
    def __init__(self, parent: Optional['AbortController'] = None): ...
    def abort(self, reason: str, exc: Exception = CancelledError) -> None: ...
    def create_child(self) -> 'AbortController': ...
    @property
    def is_aborted(self) -> bool: ...
    @property
    def abort_reason(self) -> Optional[str]: ...
    def add_done_callback(self, cb: Callable) -> None: ...

class AbortScope:
    """Abort 作用域管理器"""
    def __init__(self, controller: AbortController): ...
    async def __aenter__(self) -> AbortController: ...
    async def __aexit__(self, *args) -> None: ...

# 使用示例
async def run_with_abort(controller: AbortController, task: Coroutine):
    async with AbortScope(controller):
        return await task

# 多层级取消
root = AbortController()
skill_abort = root.create_child()
vla_abort = skill_abort.create_child()

try:
    async with AbortScope(vla_abort):
        await vla.execute(action)
except AbortError:
    logger.info(f"Aborted: {vla_abort.abort_reason}")
```

**理由**: 支持精细的取消控制，支持超时和级联取消

---

### 11.8 测试改进 ⭐⭐⭐ 高优先级

**现状**: 测试分散，无统一 mock 策略
**建议**: 完善测试基础设施

```
tests/
  ├── conftest.py          # ✅ 已有，需增强
  ├── fixtures/
  │   ├── __init__.py
  │   ├── mock_vla.py       # MockVLAAdapter 工厂
  │   ├── mock_arm.py       # MockArmAdapter 工厂
  │   ├── mock_llm.py       # Mock LLM Provider
  │   ├── mock_ros.py       # Mock ROS2 节点
  │   └── mock_events.py    # Mock EventBus
  ├── fixtures.py           # pytest fixtures
  ├── helpers/
  │   ├── async_helpers.py  # 异步测试工具
  │   └── assertion_helpers.py
  ├── integration/
  │   ├── test_harness_full.py
  │   └── test_agent_loop.py
  └── unit/
      ├── test_skills/
      ├── test_components/
      └── test_clients/
```

**Fixture 示例**:
```python
# tests/fixtures/mock_vla.py

@pytest.fixture
def mock_vla_adapter():
    """Mock VLA Adapter factory"""
    class MockVLAAdapter(VLAAdapterBase):
        def __init__(self, **overrides):
            self._config = overrides
            self.action_history = []

        async def reset(self) -> None: ...
        async def act(self, observation, skill_token) -> Action: ...
        async def execute(self, action) -> None: ...
        @property
        def action_dim(self) -> int: return 7

    return MockVLAAdapter

# QueryDeps 风格的依赖注入
class HarnessDeps:
    """Harness 测试依赖注入"""
    def __init__(
        self,
        vla_adapter: MockVLAAdapter = None,
        arm_adapter: MockArmAdapter = None,
        llm_provider: MockLLMProvider = None,
    ): ...
```

**理由**: 提高测试可维护性和覆盖率

---

### 11.9 改进实施建议

#### 阶段一：基础改进（1-2周）
1. 实现 `agents/exceptions.py` 错误层次
2. 实现 `agents/cache.py` 缓存机制
3. 完善测试 fixtures

#### 阶段二：增强功能（2-3周）
4. 实现 `agents/plugins/` 插件系统
5. 实现 `agents/mcp/` MCP 客户端
6. 实现 `agents/context/` 上下文压缩

#### 阶段三：高级特性（3-4周）
7. 实现 `agents/abort.py` 分层 Abort
8. 性能优化和监控

---

## 12. 总结

EmbodiedAgentsSys 在模块化架构和事件驱动方面已有良好基础，通过借鉴 Claude Code 的工程实践，可以进一步提升：

1. **错误处理**: 建立统一的错误抽象层次
2. **性能**: 引入缓存和自动压缩机制
3. **扩展性**: 构建插件系统和 MCP 支持
4. **可测试性**: 完善测试基础设施

建议按优先级分阶段实施，优先解决高优先级、高影响的改进项。

---

*文档生成时间: 2026-04-02*
*更新: 2026-04-02 (添加改进建议)*
