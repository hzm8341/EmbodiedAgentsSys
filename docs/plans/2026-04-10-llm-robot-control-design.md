# LLM 机器人控制 - 设计文档

**日期**: 2026-04-10
**状态**: 设计中

---

## 1. 目标

构建一个端到端的系统：用户通过 Web 前端输入自然语言命令（如 "将机器人移动到 x=10 y=0 z=20"），由 LLM（DeepSeek）解析意图并调用预设的工具（skills），最终在 MuJoCo 仿真环境中执行相应动作。

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Frontend (Vue)                      │
│  - 用户输入自然语言命令                                       │
│  - 调用 DeepSeek API (with tools)                           │
│  - 解析 tool_call 调用后端                                   │
│  - 显示执行结果/仿真画面                                      │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                                                              │
│  /api/execute          POST   执行动作 (move_to/grasp/...)  │
│  /api/scene            GET    获取当前场景状态               │
│  /api/reset            POST   重置仿真环境                   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              GymnasiumEnvDriver                       │   │
│  │  (复用 simulation/mujoco/gymnasium_env_driver.py)    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   MuJoCo Simulation                          │
│              (Gymnasium Env: FrankaPushSparse-v0)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 技术选型

| 组件 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite + TypeScript + TailwindCSS |
| 后端框架 | FastAPI (Python) |
| LLM | DeepSeek API (deepseek-chat model) |
| 仿真环境 | MuJoCo via gymnasium (FrankaPushSparse-v0) |
| 通信方式 | HTTP REST |

---

## 4. 前端设计

### 4.1 工具定义 (DeepSeek Tools)

```typescript
const tools = [
  {
    type: "function",
    function: {
      name: "move_to",
      description: "将机器人末端移动到指定的三维位置",
      parameters: {
        type: "object",
        properties: {
          x: { type: "number", description: "X坐标 (米)" },
          y: { type: "number", description: "Y坐标 (米)" },
          z: { type: "number", description: "Z坐标 (米)" }
        },
        required: ["x", "y", "z"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "move_relative",
      description: "相对当前位置移动机器人末端",
      parameters: {
        type: "object",
        properties: {
          dx: { type: "number", description: "X方向位移 (米)" },
          dy: { type: "number", description: "Y方向位移 (米)" },
          dz: { type: "number", description: "Z方向位移 (米)" }
        },
        required: ["dx", "dy", "dz"]
      }
    }
  },
  {
    type: "function",
    function: {
      name: "grasp",
      description: "执行抓取动作",
      parameters: {
        type: "object",
        properties: {}
      }
    }
  },
  {
    type: "function",
    function: {
      name: "release",
      description: "执行释放动作",
      parameters: {
        type: "object",
        properties: {}
      }
    }
  },
  {
    type: "function",
    function: {
      name: "get_scene",
      description: "获取当前仿真场景状态",
      parameters: {
        type: "object",
        properties: {}
      }
    }
  }
]
```

### 4.2 前端交互流程

1. 用户在输入框输入自然语言命令
2. 前端调用 `deepseek-chat` API，传入 `tools` 参数
3. DeepSeek 返回 `tool_call`（包含函数名和参数）
4. 前端解析 `tool_call`，调用后端 `/api/execute` 接口
5. 后端执行仿真动作，返回结果
6. 前端显示执行结果，更新场景状态

### 4.3 消息示例

**用户输入**: `将机器人移动到 x=0.5 y=0 z=0.3`

**DeepSeek 响应**:
```json
{
  "tool_calls": [{
    "id": "call_xxx",
    "type": "function",
    "function": {
      "name": "move_to",
      "arguments": "{\"x\": 0.5, \"y\": 0, \"z\": 0.3}"
    }
  }]
}
```

---

## 5. 后端 API 设计

### 5.1 FastAPI 接口

```python
# /api/execute - 执行动作
POST /api/execute
Request: {
    "action": "move_to",  # | "move_relative" | "grasp" | "release"
    "params": {"x": 0.5, "y": 0, "z": 0.3}  # 动作参数
}
Response: {
    "status": "success",  # | "failed"
    "message": "Moved to (0.5, 0, 0.3)",
    "data": {"position": [0.5, 0, 0.3]}
}

# /api/scene - 获取场景
GET /api/scene
Response: {
    "robot_position": [0.5, 0, 0.3],
    "object_position": [0.6, 0.1, 0.2]
}

# /api/reset - 重置环境
POST /api/reset
Response: {"status": "success", "message": "Environment reset"}
```

### 5.2 错误处理

- 动作执行失败返回 `status: "failed"` 并附带错误信息
- 后端捕获异常返回 500 错误
- 前端显示错误提示

---

## 6. 文件结构

```
/media/hzm/Data/EmbodiedAgentsSys
├── web-dashboard/                    # 前端 (已有)
│   ├── src/
│   │   ├── components/
│   │   │   └── RobotControl.vue     # 新增: 机器人控制组件
│   │   ├── services/
│   │   │   └── deepseek.ts          # 新增: DeepSeek API 调用
│   │   └── App.vue                  # 修改: 集成控制组件
│   └── ...
│
├── backend/                          # 新增: FastAPI 后端
│   ├── main.py                       # FastAPI 入口
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                 # API 路由
│   ├── services/
│   │   ├── __init__.py
│   │   └── simulation.py             # 仿真环境管理
│   └── requirements.txt
│
├── simulation/                       # 已有 (复用)
│   └── mujoco/
│       └── gymnasium_env_driver.py   # GymnasiumEnvDriver
│
└── docs/plans/                       # 本文档
```

---

## 7. 实现步骤

1. **后端服务** (backend/)
   - 创建 FastAPI 项目结构
   - 实现 `/api/execute`, `/api/scene`, `/api/reset` 接口
   - 集成 `GymnasiumEnvDriver`
   - 测试仿真控制

2. **前端集成** (web-dashboard/)
   - 创建 `deepseek.ts` 服务
   - 定义 tools 工具描述
   - 创建 `RobotControl.vue` 组件
   - 集成到 App.vue

3. **端到端测试**
   - 启动后端服务
   - 启动前端开发服务器
   - 发送自然语言命令验证

---

## 8. 关键设计决策

1. **前端直连 DeepSeek**：利用 DeepSeek 原生 tool calling，减少后端复杂度
2. **后端仅执行仿真**：后端不做 LLM 调用，只负责执行动作
3. **复用已有模块**：`GymnasiumEnvDriver` 直接复用，不重复造轮子
4. **简化渲染**：使用 gymnasium 内置 `render_mode="human"`

---

## 9. 安全考虑

- API Key 存储在前端环境变量（开发环境）
- 生产环境应通过后端代理 DeepSeek API
- 仿真动作有安全边界检查（复用 GymnasiumEnvDriver 已有检查）

---

## 10. 后续扩展

- 添加 WebSocket 支持实时状态推送
- 添加仿真画面截图/视频功能
- 支持更多动作类型（关节控制、轨迹规划）
