# 交互式代理调试器 (Agent Debugger)

基于 WebSocket 的前后端系统，用于实时观察具身智能代理的四层架构（Planning → Reasoning → Execution → Learning）推理过程。

## 架构

```
┌────────────────────┐         WebSocket         ┌──────────────────────┐
│ React Frontend     │ ◀────────────────────────▶│ FastAPI Backend      │
│ (Vite, port 5173)  │    /api/agent/ws          │ (port 8000)          │
│                    │                            │                      │
│ - TaskPanel        │    /api/agent/scenarios    │ - AgentBridge        │
│ - ExecutionMonitor │                            │ - AgentStreamManager │
│ - ObservationPanel │                            │ - Cognition Layers   │
│ - ResultPanel      │                            │ - 5 Scenarios        │
└────────────────────┘                            └──────────────────────┘
```

## 启动

### 1. 后端

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

打开浏览器测试：
- Health check: http://localhost:8000/health
- Scenarios list: http://localhost:8000/api/agent/scenarios

### 2. 前端

```bash
cd frontend
npm install   # 首次启动时执行
npm run dev
```

前端访问：http://localhost:5173

Vite 已配置代理：`/api/*` 请求（含 WebSocket）自动转发到后端 8000 端口。

## 使用流程

1. 访问前端页面，确认右上角 `● Connected` 徽章为绿色
2. 在左侧 **Task Input** 面板：
   - 直接在文本框输入任务，或
   - 点击 5 个预设场景之一：
     - `spatial_detection` — 空间检测
     - `single_grasp` — 单一抓取
     - `grasp_and_move` — 抓取 + 移动
     - `error_recovery` — 错误恢复
     - `dynamic_environment` — 动态环境
3. 点击 **Execute**
4. 右侧 **Execution Monitor** 实时显示四层的推理输出：
   - Planning Layer（任务计划）
   - Reasoning Layer（推理选择动作）
   - Execution（动作执行反馈）
   - Learning Layer（改进建议）
5. **Result Panel** 显示最终任务成功/失败，可展开完整日志

## 消息协议

### 前端 → 后端
```json
{
  "type": "execute_task",
  "task": "pick up the red cube",
  "observation": {
    "state": {"gripper_open": 1.0},
    "gripper": {"position": 0.04}
  },
  "max_steps": 3
}
```

### 后端 → 前端 (按序广播)
```json
{"type": "task_start",  "timestamp": 1713340000.0, "data": {"task": "..."}}
{"type": "planning",    "timestamp": 1713340000.1, "data": {"plan": {...}}}
{"type": "reasoning",   "timestamp": 1713340000.2, "data": {"step": 0, "action": "..."}}
{"type": "execution",   "timestamp": 1713340000.3, "data": {"step": 0, "feedback": {...}}}
{"type": "learning",    "timestamp": 1713340000.4, "data": {"step": 0, "improved_action": "..."}}
{"type": "result",      "timestamp": 1713340000.9, "data": {"task_success": true, "steps_executed": 3}}
```

错误消息：
```json
{"type": "error", "data": {"message": "invalid request: ..."}}
```

## 测试

```bash
# 后端单元测试（38 个）
pytest tests/backend/ -v

# 端到端集成测试（9 个，覆盖 5 场景 + WebSocket 交互）
pytest tests/integration/test_agent_debugger_e2e.py -v

# 前端 TypeScript 类型检查 + 构建
cd frontend && npm run build
```

## 代码结构

### 后端（新增）
- `backend/services/agent_bridge.py` — AgentBridge：包装 planning/reasoning/learning 三层，运行多步循环并广播遥测
- `backend/services/scenarios.py` — 5 个预设场景及注册表
- `backend/api/agent_ws.py` — WebSocket 端点 `/api/agent/ws` + REST `/api/agent/scenarios`
- `backend/services/websocket_manager.py` — 新增 `AgentStreamManager` 类（广播式 WebSocket 管理器）

### 后端（复用现有）
- `backend/main.py` — FastAPI 主应用（仅追加 `agent_ws.router` 注册）
- `backend/services/simulation.py` — 现有仿真服务（eyoubot MuJoCo）

### 前端（全新）
- `frontend/src/App.tsx` — 主组件，双列布局
- `frontend/src/hooks/useAgentWebSocket.ts` — WebSocket 连接管理
- `frontend/src/components/` — TaskPanel / ExecutionMonitor / ObservationPanel / ResultPanel
- `frontend/src/types.ts` — 共享 TypeScript 类型

## 扩展方向

- **切换机器人**：当前使用 eyoubot URDF；更换 Franka 只需修改 `backend/api/ik.py` 的 `ROBOT_CONFIGS`
- **接入真实仿真**：在 `AgentBridge` 的执行步骤中调用 `simulation_service.execute_action()`（当前使用 mock feedback）
- **自定义场景**：在 `backend/services/scenarios.py` 的 `SCENARIOS` 字典新增条目
- **自定义层**：`AgentBridge` 构造器接受依赖注入（planning/reasoning/learning），可换成自定义实现
- **3D 可视化**：前端可接入 Three.js 显示机器人实时状态

## 约束 & 注意事项

- `backend/requirements.txt` 固定 `httpx<0.28`（新版移除 TestClient 所需的 `app=` 参数）
- FastAPI TestClient WebSocket 测试在 `tests/integration/` 和 `tests/backend/test_agent_ws.py`
- 现有 `WebSocketManager`（robot state 通道）与 `AgentStreamManager`（agent 遥测通道）独立运行，互不影响
