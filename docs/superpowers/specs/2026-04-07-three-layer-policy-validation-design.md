:orphan:

# 三层分离架构设计文档：EmbodiedAgentsSys 工业级安全隔离

**文档版本**: 1.0
**创建日期**: 2026-04-07
**作者**: Claude Code (Brainstorming + Self-Review)
**项目**: EmbodiedAgentsSys
**设计方案**: 三层分离架构 (Three-Layer Policy Validation Architecture)

---

## 目录

1. [执行摘要](#执行摘要)
2. [背景与需求](#背景与需求)
3. [设计目标](#设计目标)
4. [整体架构](#整体架构)
5. [核心组件设计](#核心组件设计)
6. [两层验证系统](#两层验证系统)
7. [闭环执行与确认](#闭环执行与确认)
8. [人工接管机制](#人工接管机制)
9. [边界情况处理](#边界情况处理)
10. [实现路线图](#实现路线图)
11. [配置与扩展](#配置与扩展)
12. [安全性分析](#安全性分析)
13. [测试策略](#测试策略)

---

## 执行摘要

本设计文档描述了对 EmbodiedAgentsSys 的架构改进，以满足工业 Agent 设计准则（特别是"七大铁律"）的要求。

**核心改进**：
- ✅ **P1 安全优先**：零容错的白名单校验和边界检查
- ✅ **P2 可控接管**：任何时刻操作员可中止系统，完整人工接管模式
- ✅ **P3 决策分离**：明确的三层架构（LLM 提案 → 规则校验 → 执行）
- ✅ **P4 闭环设计**：所有执行必须进行结果确认，禁止"发出即完成"
- ✅ **P5 可靠性**：两层验证确保离线降级，网络中断时继续运行
- ✅ **P6 安全机制**：完整的白名单、二次确认、审计日志
- ✅ **P7 LLM 隔离**：大模型完全隔离，只输出提案不执行

**实现时间**: 3-5 天
**工作量**: ~2500 行代码 + 测试
**破坏性改动**: 最小（使用适配器模式，现有代码可继续运行）

---

## 背景与需求

### 当前问题

EmbodiedAgentsSys 目前采用 4 层架构：
```
感知 → 认知(LLM直接生成指令) → 执行 → 反馈
```

**存在的安全风险**：

1. **LLM 直接控制** — LLM 生成的指令直接发送给执行层，无校验层
2. **反馈无确认** — 发出指令后不确认是否实际执行，允许"发出即完成"
3. **人工接管困难** — 无明确的人工中止机制
4. **无白名单保护** — 未授权的危险操作无法被阻止
5. **审计链不完整** — 无完整的从提案到执行的追溯路径

### 工业 Agent 准则映射

| 准则 | 当前状态 | 改进后 |
|-----|--------|------|
| P1 安全优先 | ❌ LLM 可生成任意指令 | ✅ 白名单 + 边界检查强制过滤 |
| P2 可控接管 | ❌ 无明确的接管机制 | ✅ 紧急按钮/示教器/Web 界面可中止 |
| P3 决策分离 | ❌ 缺少规则校验层 | ✅ LLM→规则→执行的三层模式 |
| P4 闭环设计 | ❌ 无结果确认 | ✅ 所有执行必须确认 |
| P5 可靠性 | ❌ 网络中断则停止 | ✅ 本地缓存规则 + 离线降级 |
| P6 安全机制 | ❌ 无白名单、二次确认、审计 | ✅ 三项全覆盖 |
| P7 LLM 隔离 | ❌ LLM 直接执行 | ✅ LLM 只提案，规则系统执行 |

---

## 设计目标

### 功能目标

1. **决策分离**：LLM 不能直接控制设备，必须通过规则校验系统
2. **闭环确认**：每个执行动作都必须进行结果确认
3. **人工可控**：任何时刻操作员可以接管或中止系统
4. **完整审计**：从 LLM 提案到执行确认的完整链路都被记录

### 非功能目标

1. **向后兼容**：现有的 Tool 代码无需立即改造，使用适配器逐步迁移
2. **低延迟**：毫秒级的本地校验，不因网络中断而停止关键功能
3. **扩展性**：支持用户定义自定义校验器和验证规则
4. **可观测性**：实时反馈、告警、审计，便于监控和调试

---

## 整体架构

### 五层架构（改进后）

```
┌─────────────────────────────────────────────────────┐
│         感知层（Perception Layer）                   │
│   RobotObservation：图像、状态、机械爪位置            │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│     认知层（Cognition Layer）- LLM 提案              │
│  输出：ActionProposal（而非最终指令）                │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  规则校验系统（Policy Validation Layer）- 新增      │
│  ✅ 两层验证：本地快速 + 中央深度                    │
│  ✅ WhitelistValidator / BoundaryChecker / ...       │
│  输出：ValidatedAction（通过校验的指令）             │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│     执行层（Execution Layer）- 改造                  │
│  ✅ 异步生成器式执行 + 实时反馈                      │
│  ✅ 闭环确认机制                                     │
│  ✅ 人工接管支持                                     │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│    反馈层（Feedback Layer）- 增强                    │
│  ✅ ExecutionLog：完整的执行生命周期                 │
│  ✅ AuditTrail：不可篡改的审计日志                   │
│  ✅ AlertSystem：异常立即告警                        │
└─────────────────────────────────────────────────────┘
```

### 数据流

```
LLM (认知层)
  │
  └─→ ActionProposal
       {"action_type": "move_to", "params": {...}, "expected_outcome": "..."}
       │
       └─→ 两层验证系统
           │
           ├─→ 本地验证（快速，永不离线）
           │   ├─ WhitelistValidator
           │   └─ BoundaryChecker
           │
           └─→ 中央验证（可选，可能不可用）
               ├─ ConflictDetector
               └─ SecondConfirmation
           │
           └─→ ValidatedAction (通过校验)
               │
               └─→ 执行层（异步生成器）
                   │
                   ├─→ 执行反馈 (实时)
                   │   ├─ 进度更新
                   │   ├─ 状态更新
                   │   └─ 错误检测
                   │
                   └─→ 执行确认
                       ├─ 检查结果是否符合 expected_outcome
                       ├─ 返回 CONFIRMED / PARTIAL / FAILED / TIMEOUT
                       └─ 写入审计日志
```

---

## 核心组件设计

### 1. 数据结构定义

#### ActionType（预定义的动作类型）

```python
class ActionType(Enum):
    MOVE_TO = "move_to"
    GRIPPER_OPEN = "gripper_open"
    GRIPPER_CLOSE = "gripper_close"
    VISION_CAPTURE = "vision_capture"
    EMERGENCY_STOP = "emergency_stop"
    # ... 更多预定义类型
```

**设计意图**：使用 Enum 而非自由字符串，确保类型安全。

#### ExpectedOutcomeType（预定义的期望结果）

```python
class ExpectedOutcomeType(Enum):
    ARM_REACHES_TARGET = "arm_reaches_target"
    OBJECT_GRASPED = "object_grasped"
    OBJECT_RELEASED = "object_released"
    OBJECT_VISIBLE = "object_visible"
    EMERGENCY_STOPPED = "emergency_stopped"
```

**设计意图**：确认引擎可以对这些预定义的结果执行精确检查。

#### ActionProposal（LLM 的动作提案）

```python
@dataclass
class Action:
    action_type: ActionType
    params: dict
    expected_outcome: ExpectedOutcomeType

@dataclass
class ActionProposal:
    id: str
    action_sequence: List[Action]
    sequence_type: SequenceType = SequenceType.SEQUENTIAL
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)
```

**设计意图**：
- 强类型，减少错误
- `expected_outcome` 让执行引擎知道检查什么
- `reasoning` 用于审计和调试
- `id` 用于追踪

#### ExecutionFeedback（执行反馈）

```python
class ExecutionFeedback:
    class Stage(Enum):
        STARTED = "started"
        IN_PROGRESS = "in_progress"
        PAUSED = "paused"
        RESUMED = "resumed"
        COMPLETED = "completed"
        FAILED = "failed"

    stage: Stage
    progress: float  # 0.0 ~ 1.0
    current_state: dict
    message: str
    has_error: bool
    error_message: str
    error_type: Optional[str]  # "hardware", "timeout", "user_cancel", etc.
    timestamp: float

    @property
    def is_terminal(self) -> bool:
        """是否是终态"""
        return self.stage in [self.Stage.COMPLETED, self.Stage.FAILED]

    @property
    def is_recoverable(self) -> bool:
        """是否可以恢复"""
        return self.stage == self.Stage.PAUSED
```

**设计意图**：
- 完整的状态机，支持暂停和恢复
- `is_terminal` 让执行引擎知道何时停止监听
- `is_recoverable` 让人工接管知道是否可以继续

#### ConfirmationResult（执行确认结果）

```python
class ConfirmationStatus(Enum):
    CONFIRMED = "confirmed"        # 完全符合预期
    PARTIAL = "partial"            # 部分成功，需要人工审查
    FAILED = "failed"              # 执行失败
    TIMEOUT = "timeout"            # 超时

@dataclass
class ConfirmationResult:
    status: ConfirmationStatus
    reason: str
    actual_state: dict
    confirmation_details: dict
    recovery_action: Optional[str] = None
```

**设计意图**：
- 区分四种结果，每种有不同的处理逻辑
- `recovery_action` 建议下一步操作

---

### 2. 规则校验系统

#### WhitelistValidator（白名单校验器）

**职责**：检查动作是否被允许

**输入**：ActionProposal
**输出**：ValidationResult(valid=True/False)

**规则**：
- 所有可执行指令必须在 `whitelist.yaml` 中预先登记
- 未授权指令一律拒绝，不做推断，不做例外
- 参数类型和范围也必须符合白名单定义

**配置示例**：
```yaml
allowed_actions:
  move_to:
    required_params:
      target_pose: {type: list, length: 3}
      speed: {type: float, min: 0.01, max: 1.0}
  gripper_close:
    required_params:
      force: {type: float, min: 0, max: 100}
```

#### BoundaryChecker（边界检查器）

**职责**：检查参数是否在物理安全范围内

**输入**：ActionProposal
**输出**：ValidationResult(valid=True/False)

**规则**：
- 机械臂目标位置必须在工作空间范围内
- 关节角度必须在极限范围内
- 夹爪力度必须在 0-100N 范围内
- 运动速度必须在安全范围内

**配置示例**：
```yaml
workspace:
  x: {min: 0.1, max: 1.5}
  y: {min: -1.0, max: 1.0}
  z: {min: 0.0, max: 2.0}
gripper_limits:
  min_force: 0
  max_force: 100
```

#### ConflictDetector（冲突检测器）

**职责**：检查当前系统状态下，新动作是否存在逻辑冲突

**输入**：ActionProposal + RobotState
**输出**：ValidationResult(valid=True/False)

**规则**：
- 机械臂正在运动时，不能立即改变方向
- 夹爪正在夹持时，不能无限制打开
- 紧急停止激活时，不能执行任何动作

**特点**：
- 需要实时的 RobotState，只能在中央验证系统中进行
- 本地验证系统不进行冲突检测

#### SecondConfirmation（二次确认）

**职责**：高危操作强制人工审批

**输入**：ActionProposal
**输出**：ApprovalResult(granted=True/False)

**规则**：
- 高风险动作需要人工确认（例：move_to）
- 确认必须通过物理设备（示教器/紧急按钮），不接受 Web 界面
- 超时（30秒）自动拒绝
- 人工强制执行超出边界的操作时，必须经过额外确认

**动态条件判断**：
```python
conditions = {
    "move_to": [
        {
            "name": "long_distance_move",
            "evaluate": lambda action: distance(action.params["target_pose"]) > 0.5,
            "requires_approval": True
        },
        {
            "name": "high_speed_move",
            "evaluate": lambda action: action.params.get("speed", 0.5) > 0.8,
            "requires_approval": True
        }
    ]
}
```

---

### 3. 两层验证系统

#### 本地验证（LocalValidator）

**何时使用**：所有情况（永不离线）

**包含的校验**：
1. WhitelistValidator（动作是否被允许）
2. BoundaryChecker（参数是否在安全范围）

**特点**：
- 延迟 <10ms
- 缓存在内存中，从配置文件加载
- 不依赖网络

**用途**：
- 核心安全功能，永远不能被关闭
- 即使中央服务不可用，也能进行基础的安全检查

#### 中央验证（CentralValidator）

**何时使用**：网络可用时

**包含的校验**：
1. ConflictDetector（需要实时状态）
2. SecondConfirmation（需要网络联系人工）
3. 自定义校验器（用户扩展）

**特点**：
- 延迟 2-5 秒（包括网络往返）
- 需要网络连接
- 如果不可用，系统自动降级

**降级策略**：
- 网络不可用 → 本地规则继续工作
- 对于高风险操作，改为本地强制人工确认
- 记录网络中断事件，等待网络恢复后同步

---

### 4. 执行层改造

#### ToolBase 基类

**旧接口（废弃）**：
```python
def execute(self, params: dict) -> dict:
    # 同步执行，返回结果
    ...
```

**新接口（推荐）**：
```python
async def execute_with_feedback(self, params: dict, current_state: RobotState) -> AsyncGenerator[ExecutionFeedback, None]:
    # 异步生成器，执行过程中 yield 反馈
    yield ExecutionFeedback(...)
    ...
```

#### ToolAdapter（兼容性适配器）

**用途**：自动将旧接口转换为新接口

**优点**：
- 现有 Tool 无需立即改造
- 在后台线程中运行旧的同步 execute()
- 逐步迁移，无破坏性改动

**迁移路线**：
```
第一阶段（第一周）：
  - 实现 ToolAdapter
  - 所有旧 Tool 用适配器包装
  - 系统可正常工作（但有警告）

第二周：逐个改造 Tool → 新接口
第三周：继续改造
第四周：删除适配器和旧接口支持
```

#### ExecutionConfirmationEngine（执行确认引擎）

**职责**：验证执行结果是否符合期望

**流程**：
1. 收集执行过程中的所有 ExecutionFeedback
2. 获取实际状态
3. 根据 expected_outcome 执行检查
4. 返回 CONFIRMED / PARTIAL / FAILED / TIMEOUT

**检查规则示例**：

对于 `expected_outcome = "arm_reaches_target"`：
```python
checks = [
    {
        "name": "pose_accuracy",
        "evaluate": lambda actual, expected: abs(actual - expected) < 0.002,
        "severity": "critical"  # 失败则整个执行视为失败
    },
    {
        "name": "execution_time_reasonable",
        "evaluate": lambda duration: duration < 10.0,
        "severity": "warning"  # 失败但不致命，需要人工审查
    }
]
```

**决策逻辑**：
- ✅ CONFIRMED：所有检查都通过，继续下一步
- ⚠️ PARTIAL：仅警告级检查失败，需要人工审查后继续
- ❌ FAILED：有关键检查失败，停止执行序列，触发告警
- ⏱️ TIMEOUT：执行超时，询问操作员是否继续

---

### 5. 人工接管机制

#### SystemMode（系统模式状态机）

```
AUTOMATIC ←→ MANUAL_OVERRIDE
    ↓            ↑
  PAUSED ←─────┘
    ↑
EMERGENCY_STOP
```

**四种模式**：

1. **AUTOMATIC**：自动执行，LLM 生成动作序列
2. **MANUAL_OVERRIDE**：人工接管，操作员直接控制
3. **PAUSED**：暂停，等待操作员决策
4. **EMERGENCY_STOP**：紧急停止，所有动作停止

#### 人工干预信号源

**三个渠道**：
1. 紧急按钮（GPIO 17）→ 立即 EMERGENCY_STOP
2. 示教器（示教手柄）→ MANUAL_OVERRIDE + 直接控制
3. Web 仪表板 → PAUSE / RESUME / CANCEL

#### 人工模式下的安全检查

**关键原则**：即使在人工模式，也必须进行**边界检查**

**流程**：
1. 操作员尝试执行动作
2. 系统检查边界（必须）
3. 如果超出边界：
   - ⚠️ 发出 CRITICAL 告警
   - 请求操作员确认是否强制执行
   - 操作员通过**物理按钮**（不是 Web）确认
   - 记录到审计日志
4. 执行动作
5. 完成

#### 状态转换规则

```
AUTOMATIC:
  - 紧急按钮 → EMERGENCY_STOP
  - 示教器激活 → MANUAL_OVERRIDE
  - 暂停命令 → PAUSED

MANUAL_OVERRIDE:
  - 紧急按钮 → EMERGENCY_STOP
  - 示教器释放 + 操作员确认 → AUTOMATIC
  - 无操作超过 5 分钟 → 询问是否恢复自动

PAUSED:
  - 恢复命令 → AUTOMATIC
  - 取消命令 → AUTOMATIC
  - 紧急按钮 → EMERGENCY_STOP

EMERGENCY_STOP:
  - 只有操作员按下恢复按钮 → AUTOMATIC
```

---

## 两层验证系统

### 验证管道流程

```
Action Proposal
    │
    ├─→ 【第一层：本地验证】（总是执行，不能跳过）
    │   ├─ WhitelistValidator
    │   └─ BoundaryChecker
    │
    ├─→ 验证通过？
    │   ├─ NO → 拒绝，返回 REJECTED
    │   └─ YES ↓
    │
    └─→ 【第二层：中央验证】（如果网络可用）
        ├─ ConflictDetector
        ├─ SecondConfirmation
        └─ 自定义校验器

        ├─→ 网络可用？
        │   ├─ NO → 降级模式（见下文）
        │   └─ YES ↓
        │
        ├─→ 验证通过？
        │   ├─ NO → 拒绝
        │   └─ YES → ValidatedAction（允许）
```

### 降级模式（网络中断时）

**触发条件**：中央服务不可用（网络中断、服务崩溃等）

**行为**：
```
高风险操作（move_to、emergency_stop）：
  - 本地强制人工确认（不依赖网络）
  - 记录降级事件到本地日志

低风险操作（gripper_open、vision_capture）：
  - 允许自动执行
  - 记录操作到本地日志

配置选项（approval_policy.yaml）：
  degraded_mode:
    allow_low_risk_actions: true
    high_risk_actions_handling: "local_approval_required"
```

**网络恢复后**：
- 定期尝试重新连接中央服务（每 10 秒）
- 一旦恢复，自动同步本地日志到中央审计系统
- 恢复期间的所有操作都有"降级模式"标记

---

## 闭环执行与确认

### 执行流程（完整）

```
Step 1: 校验
  ActionProposal → ValidationPipeline → ValidatedAction

Step 2: 执行
  ValidatedAction → Tool.execute_with_feedback()

  Tool 在执行过程中持续 yield ExecutionFeedback：
    - STARTED: 0%
    - IN_PROGRESS: 25%, 50%, 75%
    - COMPLETED: 100% 或 FAILED

  执行引擎记录所有 feedback

Step 3: 确认
  确认引擎检查：
    - 实际状态 vs expected_outcome
    - 执行时间是否合理
    - 是否有错误或碰撞

  返回：CONFIRMED / PARTIAL / FAILED / TIMEOUT

Step 4: 决策
  根据确认结果：
    - CONFIRMED → 继续下一个动作
    - PARTIAL → 询问操作员是否继续
    - FAILED → 停止，触发告警
    - TIMEOUT → 询问操作员是否继续

Step 5: 审计
  完整记录到 AuditTrail：
    - 提案信息
    - 校验结果
    - 执行过程
    - 确认结果
    - 时间戳
    - 不可篡改的哈希
```

### 禁止"发出即完成"

**原则**：每个执行都必须有结果确认

```python
async def execute_action_sequence(self, actions: List[ActionProposal]):
    for action in actions:
        # ... 校验 ...

        # 执行
        async for feedback in tool.execute_with_feedback(...):
            if feedback.has_error:
                raise ExecutionError(...)

        # ✨ 必须进行确认，不能跳过
        confirmation = await self.confirmation_engine.confirm_execution_result(...)

        if confirmation.status == ConfirmationStatus.FAILED:
            raise ExecutionError(f"Confirmation failed: {confirmation.reason}")

        # 只有确认通过，才允许继续下一个动作
```

**任何情况都不能跳过确认**，即使：
- 执行看起来成功了
- 操作员很着急
- 这是 Nth 次相同的动作

---

## 人工接管机制

（详见第 8 节中的详细设计）

### 快速参考

| 事件 | 立即动作 | 模式转换 | 记录 |
|-----|--------|--------|------|
| 紧急按钮按下 | 停止所有 Tool | → EMERGENCY_STOP | ✅ 关键 |
| 示教器激活 | 暂停自动执行 | → MANUAL_OVERRIDE | ✅ |
| 示教器控制 | 直接操纵关节/夹爪 | 保持 MANUAL_OVERRIDE | ✅ |
| 边界违反（人工模式） | 发出警报 | 请求人工确认 | ✅ 关键 |
| 示教器释放 | 询问是否恢复自动 | → AUTOMATIC | ✅ |
| Web 暂停命令 | 暂停执行序列 | → PAUSED | ✅ |
| Web 恢复命令 | 继续执行 | → AUTOMATIC | ✅ |

---

## 边界情况处理

### 网络中断

**本设计采用方案 B：基础容错**

```
正常情况（网络可用）：
  本地验证 + 中央验证 → ValidatedAction

网络中断（中央服务不可用）：
  本地验证 + 本地缓存规则 → ValidatedAction（降级）

  - 低风险操作：允许自动执行
  - 高风险操作：本地强制人工确认
  - 所有操作记录到本地日志

网络恢复：
  定期重试连接中央服务
  一旦恢复，同步本地日志
```

**配置**：
```yaml
central_validator:
  timeout_seconds: 5
  fallback_strategy: "local_cached"

degraded_mode:
  high_risk_actions_handling: "local_approval_required"
  network_recovery_check_interval: 10
```

### 执行超时

**定义**：执行超过预定时间（默认 10 秒）

**处理**：
1. 检测到超时
2. 发出 CRITICAL 告警
3. 返回 ConfirmationStatus.TIMEOUT
4. 询问操作员：是否继续下一个动作？
5. 记录到审计日志

```python
confirmation = await confirmation_engine.confirm_execution_result(
    action=action,
    execution_feedback=feedback_list,
    actual_state=actual_state,
    timeout_seconds=10.0  # 配置化
)

if confirmation.status == ConfirmationStatus.TIMEOUT:
    approval = await ask_human_decision(
        "Execution timeout. Continue with next action?"
    )
```

### 硬件故障

**检测**：Tool 的 execute_with_feedback() 中检测到错误

```python
yield ExecutionFeedback(
    stage=ExecutionFeedback.Stage.FAILED,
    has_error=True,
    error_message="Gripper servo fault",
    error_type="hardware"
)
```

**处理**：
1. ExecutionFeedback 包含错误信息
2. 执行引擎检查 `feedback.has_error`
3. 立即抛出 ExecutionError
4. 触发 CRITICAL 告警
5. 记录错误信息到审计日志

### 人工强制执行超出边界的操作

**流程**：
1. 操作员尝试执行超出边界的操作（例：力度 150N，限制 100N）
2. BoundaryChecker 拒绝
3. 发出 CRITICAL 告警
4. 询问操作员是否强制执行（通过物理按钮）
5. 如果同意：
   - 记录"强制执行"事件到审计日志
   - 执行操作
   - 完成后继续
6. 如果拒绝：取消操作

**审计记录示例**：
```
[2026-04-07 10:23:15.125]
  EVENT: alert
  level: CRITICAL
  message: Manual gripper force exceeds safety limit: target=150N not in [0, 100]N

[2026-04-07 10:23:17.500]
  EVENT: approval_granted
  approval_channel: teach_pendant_button

[2026-04-07 10:23:17.501]
  EVENT: manual_operation_forced_execution
  operation_type: gripper_control
  boundary_violation: {"force": 150, "limit": {"min": 0, "max": 100}}
```

---

## 实现路线图

### 阶段化实现（3-5 天）

#### 第一阶段：基础架构和接口定义（1 天）

**目标**：定义新的数据结构和接口，不改动现有执行逻辑

**改动范围**：新增代码，零破坏性改动

**核心产出**：
- ActionProposal / ValidatedAction / ExecutionFeedback 数据结构
- ToolBase 新接口定义（execute_with_feedback）
- ValidationResult / ConfirmationResult 数据结构

**文件**：
```
新增：
  agents/policy/action_proposal.py
  agents/policy/validated_action.py
  agents/execution/tool_base.py （扩展）
  agents/execution/execution_feedback.py
  agents/feedback/execution_log.py
```

#### 第二阶段：规则校验系统实现（1.5 天）

**目标**：实现四大校验器

**核心产出**：
```
新增：
  agents/policy/validators/
    ├─ whitelist_validator.py
    ├─ boundary_checker.py
    ├─ conflict_detector.py
    ├─ second_confirmation.py
  agents/policy/validation_pipeline.py

配置：
  config/whitelist.yaml
  config/safety_limits.yaml
  config/approval_policy.yaml
```

#### 第三阶段：执行层改造和反馈系统（1.5 天）

**目标**：改造 ToolBase 为异步生成器，实现闭环反馈

**核心产出**：
```
改造：
  agents/execution/tool_base.py （实现 execute_with_feedback）
  agents/execution/tools/gripper_tool.py
  agents/execution/tools/move_tool.py
  agents/execution/tools/vision_tool.py

新增：
  agents/execution/tool_adapter.py （兼容性适配器）
  agents/execution/execution_confirmation.py
  agents/feedback/audit_trail.py
  agents/feedback/alert_system.py
```

#### 第四阶段：人工接管和认知层集成（1 天）

**目标**：改造认知层和集成人工接管

**核心产出**：
```
新增：
  agents/human_oversight/human_oversight_engine.py
  agents/human_oversight/system_mode.py

改造：
  agents/cognition/cognition_engine.py （输出 ActionProposal）
  agents/agent.py （集成所有系统）

新增管道：
  agents/pipeline/execution_pipeline.py
```

#### 第五阶段：测试、文档、部署（1 天）

**目标**：单元测试、集成测试、文档

**核心产出**：
```
测试：
  tests/policy/test_validators.py
  tests/feedback/test_confirmation.py
  tests/security/test_reject_dangerous_actions.py
  tests/integration/test_end_to_end.py

文档：
  docs/policy/whitelist_guide.md
  docs/human_oversight/mode_transitions.md
  docs/audit_trail/query_examples.md
```

---

## 配置与扩展

### 配置文件

#### whitelist.yaml

```yaml
allowed_actions:
  move_to:
    dangerous: true
    required_params:
      target_pose: {type: list, length: 3}
      speed: {type: float, min: 0.01, max: 1.0}
  gripper_close:
    dangerous: false
    required_params:
      force: {type: float, min: 0, max: 100}
  # ... 更多动作
```

#### safety_limits.yaml

```yaml
workspace:
  x: {min: 0.1, max: 1.5, unit: "meters"}
  y: {min: -1.0, max: 1.0, unit: "meters"}
  z: {min: 0.0, max: 2.0, unit: "meters"}

gripper_limits:
  min_force: 0
  max_force: 100
  unit: "N"
```

#### approval_policy.yaml

```yaml
approval_rules:
  move_to:
    required: true
    timeout_seconds: 30
    conditions:
      - name: "long_distance_move"
        evaluate: "distance(target_pose) > 0.5"
        requires_approval: true
```

### 自定义校验器

**用户可以添加自定义校验器**：

```python
class EnergyBudgetValidator(Validator):
    def __init__(self, energy_budget_wh: float):
        self.energy_budget_wh = energy_budget_wh

    async def validate(self, action: ActionProposal) -> ValidationResult:
        estimated_energy = self._estimate_energy(action)
        if estimated_energy > self.energy_budget_wh:
            return ValidationResult(valid=False, reason="Energy budget exceeded")
        return ValidationResult(valid=True)

    def priority(self) -> int:
        return 50  # 在其他校验器之后

# 注册到管道
pipeline.register_custom_validator(EnergyBudgetValidator(1000.0))
```

---

## 安全性分析

### 对应工业 Agent "七大铁律"的覆盖

| 铁律 | 设计覆盖 | 具体机制 |
|-----|--------|--------|
| P1 零错误容忍 | ✅ 100% | 白名单 + 边界检查强制过滤任何未授权操作 |
| P2 人工可控 | ✅ 100% | 紧急按钮/示教器/Web 可随时中止，EMERGENCY_STOP 模式 |
| P3 决策分离 | ✅ 100% | 明确的三层架构，LLM 只提案，规则系统执行 |
| P4 闭环设计 | ✅ 100% | 所有执行必须结果确认，禁止"发出即完成" |
| P5 可靠性 | ✅ 85% | 两层验证 + 本地缓存 + 离线降级；不包括边缘计算 |
| P6 安全机制 | ✅ 100% | 完整的白名单、二次确认、审计日志 |
| P7 LLM 隔离 | ✅ 100% | LLM 完全隔离，无直控权 |

### 威胁模型

**威胁 1：LLM 生成危险指令**
- ❌ 不能发生：白名单校验阻止
- ✅ 缓解：所有指令都通过 WhitelistValidator

**威胁 2：网络中断导致系统停止**
- ❌ 不能发生：本地验证继续工作
- ✅ 缓解：两层验证，中央不可用时本地继续

**威胁 3：执行出错但系统不知道**
- ❌ 不能发生：必须结果确认
- ✅ 缓解：所有执行都进行确认检查

**威胁 4：操作员无法中止危险操作**
- ❌ 不能发生：任何时刻可按紧急按钮
- ✅ 缓解：EMERGENCY_STOP 模式立即停止

**威胁 5：审计日志可被篡改**
- ❌ 不能发生：哈希验证防篡改
- ✅ 缓解：完整的 ExecutionLog + AuditTrail

### 安全假设

1. **物理设备假设**：紧急按钮、示教器等物理设备是可靠的
2. **配置假设**：whitelist.yaml、safety_limits.yaml 是准确的
3. **传感器假设**：机器人状态反馈（位置、力度等）是准确的
4. **操作员假设**：操作员能够正确理解系统状态和告警信息

---

## 测试策略

### 单元测试

#### 校验器测试

```python
class TestWhitelistValidator:
    async def test_reject_unauthorized_action(self):
        """拒绝不在白名单中的动作"""
        proposal = ActionProposal(action_type="disable_safety_check")
        result = await validator.validate(proposal)
        assert not result.valid

    async def test_accept_authorized_action(self):
        """接受在白名单中的动作"""
        proposal = ActionProposal(action_type="gripper_close", params={"force": 50})
        result = await validator.validate(proposal)
        assert result.valid

class TestBoundaryChecker:
    async def test_reject_out_of_workspace(self):
        """拒绝超出工作空间的目标"""
        proposal = ActionProposal(action_type="move_to", params={"target_pose": [10, 10, 10]})
        result = await boundary_checker.validate(proposal)
        assert not result.valid

    async def test_accept_in_workspace(self):
        """接受工作空间范围内的目标"""
        proposal = ActionProposal(action_type="move_to", params={"target_pose": [0.5, 0.5, 0.5]})
        result = await boundary_checker.validate(proposal)
        assert result.valid
```

### 集成测试

```python
class TestEndToEnd:
    async def test_complete_execution_flow(self):
        """测试完整的执行流程：提案 → 校验 → 执行 → 确认"""
        proposal = ActionProposal(
            action_sequence=[
                Action(action_type=ActionType.MOVE_TO, ...),
                Action(action_type=ActionType.GRIPPER_CLOSE, ...)
            ]
        )

        result = await execution_pipeline.execute(proposal)

        assert result.success
        assert result.execution_log is not None
        assert len(result.execution_log.events) > 0
```

### 安全测试

```python
class TestSecurityRequirements:
    async def test_reject_dangerous_actions(self):
        """确保系统拒绝危险指令"""
        dangerous_proposals = [
            ActionProposal(action_type="disable_safety_check"),
            ActionProposal(action_type="arbitrary_code_exec"),
        ]

        for proposal in dangerous_proposals:
            result = await validation_pipeline.validate(proposal)
            assert not result.valid

    async def test_human_approval_mandatory(self):
        """确保高危操作强制人工审批"""
        proposal = ActionProposal(action_type="move_to", ...)
        result = await validation_pipeline.validate(proposal)
        assert result.requires_human_approval

    async def test_no_silent_failures(self):
        """确保任何异常都会触发告警"""
        # 模拟硬件故障
        tool.execute_with_feedback.side_effect = HardwareError()

        with pytest.raises(ExecutionError):
            await execution_engine.execute_action_proposal(proposal)

        # 验证告警被触发
        alert_system.raise_alert.assert_called()
```

---

## 附录 A：数据流示例

（详见主体的"完整的数据流示例"章节）

---

## 附录 B：配置变更清单

### 需要添加的新配置文件

```
config/
├─ whitelist.yaml              ← 新增
├─ safety_limits.yaml          ← 新增
├─ approval_policy.yaml        ← 新增
├─ validation_policy.yaml      ← 新增
├─ human_oversight.yaml        ← 新增
└─ tool_migration.yaml         ← 新增
```

### 需要修改的现有配置

```
config/
├─ default_config.yaml         ← 添加新的配置段
└─ environment.yaml            ← 添加环境模式配置
```

---

## 附录 C：迁移检查清单

- [ ] ToolAdapter 实现完成
- [ ] GripperTool 迁移到新接口
- [ ] MoveTool 迁移到新接口
- [ ] VisionTool 迁移到新接口
- [ ] 单元测试全部通过
- [ ] 集成测试全部通过
- [ ] 安全测试全部通过
- [ ] 审计日志正常工作
- [ ] 人工接管正常工作
- [ ] 网络中断场景测试
- [ ] 文档完成
- [ ] 部署前安全审查

---

**文档完成日期**：2026-04-07
**下一步**：设计文档审查 → 实现计划生成
