:orphan:

# Async API + WebSocket 实时通信增强设计

日期: 2026-04-24 | 方案: B (仿真专用事件循环 + Pub/Sub 状态流)

## 1. 总体架构

```
                        ┌── Uvicorn 主事件循环 ──────────────────────────┐
                        │                                                │
前端 (React)             │  /api/execute    ──▶ SimBridge ──▶ queue ──┐  │
  │                      │  /api/chat       ──▶ DeepSeek LLM          │  │
  │                      │  /api/agent/ws   ◀── AgentStreamManager     │  │
  ├─ /robot/state/ws ────│──▶ StateBroadcaster ◀─ robot_state ◀─────┐ │  │
  ├─ /robot/command/ws ──│──▶ CommandBridge  ──▶ command_queue ────┐│ │  │
  │                      │                                         ││ │  │
  └─ 自动重连 + 心跳      │                                         ││ │  │
                        └──────────────────────────────────────────││─│──┘
                                                                    ││ │
                        ┌── 仿真线程 (独立 asyncio loop) ───────────┘│ │
                        │                                            │ │
                        │  SimController                             │ │
                        │  ├─ MuJoCoDriver (step/ik/reset)          │ │
                        │  ├─ StatePublisher (每 16ms 推送状态快照)  │ │
                        │  └─ CommandWorker (消费命令队列)           │ │
                        │                                            │
                        └── MuJoCo viewer 线程 ───────────────────────┘
```

- 仿真跑在独立线程的专属 asyncio.AbstractEventLoop 里
- 主循环与仿真线程通过 asyncio.Queue 通信
- 状态推送改为事件驱动：仿真每 step 后主动发布

## 2. 核心组件

### 2.1 SimController — 仿真线程管理器

在独立线程中运行专属 asyncio 事件循环。核心循环：
1. 消费命令队列（非阻塞）
2. 推进 MuJoCo 仿真
3. 发布状态到状态队列（maxsize=2，自动淘汰旧状态）

命令提交通过 `asyncio.Queue` + `concurrent.futures.Future` 跨线程返回结果。

### 2.2 SimBridge — 主循环代理

主 API 循环中使用的仿真代理。REST/WS 端点通过 SimBridge 间接操作仿真：
- `execute_action()` → `asyncio.run_coroutine_threadsafe()` → SimController
- `get_state()` → 返回最新状态快照

### 2.3 StateBroadcaster — 状态广播器

消费 SimController 状态流，广播到所有 `/api/robot/state/ws` 客户端。
- 默认 JSON 编码，支持 `?binary=1` 启用 MessagePack
- 运行在 uvicorn 主循环中的后台 asyncio.Task

### 2.4 WebSocket 端点

| 端点 | 方向 | 用途 |
|------|------|------|
| `/api/robot/state/ws` | 服务器→客户端 | 高频状态流（关节角度、传感器） |
| `/api/robot/command/ws` | 双向 | 指令下发 + 结果回传 |
| `/api/agent/ws` | 双向 | 任务遥测（保持现有） |

心跳机制：服务端每 15s 发送 heartbeat，客户端 30s 超时重连。

## 3. 数据流

### 指令流 (前端 → 仿真)
```
WS /robot/command/ws → SimBridge → future → command_queue → SimController → MuJoCoDriver
```

### 状态流 (仿真 → 前端)
```
SimController._run() → state_queue → StateBroadcaster → JSON/MessagePack → WS 客户端
```

### 任务遥测流 (AgentBridge → 前端)
保持现有流程，AgentBridge 内部改为通过 SimBridge 执行仿真指令。

## 4. 生命周期

- startup: SimController.start() → viewer → StateBroadcaster.start()
- shutdown: StateBroadcaster.stop() → SimController.stop() → viewer.close() → thread.join()

## 5. 错误处理

- 仿真异常：推 error 到所有客户端 → event loop 安全退出
- 命令队列积压 >100：返回 REJECTED
- future 超时 5s：返回 timeout error
- 状态队列满：丢弃旧值，不阻塞

## 6. 改动清单

| 文件 | 操作 |
|------|------|
| `backend/services/sim_controller.py` | 新建 |
| `backend/services/sim_bridge.py` | 新建 |
| `backend/services/state_broadcaster.py` | 新建 |
| `backend/api/robot_ws.py` | 新建 |
| `backend/main.py` | 修改 |
| `backend/services/agent_bridge.py` | 修改 |
| `backend/api/chat.py` | 修改 |
| `frontend/src/hooks/useRobotWebSocket.ts` | 新建 |
| `frontend/src/hooks/useAgentWebSocket.ts` | 修改 |
| `backend/requirements.txt` | 修改 |

5 个新文件，6 个修改文件，0 个删除。
