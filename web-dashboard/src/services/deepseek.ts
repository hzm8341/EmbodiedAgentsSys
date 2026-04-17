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
      name: "move_arm_to",
      description: "将机器人指定臂的末端移动到目标位置（基于基座坐标系）",
      parameters: {
        type: "object",
        properties: {
          arm: { type: "string", enum: ["left", "right"], description: "臂名称：left 或 right" },
          x: { type: "number", description: "X坐标 (米，相对于基座)" },
          y: { type: "number", description: "Y坐标 (米，相对于基座)" },
          z: { type: "number", description: "Z坐标 (米，相对于基座)" }
        },
        required: ["arm", "x", "y", "z"]
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
