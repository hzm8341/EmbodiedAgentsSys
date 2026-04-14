"""聊天端点 - LLM解析 + 工具执行"""
import os
import httpx
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from fastapi import Header

from backend.services.simulation import simulation_service

router = APIRouter()

# DeepSeek API配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
MODEL = "deepseek-chat"

# 机器人工具定义（与前端 deepseek.ts 保持一致）
ROBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "move_arm_to",
            "description": "将机器人指定臂的末端移动到目标位置（基于基座坐标系）",
            "parameters": {
                "type": "object",
                "properties": {
                    "arm": {
                        "type": "string",
                        "enum": ["left", "right"],
                        "description": "臂名称：left 或 right"
                    },
                    "x": {"type": "number", "description": "X坐标 (米，相对于基座)"},
                    "y": {"type": "number", "description": "Y坐标 (米，相对于基座)"},
                    "z": {"type": "number", "description": "Z坐标 (米，相对于基座)"},
                },
                "required": ["arm", "x", "y", "z"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_relative",
            "description": "相对当前位置移动机器人末端",
            "parameters": {
                "type": "object",
                "properties": {
                    "dx": {"type": "number", "description": "X方向位移 (米)"},
                    "dy": {"type": "number", "description": "Y方向位移 (米)"},
                    "dz": {"type": "number", "description": "Z方向位移 (米)"},
                },
                "required": ["dx", "dy", "dz"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grasp",
            "description": "执行抓取动作",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "release",
            "description": "执行释放动作",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scene",
            "description": "获取当前仿真场景状态",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

SYSTEM_PROMPT = """你是一个机器人控制助手。用户会用自然语言描述想要的动作，你需要调用相应的工具来执行。

支持的工具：
- move_arm_to(arm, x, y, z): 移动指定臂的末端到目标位置
  - arm: "left" 或 "right"
  - x, y, z: 目标位置（米，相对于基座坐标系）
- move_relative(dx, dy, dz): 相对移动
- grasp(): 抓取
- release(): 释放
- get_scene(): 获取场景状态

注意：
- 位置单位是米
- 使用 move_arm_to 控制机械臂移动
- 如果用户没有指定具体数值，先调用get_scene了解当前状态
- 保持回复简洁"""

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class ToolCallResult(BaseModel):
    tool: str
    params: dict
    result: dict

class ChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallResult] = []
    scene_state: Optional[dict] = None


def execute_robot_tool(tool_name: str, params: dict) -> dict:
    """执行机器人工具并返回结果"""
    action_map = {
        "move_arm_to": "move_arm_to",
        "move_relative": "move_relative",
        "grasp": "grasp",
        "release": "release",
        "get_scene": "get_scene",
    }

    action = action_map.get(tool_name)
    if not action:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}

    try:
        if action == "get_scene":
            result = simulation_service.get_scene()
            return {"status": "success", "data": result}

        receipt = simulation_service.execute_action(action, params)
        return {
            "status": receipt.status.value,
            "message": receipt.result_message,
            "data": receipt.result_data or {},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def call_deepseek(messages: list[dict], api_key: str) -> dict:
    """调用DeepSeek API"""
    # 优先使用请求头中的API Key，其次使用环境变量
    key = api_key or DEEPSEEK_API_KEY
    if not key:
        raise HTTPException(status_code=500, detail="DeepSeek API Key not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            DEEPSEEK_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "tools": ROBOT_TOOLS,
                "stream": False,
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"DeepSeek API error: {response.text}",
            )

        return response.json()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_api_key: Optional[str] = Header(None)):
    """处理自然语言聊天请求"""
    # 构建消息历史
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.message})

    # 调用DeepSeek（优先使用请求头中的API Key）
    result = await call_deepseek(messages, x_api_key)
    assistant_message = result["choices"][0]["message"]

    response_text = assistant_message.get("content", "")
    tool_calls = assistant_message.get("tool_calls", [])
    tool_results = []

    # 执行工具调用
    for tool_call in tool_calls:
        func = tool_call["function"]
        tool_name = func["name"]
        params = eval(func["arguments"])  # 安全：只执行预定义的工具

        exec_result = execute_robot_tool(tool_name, params)
        tool_results.append(
            ToolCallResult(tool=tool_name, params=params, result=exec_result)
        )

    # 获取场景状态
    scene_state = simulation_service.get_scene()

    return ChatResponse(
        response=response_text or f"已执行 {len(tool_results)} 个工具调用",
        tool_calls=tool_results,
        scene_state=scene_state,
    )
