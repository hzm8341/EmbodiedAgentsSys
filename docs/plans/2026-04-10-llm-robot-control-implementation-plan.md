:orphan:

# LLM 机器人控制 - 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建端到端系统：用户通过 Web 前端输入自然语言，DeepSeek LLM 解析并调用 tools，后端 FastAPI 控制 MuJoCo 仿真执行动作。

**Architecture:** 前端 Vue 直连 DeepSeek API（tool calling），后端 FastAPI 作为仿真执行器，复用已有的 GymnasiumEnvDriver。

**Tech Stack:** Vue 3 + Vite + TypeScript | FastAPI + Python | DeepSeek API | MuJoCo/gymnasium

---

## 前提条件

- [ ] DeepSeek API Key 已配置 (sk-985a3370aeb04666969329b5af10d9f9)
- [ ] Python 3.10+ 环境
- [ ] pnpm/node 环境
- [ ] MuJoCo 和 gymnasium 已安装

---

## Part 1: 后端服务

### Task 1: 创建 FastAPI 后端项目结构

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `backend/api/__init__.py`
- Create: `backend/api/routes.py`
- Create: `backend/services/__init__.py`
- Create: `backend/services/simulation.py`
- Create: `backend/requirements.txt`

**Step 1: 创建目录结构**

```bash
mkdir -p backend/api backend/services
touch backend/__init__.py backend/api/__init__.py backend/services/__init__.py
```

**Step 2: 创建 requirements.txt**

```txt
fastapi==0.109.0
uvicorn==0.27.0
numpy==1.26.0
gymnasium==0.29.1
panda-mujoco-gym==0.0.0
```

**Step 3: 创建 backend/main.py**

```python
"""FastAPI 后端入口 - LLM 机器人控制"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router

app = FastAPI(title="LLM Robot Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 4: 创建 backend/services/simulation.py**

```python
"""仿真环境管理服务"""
from typing import Optional
import gymnasium as gym
from simulation.mujoco import GymnasiumEnvDriver

class SimulationService:
    """单例仿真服务"""
    _instance: Optional['SimulationService'] = None
    _driver: Optional[GymnasiumEnvDriver] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, env_name: str = "FrankaPushSparse-v0"):
        """初始化仿真环境"""
        if self._driver is None:
            self._driver = GymnasiumEnvDriver(
                env_name=env_name,
                render_mode="human"
            )
            self._driver.reset()
        return self

    def execute_action(self, action: str, params: dict):
        """执行动作"""
        if self._driver is None:
            self.initialize()
        return self._driver.execute_action(action, params)

    def get_scene(self) -> dict:
        """获取场景状态"""
        if self._driver is None:
            return {"robot_position": [0, 0, 0], "object_position": [0, 0, 0]}
        return self._driver.get_scene()

    def reset(self):
        """重置环境"""
        if self._driver:
            self._driver.reset()
        return {"status": "success", "message": "Environment reset"}


# 全局实例
simulation_service = SimulationService()
```

**Step 5: 创建 backend/api/routes.py**

```python
"""API 路由"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.simulation import simulation_service

router = APIRouter()

class ExecuteRequest(BaseModel):
    action: str
    params: dict = {}

class ExecuteResponse(BaseModel):
    status: str
    message: str
    data: dict = {}

@router.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest):
    """执行动作"""
    receipt = simulation_service.execute_action(req.action, req.params)
    return ExecuteResponse(
        status=receipt.status.value,
        message=receipt.result_message,
        data=receipt.result_data or {}
    )

@router.get("/scene")
def get_scene():
    """获取场景状态"""
    return simulation_service.get_scene()

@router.post("/reset")
def reset():
    """重置环境"""
    return simulation_service.reset()
```

**Step 6: 测试后端**

```bash
cd /media/hzm/Data/EmbodiedAgentsSys
pip install -r backend/requirements.txt
python -c "from backend.main import app; print('Backend imports OK')"
```

**Step 7: 提交**

```bash
git add backend/ && git commit -m "feat(backend): add FastAPI backend structure"
```

---

### Task 2: 测试后端 API

**Files:**
- Create: `tests/integration/test_backend_api.py`

**Step 1: 编写测试**

```python
"""后端 API 测试"""
import sys
sys.path.insert(0, "/media/hzm/Data/EmbodiedAgentsSys")

def test_execute_move_to():
    from backend.services.simulation import simulation_service
    simulation_service.initialize()
    result = simulation_service.execute_action("move_to", {"x": 0.5, "y": 0, "z": 0.3})
    assert result.status.value == "success"

def test_get_scene():
    from backend.services.simulation import simulation_service
    scene = simulation_service.get_scene()
    assert "robot_position" in scene
```

**Step 2: 运行测试**

```bash
pytest tests/integration/test_backend_api.py -v
```

**Step 3: 提交**

```bash
git add tests/ && git commit -m "test(backend): add API tests"
```

---

## Part 2: 前端集成

### Task 3: 创建 DeepSeek API 服务

**Files:**
- Create: `web-dashboard/src/services/deepseek.ts`

**Step 1: 创建服务**

```typescript
/** @see https://platform.deepseek.com/docs */

const DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

export interface ToolCall {
  id: string
  type: "function"
  function: {
    name: string
    arguments: string
  }
}

export interface DeepSeekMessage {
  role: "system" | "user" | "assistant"
  content: string
  tool_calls?: ToolCall[]
  tool_call_id?: string
}

export interface ExecuteResult {
  status: string
  message: string
  data: Record<string, any>
}

// DeepSeek Tools 定义
export const ROBOT_TOOLS = [
  {
    type: "function" as const,
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
    type: "function" as const,
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
    type: "function" as const,
    function: {
      name: "grasp",
      description: "执行抓取动作",
      parameters: { type: "object", properties: {} }
    }
  },
  {
    type: "function" as const,
    function: {
      name: "release",
      description: "执行释放动作",
      parameters: { type: "object", properties: {} }
    }
  },
  {
    type: "function" as const,
    function: {
      name: "get_scene",
      description: "获取当前仿真场景状态",
      parameters: { type: "object", properties: {} }
    }
  }
]

export class DeepSeekService {
  private apiKey: string
  private model: string

  constructor(apiKey: string, model: string = "deepseek-chat") {
    this.apiKey = apiKey
    this.model = model
  }

  async chat(messages: DeepSeekMessage[]): Promise<{
    message: DeepSeekMessage
    finishReason: string
  }> {
    const response = await fetch(DEEPSEEK_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        tools: ROBOT_TOOLS,
        stream: false
      })
    })

    if (!response.ok) {
      throw new Error(`DeepSeek API error: ${response.status}`)
    }

    const data = await response.json()
    return {
      message: data.choices[0].message,
      finishReason: data.choices[0].finish_reason
    }
  }
}

// 后端 API 基础 URL
const API_BASE = "http://localhost:8000/api"

export async function executeAction(action: string, params: object = {}): Promise<ExecuteResult> {
  const response = await fetch(`${API_BASE}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, params })
  })
  return response.json()
}

export async function getScene(): Promise<{robot_position: number[], object_position: number[]}> {
  const response = await fetch(`${API_BASE}/scene`)
  return response.json()
}

export async function resetEnv(): Promise<ExecuteResult> {
  const response = await fetch(`${API_BASE}/reset`, { method: "POST" })
  return response.json()
}
```

**Step 2: 提交**

```bash
git add web-dashboard/src/services/deepseek.ts && git commit -m "feat(frontend): add DeepSeek API service with robot tools"
```

---

### Task 4: 创建机器人控制组件

**Files:**
- Create: `web-dashboard/src/components/RobotControl.vue`

**Step 1: 创建组件**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { DeepSeekService, executeAction, getScene, resetEnv, ROBOT_TOOLS, type DeepSeekMessage, type ToolCall } from '../services/deepseek'

const API_KEY = import.meta.env.VITE_DEEPSEEK_API_KEY || "sk-985a3370aeb04666969329b5af10d9f9"

const userInput = ref("")
const messages = ref<Array<{role: string, content: string}>>([])
const isLoading = ref(false)
const scene = ref({ robot_position: [0, 0, 0], object_position: [0, 0, 0] })
const deepseek = new DeepSeekService(API_KEY)

onMounted(async () => {
  await refreshScene()
})

async function refreshScene() {
  try {
    scene.value = await getScene()
  } catch (e) {
    console.error("Failed to get scene:", e)
  }
}

async function handleSubmit() {
  const userMsg = userInput.value.trim()
  if (!userMsg) return

  // 添加用户消息
  messages.value.push({ role: "user", content: userMsg })
  userInput.value = ""
  isLoading.value = true

  try {
    // 调用 DeepSeek
    const systemPrompt: DeepSeekMessage = {
      role: "system",
      content: "你是一个机器人控制助手。用户用自然语言描述命令，你需要调用适当的工具来控制机器人。机器人支持: move_to(x,y,z), move_relative(dx,dy,dz), grasp, release, get_scene。"
    }

    const allMessages: DeepSeekMessage[] = [
      systemPrompt,
      ...messages.value.map(m => ({ role: m.role as "user" | "assistant", content: m.content }))
    ]

    const response = await deepseek.chat(allMessages)
    const assistantMsg = response.message

    // 添加助手消息
    messages.value.push({ role: "assistant", content: assistantMsg.content || "" })

    // 处理工具调用
    if (assistantMsg.tool_calls) {
      for (const toolCall of assistantMsg.tool_calls) {
        const result = await executeToolCall(toolCall)
        messages.value.push({
          role: "assistant",
          content: `[${toolCall.function.name}] 结果: ${JSON.stringify(result)}`
        })
      }
      await refreshScene()
    }
  } catch (e) {
    messages.value.push({ role: "assistant", content: `错误: ${e}` })
  } finally {
    isLoading.value = false
  }
}

async function executeToolCall(toolCall: ToolCall) {
  const { name, arguments: argsStr } = toolCall.function
  const params = JSON.parse(argsStr)
  return executeAction(name, params)
}

async function handleReset() {
  await resetEnv()
  await refreshScene()
  messages.value = []
}
</script>

<template>
  <div class="robot-control p-4">
    <h2 class="text-xl font-bold mb-4">🤖 机器人控制</h2>

    <!-- 场景状态 -->
    <div class="scene-status mb-4 p-3 bg-gray-100 rounded">
      <div>机器人位置: {{ scene.robot_position?.join(', ') || 'N/A' }}</div>
      <div>物体位置: {{ scene.object_position?.join(', ') || 'N/A' }}</div>
    </div>

    <!-- 消息列表 -->
    <div class="messages h-64 overflow-y-auto border rounded p-3 mb-4">
      <div v-for="(msg, i) in messages" :key="i" class="mb-2">
        <strong>{{ msg.role === 'user' ? '👤' : '🤖' }}:</strong> {{ msg.content }}
      </div>
      <div v-if="isLoading" class="text-gray-500">思考中...</div>
    </div>

    <!-- 输入框 -->
    <div class="flex gap-2">
      <input
        v-model="userInput"
        @keyup.enter="handleSubmit"
        placeholder="输入命令，如: 将机器人移动到 x=0.5 y=0 z=0.3"
        class="flex-1 border rounded px-3 py-2"
        :disabled="isLoading"
      />
      <button
        @click="handleSubmit"
        :disabled="isLoading"
        class="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
      >
        发送
      </button>
      <button
        @click="handleReset"
        class="bg-gray-300 px-4 py-2 rounded"
      >
        重置
      </button>
    </div>

    <!-- 可用工具说明 -->
    <div class="mt-4 text-sm text-gray-600">
      <p>可用命令示例:</p>
      <ul class="list-disc list-inside">
        <li>将机器人移动到 x=0.5 y=0 z=0.3</li>
        <li>向上移动 0.1 米</li>
        <li>抓取物体</li>
        <li>释放物体</li>
      </ul>
    </div>
  </div>
</template>
```

**Step 2: 提交**

```bash
git add web-dashboard/src/components/RobotControl.vue && git commit -m "feat(frontend): add RobotControl component"
```

---

### Task 5: 集成到 App.vue

**Files:**
- Modify: `web-dashboard/src/App.vue`

**Step 1: 修改 App.vue**

在现有 App.vue 中添加 RobotControl 组件的导入和使用。具体修改取决于现有 App.vue 结构。

**Step 2: 添加环境变量**

创建 `web-dashboard/.env`:
```bash
VITE_DEEPSEEK_API_KEY=sk-985a3370aeb04666969329b5af10d9f9
```

**Step 3: 提交**

```bash
git add web-dashboard/src/App.vue web-dashboard/.env && git commit -m "feat(frontend): integrate RobotControl into App"
```

---

## Part 3: 端到端测试

### Task 6: 启动并验证系统

**Step 1: 启动后端**

```bash
cd /media/hzm/Data/EmbodiedAgentsSys
pip install -r backend/requirements.txt
python -m backend.main
# 后端应该在 http://0.0.0.0:8000 运行
```

**Step 2: 启动前端**

```bash
cd web-dashboard
pnpm install
pnpm dev
# 前端应该在 http://localhost:5173 运行
```

**Step 3: 测试完整流程**

1. 打开浏览器访问 http://localhost:5173
2. 在输入框输入: `将机器人移动到 x=0.5 y=0 z=0.3`
3. 点击发送
4. 验证:
   - DeepSeek 返回了 tool_call
   - 后端执行了 move_to 动作
   - 仿真环境发生了变化

**Step 4: 提交**

```bash
git commit -m "chore: complete E2E integration"
```

---

## 任务清单

| Task | 描述 | 状态 |
|------|------|------|
| 1 | 创建 FastAPI 后端项目结构 | ⬜ |
| 2 | 测试后端 API | ⬜ |
| 3 | 创建 DeepSeek API 服务 | ⬜ |
| 4 | 创建机器人控制组件 | ⬜ |
| 5 | 集成到 App.vue | ⬜ |
| 6 | 端到端测试 | ⬜ |

---

## 注意事项

1. **DeepSeek API Key**: 前端直接使用 API Key，仅适合开发环境
2. **CORS**: 后端已配置允许前端 Origin
3. **仿真渲染**: GymnasiumEnvDriver 使用 `render_mode="human"`，会在单独窗口渲染
4. **错误处理**: 简化版实现，生产环境需增强
