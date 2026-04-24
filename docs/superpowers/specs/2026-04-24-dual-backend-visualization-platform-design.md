# 双后端机器人仿真与统一前端展示平台设计文档

**文档版本**: 1.0
**创建日期**: 2026-04-24
**作者**: Codex (Brainstorming + Self-Review)
**项目**: EmbodiedAgentsSys
**设计方案**: MuJoCo + ROS2 Humble/Gazebo 双后端并行，Vue3 + Three.js 统一展示

---

## 目录

1. [执行摘要](#执行摘要)
2. [背景与约束](#背景与约束)
3. [设计目标](#设计目标)
4. [总体架构](#总体架构)
5. [核心设计原则](#核心设计原则)
6. [模块划分](#模块划分)
7. [统一数据模型](#统一数据模型)
8. [接口设计](#接口设计)
9. [WebSocket 实时消息模型](#websocket-实时消息模型)
10. [前端展示与数据源切换](#前端展示与数据源切换)
11. [后端适配层设计](#后端适配层设计)
12. [并发与状态流转模型](#并发与状态流转模型)
13. [错误处理与可观测性](#错误处理与可观测性)
14. [测试策略](#测试策略)
15. [对当前代码库的具体修改建议](#对当前代码库的具体修改建议)
16. [实施边界与非目标](#实施边界与非目标)

---

## 执行摘要

本设计面向一个明确目标：系统需要同时支持 `MuJoCo` 本地轻量仿真后端、`ROS2 Humble + Gazebo` 标准仿真后端，并通过现有 `Vue3 + Three.js` 前端统一展示机器人仿真效果、训练后效果和部署效果，同时支持前端实时切换数据源。

当前项目已经具备 `FastAPI + WebSocket + MuJoCo` 的基础能力，但主要问题是接口层、状态管理层和仿真层耦合过深。现状更接近单后端演示系统，而不是双后端统一展示平台。

本设计的核心改进如下：

- 保留 `MuJoCo` 作为本地开发和轻量仿真后端
- 新增 `ROS2 Humble + Gazebo` 作为标准仿真与联调后端
- 在后端内部建立统一状态模型与统一场景模型
- 为 `Vue3 + Three.js` 提供稳定的展示协议，而不是仅提供控制接口
- 支持前端实时切换显示数据源
- 允许暴露后端特有能力，但不污染公共主链路

本设计的最终结果不是“多加一个 ROS2 接口”，而是把 EmbodiedAgentsSys 演进为一个统一控制面与统一展示面的机器人仿真平台。

---

## 背景与约束

### 当前代码现状

当前后端已包含以下基础能力：

- `FastAPI` 服务入口和基础路由
- `WebSocket` 状态推送与任务流式输出
- 基于 `MuJoCoDriver` 的仿真服务
- 面向前端的基础状态与场景查询接口
- 已有的 `Vue3 + Three.js` 页面可展示机器人仿真效果

当前主要结构问题：

1. `backend/services/simulation.py` 直接绑定 `MuJoCo`
2. `backend/api/state.py` 使用进程内 `_current_states` 作为状态存储
3. `backend/services/websocket_manager.py` 以简单广播为主，缺少订阅、过滤、背压与心跳
4. `backend/api/agent_ws.py` 混合了任务执行与事件广播语义
5. 前端展示能力已有实现，但后端尚未明确把“统一展示协议”作为正式架构目标

### 已确认约束

本设计基于以下用户确认的约束：

- 保留 `MuJoCo` 作为本地轻量仿真后端
- 新增 `ROS2 Humble + Gazebo` 后端并行支持
- 允许暴露部分后端特有能力
- 前端网页是正式能力，用于显示机器人仿真、训练和部署效果
- 前端页面需要支持实时切换数据源

---

## 设计目标

### 功能目标

1. 同时支持 `MuJoCo` 和 `ROS2 Humble + Gazebo`
2. 对前端提供统一的场景展示协议
3. 支持前端按需实时切换当前显示的数据源
4. 对外提供统一控制接口，同时允许后端扩展接口
5. 支持机器人状态、场景状态、任务状态的实时同步

### 非功能目标

1. 不破坏现有前端展示主链路
2. 保持接口层异步化，避免长任务阻塞请求生命周期
3. 提升后端可扩展性，使未来可接入真实机器人或更多仿真后端
4. 提升状态同步稳定性与可观测性
5. 支持测试分层，尽量降低对真实 ROS2/Gazebo 环境的硬依赖

---

## 总体架构

### 四层结构

```text
┌─────────────────────────────────────────────────────────┐
│ 接入层                                                  │
│ FastAPI / HTTP / WebSocket / Pydantic                  │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 应用层                                                  │
│ TaskService / SceneService / StateService / Registry   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 后端适配层                                              │
│ MujocoBackend / ROS2GazeboBackend                      │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 基础设施层                                              │
│ MuJoCoDriver / ROS2 Node / Gazebo / Event Bus / Cache  │
└─────────────────────────────────────────────────────────┘
```

### 分层职责

- 接入层只处理协议、校验和连接
- 应用层负责任务编排、状态聚合、前端展示模型生成
- 后端适配层负责屏蔽 `MuJoCo` 与 `ROS2/Gazebo` 差异
- 基础设施层负责和底层驱动、ROS2 节点、Gazebo、缓存、消息分发交互

该分层的核心是：API 层不直接 `import mujoco` 或 `rclpy`，应用层也不直接操作底层 driver。

---

## 核心设计原则

### 1. 控制面统一，展示面单独建模

机器人控制接口和前端展示接口不能混在一起。控制面关注命令、任务、回执；展示面关注场景连续性、位姿更新、状态可视化。

### 2. 公共能力稳定，扩展能力显式暴露

公共接口覆盖大多数前端和业务调用需求。后端特有能力通过显式扩展接口暴露，避免把 ROS2 或 MuJoCo 特性揉进公共 schema。

### 3. 双后端并行，而不是相互替代

`MuJoCo` 继续承担轻量、快速、本地仿真角色。`ROS2 Humble + Gazebo` 提供更标准的仿真与联调环境。两者是并列后端，不存在“先废弃 MuJoCo 再接 ROS2”的路径依赖。

### 4. 前端是正式消费者

`Vue3 + Three.js` 页面不是调试附属品，而是系统正式输出面。因此后端必须显式保证面向前端的场景协议稳定。

### 5. 数据源切换是平台级能力

切换 `MuJoCo`、`ROS2/Gazebo`、未来真实机器人，不应由前端写多套协议，而应由后端通过统一模型和统一消息 envelope 支撑。

---

## 模块划分

建议新增并重组以下模块：

```text
backend/
  backends/
    base.py
    mujoco_backend.py
    ros2_gazebo_backend.py
  models/
    messages.py
    scene.py
    state.py
    tasks.py
  services/
    backend_registry.py
    task_service.py
    state_store.py
    scene_service.py
    event_bus.py
    websocket_hub.py
```

### 模块职责

- `base.py`: 定义统一 backend 接口
- `mujoco_backend.py`: 封装现有 MuJoCo 运行时能力
- `ros2_gazebo_backend.py`: 封装 ROS2 节点、Gazebo 通信和状态转换
- `backend_registry.py`: 维护可用后端、默认后端、当前选中后端
- `task_service.py`: 任务提交、生命周期管理、结果查询
- `state_store.py`: 聚合机器人状态和任务状态
- `scene_service.py`: 生成前端展示所需场景模型
- `event_bus.py`: 后台事件流分发
- `websocket_hub.py`: WebSocket 连接管理、订阅、心跳、过滤和发送队列

---

## 统一数据模型

### BackendDescriptor

用于表示后端及其能力。

```python
class BackendDescriptor(BaseModel):
    backend_id: str
    display_name: str
    kind: Literal["mujoco", "ros2_gazebo"]
    available: bool
    capabilities: list[str]
    extensions: dict[str, Any] = {}
```

### RobotRuntimeState

用于表示控制和状态同步层关心的机器人运行状态。

```python
class RobotRuntimeState(BaseModel):
    robot_id: str
    backend: str
    timestamp: float
    joints: list[JointState]
    pose: Pose | None = None
    gripper: dict[str, float] = {}
    sensors: dict[str, Any] = {}
    status: str = "idle"
```

### SceneViewModel

用于给前端 Three.js 页面渲染的统一场景模型。

```python
class SceneViewModel(BaseModel):
    backend: str
    timestamp: float
    robots: list[RobotView]
    objects: list[SceneObjectView]
    overlays: list[OverlayView] = []
    metadata: dict[str, Any] = {}
```

### 设计约束

- `RobotRuntimeState` 面向执行和状态同步
- `SceneViewModel` 面向展示和渲染
- 这两个模型必须解耦，避免为了前端显示污染控制模型

---

## 接口设计

### 公共接口

- `GET /api/backends`
  返回可用后端、默认后端、能力集合

- `POST /api/backends/select`
  选择当前默认展示或控制数据源

- `GET /api/robots/{robot_id}/state`
  查询当前聚合状态

- `GET /api/view/scene`
  获取当前数据源的场景快照

- `POST /api/commands/execute`
  提交动作或控制命令

- `POST /api/tasks`
  提交异步任务，返回 `task_id`

- `GET /api/tasks/{task_id}`
  查询任务状态和结果

- `WS /api/ws`
  统一实时消息入口

### 后端扩展接口

- `/api/backends/mujoco/*`
  暴露 MuJoCo viewer、调试状态、接触信息等扩展能力

- `/api/backends/ros2/*`
  暴露 ROS2 topics、service、action、Gazebo 实体管理等扩展能力

### 设计原则

- 公共接口覆盖常规控制与展示需求
- 扩展接口只承担特有能力，不回流污染主协议
- 对前端来说，日常渲染应主要依赖公共展示接口

---

## WebSocket 实时消息模型

建议统一采用 envelope 结构：

```json
{
  "event": "scene_delta",
  "backend": "mujoco",
  "robot_id": "arm_001",
  "ts": 1777000000.123,
  "seq": 10452,
  "task_id": null,
  "payload": {},
  "extensions": {}
}
```

### 标准事件类型

- `scene_snapshot`
- `scene_delta`
- `robot_state`
- `task_update`
- `command_ack`
- `telemetry`
- `warning`
- `error`
- `heartbeat`

### 设计要求

- `scene_snapshot` 用于首次连接、数据源切换、场景重置
- `scene_delta` 用于高频增量更新
- `robot_state` 用于关节、位姿等高频状态流
- `task_update` 用于任务执行进度与最终结果
- `heartbeat` 用于连接保活和延迟测量

### WebSocket 管理要求

- 支持按 `backend`、`robot_id`、`event` 订阅
- 每个连接独立发送队列，避免慢消费者阻塞全局
- 支持心跳、断线清理和重连
- 广播失败时不影响状态写入

---

## 前端展示与数据源切换

### 前端定位

前端网页承担三类展示目标：

1. 显示机器人仿真效果
2. 显示训练后机器人效果
3. 显示机器人部署后的效果

这意味着前端不只是“看 MuJoCo 动画”，而是统一承载仿真态、训练态和部署态的可视化输出。

### 数据源切换流程

建议前端支持如下流程：

1. 用户选择 `mujoco` 或 `ros2_gazebo`
2. 前端调用 `POST /api/backends/select`
3. 前端通过 WebSocket 发送新的订阅意图
4. 服务端立即推送对应 `scene_snapshot`
5. 后续持续推送 `scene_delta` 和 `robot_state`

### 前端设计约束

- Three.js 页面只依赖统一场景 DTO
- 页面不直接理解底层是 MuJoCo 还是 Gazebo
- 若需展示特有可视化元素，可通过 `extensions` 有条件渲染

### 兼容性要求

- 设计必须优先保证现有前端展示能力能平滑迁移
- 新协议不要求前端永久兼容旧字段，但迁移期应通过映射层减小改动成本

---

## 后端适配层设计

### BaseBackend 抽象

统一抽象应至少定义：

- `start()`
- `stop()`
- `health()`
- `get_state(robot_id)`
- `get_scene()`
- `execute_command(command)`
- `submit_task(task)`
- `subscribe_events()`
- `list_capabilities()`

### MujocoBackend

职责：

- 复用并封装现有 `MuJoCoDriver`
- 提供本地快速仿真
- 对外输出统一状态模型和统一场景模型
- 支持 MuJoCo 调试扩展能力

### ROS2GazeboBackend

职责：

- 对接 `ROS2 Humble`
- 订阅 joint states、pose、sensor topics
- 调用 ROS2 service 或 action 下发控制命令
- 对接 Gazebo 场景状态或实体管理能力
- 把 ROS2/Gazebo 数据转换为统一模型

### ROS2 接入建议

推荐主实现优先使用 `rclpy`，原因：

- 类型和语义更清晰
- 链路更短
- 更适合长期工程化维护

若有调试、跨进程或外部接入需求，可保留 `rosbridge` 作为辅助接入方式，但不建议作为主控制链路。

---

## 并发与状态流转模型

### 命令流

```text
HTTP/WS 请求
  -> TaskService / CommandService
  -> BackendRegistry 路由
  -> 指定 Backend 执行
  -> 写入 TaskState
  -> 通过 EventBus 推送 task_update / command_ack
```

### 状态流

```text
MuJoCo step / ROS2 topic callback
  -> Backend 生成标准事件
  -> EventBus
  -> StateStore / SceneService 更新缓存
  -> WebSocketHub 推送 robot_state / scene_delta
```

### 并发设计要求

- 请求处理与状态广播解耦
- 后端执行与 WebSocket 广播解耦
- 长任务统一走任务注册表，而不是阻塞 HTTP 请求
- 状态广播失败不回滚状态缓存

---

## 错误处理与可观测性

### 统一错误模型

```python
class ApiError(BaseModel):
    code: str
    message: str
    backend: str | None = None
    retryable: bool = False
    task_id: str | None = None
    details: dict[str, Any] = {}
    ts: float
```

### 典型错误类别

- 后端未初始化
- MuJoCo viewer 启动失败
- ROS2 节点未连接
- Gazebo service 超时
- WebSocket 订阅参数非法
- 任务执行超时
- 场景快照生成失败

### 可观测性建议

- 为任务、状态事件、后端健康检查增加统一日志字段
- 为消息流增加 `seq` 与 `ts`
- 为前端切换数据源记录切换事件
- 为双后端状态转换增加诊断日志，便于定位字段映射问题

---

## 测试策略

### 1. 单元测试

覆盖：

- 数据模型校验
- backend 抽象行为
- 状态转换逻辑
- SceneViewModel 生成逻辑
- 消息 envelope 格式

### 2. 适配层测试

- `MujocoBackend` 使用 headless 或 mock driver
- `ROS2GazeboBackend` 使用 fake node / fake topic / fake service

目标是验证输入输出映射，不依赖真实 Gazebo。

### 3. 集成测试

验证：

- HTTP 接口创建任务
- WebSocket 接收标准事件
- 后端切换后能收到新的 `scene_snapshot`
- 状态订阅过滤按预期工作

### 4. 端到端测试

在真实 `ROS2 Humble + Gazebo` 环境下验证：

- joint state 同步
- 任务控制
- 场景展示
- 数据源切换

该层建议作为独立 smoke 或 nightly 流水线，而不是每次开发都全跑。

---

## 对当前代码库的具体修改建议

### 优先级一：解耦当前 MuJoCo 单后端结构

- 将 `backend/services/simulation.py` 拆分为抽象 backend 与 MuJoCo 实现
- 新增 `backend_registry`
- 将 API 层从直接调用仿真服务改为调用应用服务

### 优先级二：建立统一状态与展示模型

- 从 `backend/api/state.py` 中移除进程内 `_current_states`
- 新增 `StateStore`
- 新增 `SceneService`
- 让前端优先消费统一场景 DTO

### 优先级三：重写实时通信层

- 将 `backend/services/websocket_manager.py` 升级为支持订阅、心跳、独立发送队列的 `WebSocketHub`
- 将 `backend/api/agent_ws.py` 中混合的任务协议与广播协议拆开

### 优先级四：接入 ROS2 Humble + Gazebo

- 新增 `ROS2GazeboBackend`
- 建立 ROS2 状态订阅与命令下发通路
- 把 ROS2/Gazebo 数据转换成统一状态与场景模型

### 优先级五：前端展示链路适配

- 为现有 `Vue3 + Three.js` 页面增加数据源选择能力
- 适配新的 `scene_snapshot` / `scene_delta` 协议
- 在迁移期保留兼容映射层，避免一次性推翻现有前端逻辑

---

## 实施边界与非目标

### 本设计明确包含

- 双后端统一接入
- 前端统一展示协议
- 实时切换数据源
- 公共能力与扩展能力分离

### 本设计明确不包含

- 真实机器人后端的完整接入实现
- 所有 ROS2 topic/service/action 的通用浏览器
- 前端 UI 视觉重设计
- Gazebo 与 MuJoCo 物理一致性校准问题

这些能力未来可以扩展，但不应干扰本次架构主线。

---

## 结论

对当前 EmbodiedAgentsSys 来说，正确方向不是简单“加一个 ROS2 接口”，而是把系统重构为一个双后端统一展示平台：

- `MuJoCo` 负责本地轻量仿真
- `ROS2 Humble + Gazebo` 负责标准仿真和联调
- `Vue3 + Three.js` 负责统一显示机器人仿真、训练和部署效果
- 后端通过统一状态模型、统一场景模型和统一实时消息协议支撑上述三者协同工作

这套架构既保留了现有能力，也给未来扩展真实机器人、增加更多仿真后端和完善前端展示打下稳定基础。
