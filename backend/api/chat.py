"""聊天端点 - LLM解析 + 工具执行"""
import os
import json
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
            "description": "将机器人指定臂的末端移动到目标位置（基于基座坐标系）。这是控制机械臂的唯一方式！",
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
            "name": "get_scene",
            "description": "获取当前仿真场景状态",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

SYSTEM_PROMPT = """你是一个机器人控制助手。用户会用自然语言描述想要的动作，你需要调用相应的工具来执行。

重要：用户提到"左臂"或"右臂"时，必须使用 move_arm_to 工具！

支持的工具：
- move_arm_to(arm, x, y, z): 移动指定臂的末端到目标位置（这是控制机械臂的唯一方式！）
  - arm: "left" 或 "right"（必须指定！）
  - x, y, z: 目标位置（米，相对于基座坐标系，z 轴向上）
- move_relative(dx, dy, dz): 相对移动
- grasp(): 抓取
- release(): 释放
- get_scene(): 获取场景状态

机器人工作空间（重要！）：
- 基座原点在地面（z=0），坐标轴已在 MuJoCo 场景中标出（红=X前, 绿=Y左, 蓝=Z上）
- 左臂默认末端位置约 [0, +0.21, 0.80]（左侧，高度 0.80 m）
- 右臂默认末端位置约 [0, -0.21, 0.80]（右侧，高度 0.80 m）
- 可到达范围大约：x ∈ [-0.3, 0.5]，y ∈ [-0.5, 0.5]，z ∈ [0.75, 1.4]
- 工作台在 z=0.68，桌面物体在 z≈0.72；机械臂无法低于约 z=0.80
- 如果目标超出范围，系统会返回失败信息，请告知用户并建议合理范围内的目标

注意：
- 位置单位是米
- 当用户说"移动左臂"或"移动右臂"时，必须调用 move_arm_to
- move_arm_to 是控制机械臂的唯一正确方式
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
        "move_to": "move_to",
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


async def call_deepseek(messages: list[dict], api_key: Optional[str]) -> dict:
    """调用DeepSeek API"""
    # 优先使用请求头中的API Key，其次使用环境变量
    key = api_key or DEEPSEEK_API_KEY
    if not key:
        raise HTTPException(status_code=500, detail="DeepSeek API Key not configured")

    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
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
    """处理自然语言聊天请求（两阶段：工具调用 + LLM结果摘要）"""
    api_key = x_api_key or DEEPSEEK_API_KEY

    # ── 第一阶段：让 LLM 决定调用哪些工具 ──────────────────────────
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(req.history)
    messages.append({"role": "user", "content": req.message})

    result = await call_deepseek(messages, api_key)
    assistant_msg = result["choices"][0]["message"]

    response_text: str = assistant_msg.get("content") or ""
    raw_tool_calls: list = assistant_msg.get("tool_calls") or []
    tool_results: list[ToolCallResult] = []

    # ── 工具执行 ─────────────────────────────────────────────────────
    for tc in raw_tool_calls:
        func = tc["function"]
        tool_name = func["name"]
        try:
            params = json.loads(func["arguments"])
        except Exception:
            params = {}

        exec_result = execute_robot_tool(tool_name, params)
        tool_results.append(ToolCallResult(tool=tool_name, params=params, result=exec_result))

    # ── 第二阶段：将工具结果交还 LLM，生成自然语言回复 ───────────────
    if raw_tool_calls and tool_results:
        messages.append(assistant_msg)  # assistant's tool-call turn
        for i, (tc, tr) in enumerate(zip(raw_tool_calls, tool_results)):
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", f"call_{i}"),
                "content": json.dumps(tr.result, ensure_ascii=False),
            })

        result2 = await call_deepseek(messages, api_key)
        response_text = result2["choices"][0]["message"].get("content") or ""

    if not response_text:
        response_text = f"已执行 {len(tool_results)} 个工具调用"

    scene_state = simulation_service.get_scene()
    return ChatResponse(
        response=response_text,
        tool_calls=tool_results,
        scene_state=scene_state,
    )
