:orphan:

# 仿真验证 + 前端交互式调试工具设计文档

**日期**: 2026-04-17  
**版本**: v1.0  
**作者**: EmbodiedAgentsSys 团队  
**状态**: 设计阶段  

---

## 1. 概述

### 目标
基于 Franka 机器人仿真环境，构建一个交互式前端调试工具，验证四层架构（感知→认知→执行→反馈）的完整端到端流程。

### 范围
- **验证对象**：SimpleAgent 四层架构的完整端到端流程
- **仿真环境**：Franka 机器人 MuJoCo 仿真
- **前端功能**：交互式任务构造和实时推理过程可视化
- **测试场景**：5 个基础场景（空间检测、单一抓取、抓取+移动、错误恢复、动态环境）
- **使用方式**：MVP 先自己用，后续给客户演示

### 核心价值
✅ 可视化推理过程（实时看到每层的决策）  
✅ 交互式调试（手动输入任务和观察数据）  
✅ 端到端验证（完整四层流程在仿真中运行）  
✅ 客户展示就绪（Web 框架，易于部署）

---

## 2. 架构设计

### 2.1 系统整体架构

```
┌──────────────────────────────────────────────────────┐
│                  前端层（Web UI）                     │
│  React + WebSocket 客户端                            │
│  ├─ Task 输入面板                                    │
│  ├─ Observation 输入面板                             │
│  ├─ 四层实时监控面板                                │
│  └─ 结果展示面板                                    │
└──────────────────┬───────────────────────────────────┘
                   │
             WebSocket (双向)
                   │
┌──────────────────▼───────────────────────────────────┐
│              后端层（FastAPI）                        │
│  ├─ WebSocket Manager（连接管理）                   │
│  ├─ Agent Bridge（SimpleAgent 包装）                │
│  │  └─ Hook 实现（四层中间件）                       │
│  ├─ Simulation Bridge（仿真环境）                   │
│  └─ Data Models（数据模型）                        │
└──────────────────┬───────────────────────────────────┘
                   │
         内部函数调用
                   │
┌──────────────────▼───────────────────────────────────┐
│          仿真与代理核心层                             │
│  ├─ SimpleAgent (现有四层架构)                       │
│  ├─ Franka MuJoCo 仿真                              │
│  └─ RobotObservation (感知数据)                     │
└──────────────────────────────────────────────────────┘
```

### 2.2 后端架构详设

#### 文件结构
```
backend/
├── app.py                    # FastAPI 主应用
├── websocket_manager.py      # WebSocket 连接和消息管理
├── agent_bridge.py           # SimpleAgent 包装层 + Hook 实现
├── simulation.py             # Franka 仿真环境
├── models.py                 # 数据模型（Pydantic）
├── config.py                 # 配置文件
└── scenarios.py              # 5 个测试场景定义
```

#### 核心类设计

**WebSocketManager**
```python
class WebSocketManager:
    """管理所有 WebSocket 连接和消息分发"""
    
    async def broadcast(self, message: Dict):
        """广播消息给所有连接的客户端"""
    
    async def send_to_client(self, client_id: str, message: Dict):
        """发送消息给特定客户端"""
    
    async def add_client(self, websocket):
        """添加新客户端"""
    
    async def remove_client(self, websocket):
        """移除断开连接的客户端"""
```

**AgentBridge**
```python
class AgentBridge:
    """包装 SimpleAgent，添加 Hook 实现实时推理过程推送"""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.agent = SimpleAgent.from_preset('default')
        self.ws_manager = ws_manager
        self.hooks = {}
    
    def register_planning_hook(self, callback):
        """注册到 Planning 层的钩子"""
        # 捕获任务分解、计划生成等步骤
    
    def register_reasoning_hook(self, callback):
        """注册到 Reasoning 层的钩子"""
        # 捕获推理过程、动作选择等
    
    def register_learning_hook(self, callback):
        """注册到 Learning 层的钩子"""
        # 捕获反馈分析、改进建议等
    
    async def run_with_telemetry(self, task: str, observation: RobotObservation):
        """执行任务并实时推送四层处理过程"""
        # 1. 发送 task_start 消息
        # 2. 调用 agent.run_task()
        # 3. Hook 捕获每一步并通过 WebSocket 推送
        # 4. 返回最终结果
```

**FrankaBridge**
```python
class FrankaBridge:
    """Franka 仿真环境的包装"""
    
    def __init__(self):
        self.env = self._init_franka_mujoco()
        self.robot_state = None
    
    def _init_franka_mujoco(self):
        """初始化 Franka MuJoCo 仿真环境"""
    
    async def execute_action(self, action: Action) -> RobotObservation:
        """执行动作并返回新观察"""
        self.env.step(action)
        self.robot_state = self._read_state()
        return self.robot_state
    
    def _read_state(self) -> RobotObservation:
        """从仿真读取完整的机器人状态"""
        return RobotObservation(
            joint_positions=...,
            joint_velocities=...,
            ee_position=...,
            gripper_state=...,
            # ... 其他传感器
        )
    
    def reset(self):
        """重置仿真环境"""
```

#### WebSocket 消息格式

**前端 → 后端**
```json
{
  "type": "execute_task",
  "task": "pick up the red cube",
  "observation": {
    "joint_positions": [...],
    "joint_velocities": [...],
    "ee_position": [...],
    "gripper_state": "open",
    "objects": [{"name": "red_cube", "pose": {...}}]
  }
}
```

**后端 → 前端（实时推送）**
```json
{
  "type": "planning",
  "timestamp": 1713350000.0,
  "status": "in_progress",
  "data": {
    "task": "pick up the red cube",
    "plan": [
      {"step": 1, "action": "move to cube"},
      {"step": 2, "action": "open gripper"},
      {"step": 3, "action": "grasp"}
    ]
  }
}
```

```json
{
  "type": "reasoning",
  "timestamp": 1713350001.0,
  "status": "in_progress",
  "data": {
    "current_plan_step": 1,
    "selected_action": "move to cube",
    "confidence": 0.95,
    "alternative_actions": [...]
  }
}
```

```json
{
  "type": "learning",
  "timestamp": 1713350002.0,
  "status": "completed",
  "data": {
    "feedback": "action succeeded",
    "reward": 0.8,
    "improvements": ["plan was optimal"]
  }
}
```

```json
{
  "type": "result",
  "timestamp": 1713350003.0,
  "status": "completed",
  "data": {
    "task_success": true,
    "final_observation": {...},
    "execution_summary": {...}
  }
}
```

### 2.3 前端架构详设

#### 文件结构
```
frontend/
├── src/
│   ├── components/
│   │   ├── TaskPanel.tsx          # 任务输入
│   │   ├── ObservationPanel.tsx    # 观察数据输入
│   │   ├── ExecutionMonitor.tsx    # 四层实时监控
│   │   ├── ResultPanel.tsx         # 最终结果显示
│   │   └── RobotVisualization.tsx  # 机器人 3D 可视化（可选）
│   ├── hooks/
│   │   └── useWebSocket.ts         # WebSocket 连接管理
│   ├── App.tsx                     # 主应用
│   ├── App.css                     # 样式
│   └── types.ts                    # TypeScript 类型定义
├── package.json
└── tsconfig.json
```

#### 组件设计

**TaskPanel**
- 输入框：用户输入任务描述（如 "pick up the red cube"）
- 预设场景按钮：快速选择 5 个测试场景之一
- 执行按钮：触发后端任务执行

**ObservationPanel**
- 显示当前机器人状态：joint positions, gripper state 等
- 对象识别结果：显示在场景中检测到的物体列表
- 手动编辑观察数据的选项（用于调试）

**ExecutionMonitor**
- 四个实时展示区域：
  - **Planning 区**：显示任务分解和计划生成过程
  - **Reasoning 区**：显示推理过程和动作选择
  - **Learning 区**：显示反馈分析和改进建议
  - **Execution 区**：显示动作执行结果和仿真状态变化

**ResultPanel**
- 任务成功/失败标志
- 执行时间、步数等统计信息
- 完整的执行日志（可折叠/展开）

#### 前端界面布局

```
┌──────────────────────────────────────────────────────┐
│         仿真验证 - 交互式调试工具 v1.0               │
├──────────────────────────────────────────────────────┤
│ [TaskPanel]              │ [ExecutionMonitor]         │
│ ┌────────────────────┐   │ ┌────────────────────────┐ │
│ │ 任务描述输入       │   │ │ Planning Layer         │ │
│ │ [_______________]  │   │ │ • 任务: xxx            │ │
│ │                    │   │ │ • 计划: [...]          │ │
│ │ 预设场景:          │   │ │ • 步骤数: 5            │ │
│ │ [场景1] [场景2]    │   │ └────────────────────────┘ │
│ │ [场景3] [场景4]    │   │ ┌────────────────────────┐ │
│ │ [场景5]            │   │ │ Reasoning Layer        │ │
│ │                    │   │ │ • 推理步骤: xxx        │ │
│ │ [执行] [重置]      │   │ │ • 置信度: 0.95         │ │
│ └────────────────────┘   │ └────────────────────────┘ │
│                          │ ┌────────────────────────┐ │
│ [ObservationPanel]       │ │ Learning Layer         │ │
│ ┌────────────────────┐   │ │ • 反馈: 成功           │ │
│ │ 机器人状态:        │   │ │ • 奖励: 0.8            │ │
│ │ • Joint 0: 0.5     │   │ │ • 改进: [...]          │ │
│ │ • Joint 1: 0.3     │   │ │ └────────────────────────┘ │
│ │ • Gripper: open    │   │ ┌────────────────────────┐ │
│ │                    │   │ │ Execution Result       │ │
│ │ 检测到的物体:      │   │ │ • 状态: 成功           │ │
│ │ • red_cube         │   │ │ • 耗时: 2.3s           │ │
│ │ • blue_block       │   │ │ • 步数: 5              │ │
│ └────────────────────┘   │ └────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│ [ResultPanel]                                         │
│ ┌──────────────────────────────────────────────────┐ │
│ │ 任务完成 ✓ | 执行日志 [展开]                     │ │
│ │ 日志: Planning -> Reasoning -> Learning -> Done  │ │
│ └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 3. 数据流与集成

### 3.1 完整的端到端数据流

```
1. 用户在前端 TaskPanel 输入任务
        ↓
2. 前端通过 WebSocket 发送: {"type": "execute_task", ...}
        ↓
3. 后端 WebSocket Manager 接收
        ↓
4. AgentBridge.run_with_telemetry() 开始执行
        ↓
5. Hook 捕获 Planning 层的输出 → WebSocket 推送给前端
        ↓
6. 前端 ExecutionMonitor.Planning 实时显示
        ↓
7. Hook 捕获 Reasoning 层的输出 → WebSocket 推送给前端
        ↓
8. 前端 ExecutionMonitor.Reasoning 实时显示
        ↓
9. Execution 层执行到 FrankaBridge → 仿真环节
        ↓
10. Hook 捕获 Learning 层的输出 → WebSocket 推送给前端
        ↓
11. 前端 ExecutionMonitor.Learning 实时显示
        ↓
12. 任务完成，发送最终结果给前端
        ↓
13. 前端 ResultPanel 显示完整结果
```

### 3.2 与现有架构的集成点

| 集成点 | 说明 | 实现方式 |
|--------|------|---------|
| SimpleAgent | 现有四层架构核心 | AgentBridge 直接调用 |
| RobotObservation | 感知数据结构 | 作为输入/输出数据模型 |
| PlanningLayer | 计划层 | Hook 到 CognitionEngine |
| ReasoningLayer | 推理层 | Hook 到 CognitionEngine |
| LearningLayer | 学习层 | Hook 到 FeedbackLoop |
| RobotAgentLoop | 核心循环 | 通过 SimpleAgent.run_task() 调用 |

---

## 4. 测试场景设计

### 场景 1：空间检测（Perception + Planning）
**目的**：验证感知层和规划层的协同  
**步骤**：
1. 初始化场景：放置多个物体在工作空间
2. 机器人扫描环境，识别物体位置
3. Planning 层分析物体关系，生成搜索计划

**验证要点**：
- ✓ 感知数据正确传入
- ✓ Planning 层能正确分解任务
- ✓ 前端实时显示规划过程

---

### 场景 2：单一抓取（完整四层）
**目的**：验证完整的四层架构  
**步骤**：
1. 给定目标物体
2. Planning：生成抓取计划
3. Reasoning：选择最优抓取方式
4. Execution：执行抓取动作
5. Learning：评估抓取成功与失败

**验证要点**：
- ✓ 任务→计划→推理→执行→学习完整流程
- ✓ 仿真环境正确反馈物体被抓起
- ✓ WebSocket 实时推送四层信息

---

### 场景 3：抓取 + 移动（多步执行）
**目的**：验证多步规划和执行的连贯性  
**步骤**：
1. 目标：抓取红色立方体并移动到蓝色区域
2. Planning：分解为 [移动→抓取→移动到目标→放置]
3. 逐步执行，每个子任务都完成学习反馈

**验证要点**：
- ✓ 多步计划的正确生成
- ✓ 步骤间的状态传递
- ✓ 累积反馈的学习效果

---

### 场景 4：错误恢复（Learning 层）
**目的**：验证 Learning 层的反馈和自适应  
**步骤**：
1. 尝试抓取物体（故意设置高难度或冲突）
2. 执行失败，Learning 层分析原因
3. 生成改进建议（如调整抓取角度）
4. 重试执行

**验证要点**：
- ✓ 错误检测和反馈分析
- ✓ Learning 层的改进建议
- ✓ 重试执行的成功率提升

---

### 场景 5：动态环境（Reasoning 自适应）
**目的**：验证 Reasoning 层的实时自适应  
**步骤**：
1. 执行任务中途，环境状态变化（如物体被移动）
2. Reasoning 层检测到变化，重新推理
3. 调整执行策略

**验证要点**：
- ✓ 动态观察变化的检测
- ✓ Reasoning 层的重新推理
- ✓ 自适应执行策略的生成

---

## 5. 技术栈选择

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| **后端框架** | FastAPI | 异步优先，高性能，内置 WebSocket |
| **WebSocket** | FastAPI Starlette | 与框架集成 |
| **仿真环境** | MuJoCo | 高精度 Franka 模型，Python API |
| **前端框架** | React 18+ | 组件化，TypeScript 支持 |
| **前端通信** | react-use-websocket | 专业的 React WebSocket Hook |
| **可视化** | Three.js 或 Plotly | 3D 显示机器人状态（可选） |
| **样式** | Tailwind CSS | 快速原型开发 |
| **部署** | Docker | 容器化，易于演示 |

---

## 6. 实施阶段划分

### 阶段 1：后端基础（3-4 天）
**交付物**：可运行的 FastAPI + WebSocket 服务器

- [ ] 项目结构和环境配置
- [ ] FastAPI 应用和 WebSocket Manager 实现
- [ ] FrankaBridge 初始化和状态读取
- [ ] AgentBridge 和 Hook 系统
- [ ] 5 个场景的仿真脚本
- [ ] 后端功能单元测试

### 阶段 2：前端基础（3-4 天）
**交付物**：可连接后端的 React 前端

- [ ] React 项目初始化和依赖配置
- [ ] WebSocket 连接管理 Hook
- [ ] 4 个核心组件实现（TaskPanel、ObservationPanel 等）
- [ ] 基础布局和样式
- [ ] 前端功能测试

### 阶段 3：集成与验证（2-3 天）
**交付物**：端到端可运行系统

- [ ] 后端和前端集成测试
- [ ] 5 个场景逐个验证
- [ ] Bug 修复和性能优化
- [ ] 本地部署验证

### 阶段 4：展示优化（可选，1-2 天）
**交付物**：生产级演示系统

- [ ] 机器人 3D 可视化（可选）
- [ ] 执行过程动画（可选）
- [ ] 性能指标展示板（可选）
- [ ] Docker 容器化
- [ ] 部署文档

**总耗时**：10-15 天（MVP） + 后续为客户优化

---

## 7. 成功标准

### 功能验收
- ✅ 前端可正确连接后端
- ✅ 5 个场景都能完整执行
- ✅ 四层架构的每一步都能实时显示
- ✅ 仿真环境正确反馈机器人状态
- ✅ WebSocket 消息没有丢失或延迟过大

### 性能标准
- ✅ 单步推理时间 < 500ms
- ✅ WebSocket 消息延迟 < 100ms
- ✅ 内存占用稳定（无泄漏）
- ✅ 前端 UI 流畅（60fps）

### 代码质量
- ✅ 后端有单元测试
- ✅ 代码有清晰的文档
- ✅ 类型注解完整（Python + TypeScript）
- ✅ 错误处理完善

---

## 8. 后续展望

### 短期（MVP 后）
- 集成真实的 Franka 硬件测试
- 增加更多测试场景
- 优化 WebSocket 性能

### 中期（客户演示前）
- 添加 3D 机器人可视化
- 支持场景录制和回放
- 添加性能分析仪表板

### 长期（生产部署）
- 云端部署支持
- 多用户并发支持
- 与真实机器人的实时同步

---

## 9. 风险与缓解方案

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| Franka 仿真环境集成困难 | 中 | 高 | 提前验证 MuJoCo Franka 模型，准备备选方案 |
| WebSocket 实时性不达预期 | 低 | 中 | 优化消息频率和大小，考虑消息压缩 |
| Hook 系统对现有架构的侵入过大 | 低 | 中 | 使用 Callback 模式，保持现有代码不变 |
| 前端和后端集成延迟 | 中 | 中 | 并行开发，定期集成测试 |

---

## 10. 参考文档

- SimpleAgent 设计文档
- RobotObservation 数据模型
- 四层架构详设（Planning/Reasoning/Learning/Execution）
- Franka MuJoCo 文档

---

**文档版本历史**

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| v1.0 | 2026-04-17 | AI Assistant | 初版完成 |

