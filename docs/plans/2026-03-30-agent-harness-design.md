# Agent Harness 集成设计

**日期**: 2026-03-30
**状态**: 设计完成
**目标**: 构建完整的测试 + 仿真 + 监控体系

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Harness Framework (agents/harness/)           │
│                                                                  │
│  ┌──────────┐  ┌───────────────┐  ┌──────────┐  ┌───────────┐ │
│  │ TaskSet  │  │ HarnessEnv    │  │ Tracer   │  │ Evaluator │ │
│  │          │  │ ┌───────────┐ │  │          │  │           │ │
│  │ Declara- │  │ │MockSkill  │ │  │ Step     │  │ Result    │ │
│  │ tive +   │  │ │MockHW     │ │  │ Records  │  │ Efficien. │ │
│  │ Failure  │  │ │MockVLA    │ │  │ Chain    │  │ Robust.   │ │
│  │ Auto     │  │ └───────────┘ │  │ Tool     │  │ Explain.  │ │
│  │ Append   │  │               │  │ Calls    │  │           │ │
│  └──────────┘  └───────────────┘  └──────────┘  └───────────┘ │
│                         │                   │                   │
│                         └─────────┬─────────┘                   │
│                                   ▼                             │
│                            ┌──────────┐                         │
│                            │ Scorer   │                         │
│                            │ Final    │                         │
│                            │ Report   │                         │
│                            └──────────┘                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 RobotAgentLoop (现有代码，完全不变)                 │
│  MessageBus → RobotAgentLoop → CoTTaskPlanner → ToolRegistry   │
└─────────────────────────────────────────────────────────────────┘
```

**关键原则**：
- Harness 是**独立模块**，对现有 `RobotAgentLoop` 代码零侵入
- 通过拦截层在运行时切换 mock/real 模式
- 支持在线（实时运行）和离线（回放日志）两种评估方式

---

## 二、HarnessEnvironment 分层设计

```
HarnessEnvironment（支持运行时切换三种模式）
│
├── Mode.A: SkillMock（技能级模拟）
│   ├── MockGraspSkill / MockPlaceSkill / MockReachSkill ...
│   ├── 返回预设成功/失败结果（基于场景标签）
│   └── 不调用任何真实硬件或 VLA
│
├── Mode.B: HardwareMock（硬件级模拟）
│   ├── MockAGXArmAdapter / MockLeRobotArmAdapter
│   ├── 模拟关节运动、抓取力学、位置误差
│   └── Skill 逻辑完整保留，mock 适配器替代真实硬件
│
└── Mode.C: FullMock（全链路模拟）
    ├── SkillMock + HardwareMock + MockVLAAdapter
    ├── 完整端到端仿真，包含 VLA 推理结果
    └── 用于回归测试和极限场景演练
```

**切换机制**：通过 `agents/harness/config.yaml` 控制

---

## 三、TaskSet 设计

### 3.1 声明式任务定义

任务以 YAML 格式存储在 `agents/harness/tasks/`：

```yaml
task_id: "pick_place_basic_001"
description: "抓取红色方块并放置到B区"
robot_type: "arm"

scene:
  objects:
    - id: "red_cube"
      type: "cube"
      color: "red"
      initial_position: [0.3, -0.1, 0.05]

expected_skills:
  - "manipulation.reach"
  - "manipulation.grasp"
  - "manipulation.place"

success_criteria:
  result:
    type: "position_match"
    object: "red_cube"
    target: "zone_b"
    tolerance: 0.02
  efficiency:
    max_duration_seconds: 30
  robustness:
    max_retry_count: 2
    allowed_failures: ["gripper_slope"]
```

### 3.2 失败数据自动追加

当 `FailureRecorder` 记录失败数据时，Harness 自动追加到 TaskSet：
- `expected_keywords` = 实际调用的 skill 序列
- `success_criteria` = 从 `plan.yaml` 提取目标状态
- 自动标记为 `is_regression: true`

### 3.3 TaskSet 组合

```python
class TaskSet:
    declarative: list[Task]   # YAML 定义的基线任务
    regression: list[Task]    # 失败日志生成的回归任务
    custom: list[Task]        # 运行时动态添加的任务
```

---

## 四、Tracer 追踪设计

### 4.1 追踪数据结构

```python
@dataclass
class HarnessTrace:
    task_id: str
    session_id: str
    mode: HarnessMode
    start_time: datetime
    end_time: datetime | None
    subtask_graph: list[SubtaskRecord]
    tool_calls: list[ToolCallRecord]
    observations: list[ObservationRecord]
    cot_decisions: list[CoTDecisionRecord]
    memory_snapshots: list[MemorySnapshot]
    final_status: TaskStatus
    failure_reason: str | None
```

### 4.2 运行时拦截

通过装饰器/拦截器附加到 `RobotAgentLoop`，不修改原始逻辑：
- 拦截消息接收
- 拦截 CoT 决策
- 拦截工具调用
- 记录内存快照

### 4.3 离线回放

支持从已有日志回放评估，重建完整执行轨迹。

---

## 五、Evaluator 多维度评分设计

### 5.1 四大评估维度

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| **Result** | 0.25 | 任务是否完成、物体位置是否正确、技能调用是否完整 |
| **Efficiency** | 0.25 | 执行时间、工具调用效率 |
| **Robustness** | 0.25 | 重试次数、失败处理、意外错误率 |
| **Explainability** | 0.25 | CoT 推理完整性、决策与观察的一致性 |

### 5.2 评分计算

```python
@dataclass
class EvaluationResult:
    task_id: str
    result_score: EvaluationScore      # 0.0-1.0
    efficiency_score: EvaluationScore
    robustness_score: EvaluationScore
    explainability_score: EvaluationScore
    total_score: float
    overall_passed: bool               # >= pass_threshold (默认 0.70)
```

---

## 六、目录结构

```
agents/harness/
├── __init__.py
├── config.yaml                     # 全局配置
│
├── core/
│   ├── __init__.py
│   ├── task_set.py               # TaskSet + Task
│   ├── task_loader.py            # 任务加载器
│   ├── harness_env.py            # 分层 mock 环境
│   ├── tracer.py                 # 运行时追踪
│   ├── trace_replayer.py         # 离线回放
│   ├── evaluators/
│   │   ├── base.py
│   │   ├── result_eval.py
│   │   ├── efficiency_eval.py
│   │   ├── robustness_eval.py
│   │   └── explainability_eval.py
│   ├── scorer.py
│   └── mode.py
│
├── mocks/
│   ├── __init__.py
│   ├── skill_mocks.py
│   ├── hardware_mocks.py
│   └── vla_mocks.py
│
├── tasks/
│   ├── README.yaml
│   ├── pick_place_basic.yaml
│   └── inspect_task.yaml
│
├── traces/
│
└── examples/
    ├── run_harness.py
    └── batch_evaluate.py
```

---

## 七、与现有系统集成

### 7.1 AgentLoop 装饰器

```python
from agents.harness import attach_harness

# 手动附加（按需启用）
loop, tracer = attach_harness(existing_agent_loop, config)
```

### 7.2 配置开关

```yaml
harness:
  auto_attach: true  # 启动时自动注入
  mode: "hardware_mock"
```

### 7.3 使用模式

| 模式 | 侵入性 | 适用场景 |
|------|--------|----------|
| 手动附加 | 无 | 开发测试、评估 |
| 自动包含 | 低 | 标准化测试流程 |
| 仅监控 | 极低 | 生产环境监控 |

---

## 八、完整工作流程

### 开发测试流程

```
编写 Task(YAML) → 运行 Harness → Mock 执行 → Tracer 记录 → 四维评估 → Scorer 报告
```

### 仿真测试流程

```
配置 mode: hardware_mock → 无需真实硬件 → 回归测试
```

### 生产监控流程

```
配置 mode: real + tracing_enabled → 仅记录轨迹 → 事后评估
```
