import asyncio
import base64
import threading
from datetime import datetime

import cv2
import ollama
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Embodied Agents Dashboard Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# USB 摄像头后台抓帧
# ---------------------------------------------------------------------------

_latest_frame: bytes | None = None  # JPEG bytes
_camera_lock = threading.Lock()


def _camera_loop(cam_index: int = 0) -> None:
    """后台线程：持续从 USB 摄像头抓帧，存入 _latest_frame。"""
    global _latest_frame
    cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"[camera] 无法打开摄像头 index={cam_index}")
        return
    print(f"[camera] 摄像头已打开 index={cam_index}")
    while True:
        ret, frame = cap.read()
        if ret and frame is not None:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            with _camera_lock:
                _latest_frame = buf.tobytes()


def _start_camera(cam_index: int = 0) -> None:
    t = threading.Thread(target=_camera_loop, args=(cam_index,), daemon=True)
    t.start()


@app.on_event("startup")
async def startup_event() -> None:
    _start_camera(cam_index=0)


# ---------------------------------------------------------------------------
# 辅助：获取当前帧 base64
# ---------------------------------------------------------------------------

def _get_frame_b64() -> str | None:
    with _camera_lock:
        if _latest_frame is None:
            return None
        return base64.b64encode(_latest_frame).decode()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response_text = f"收到消息: {request.message}"
    return ChatResponse(response=response_text, timestamp=datetime.now())


@app.get("/api/camera/frame")
async def get_camera_frame():
    frame_b64 = _get_frame_b64()
    if frame_b64 is None:
        return {"frame": None, "timestamp": datetime.now(), "fps": 0}
    return {"frame": frame_b64, "timestamp": datetime.now(), "fps": 30}


@app.post("/api/scene/describe")
async def describe_scene():
    """
    抓取当前 USB 摄像头帧，调用 qwen2.5vl 进行场景理解。
    返回：scene_description（文字描述）和 objects（检测到的物体列表）。
    """
    with _camera_lock:
        frame_bytes = _latest_frame

    if frame_bytes is None:
        return {"error": "摄像头尚未就绪", "scene_description": "", "objects": []}

    frame_b64 = base64.b64encode(frame_bytes).decode()

    prompt = (
        "请分析这张图片，用中文回答以下两点：\n"
        "1. 场景描述：简要描述画面内容（1-2句）。\n"
        "2. 物体列表：列出画面中的主要物体，每行一个，格式为「- 物体名称（置信度估计高/中/低）」。\n"
        "请严格按照上述格式输出，不要添加其他内容。"
    )

    try:
        response = await asyncio.to_thread(
            ollama.chat,
            model="qwen2.5vl:latest",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [frame_b64],
                }
            ],
        )
        text = response["message"]["content"]
    except Exception as e:
        return {"error": str(e), "scene_description": "", "objects": []}

    # 解析文本
    scene_description = ""
    objects = []
    lines = text.splitlines()
    in_objects = False
    for line in lines:
        line = line.strip()
        if line.startswith("1.") or "场景描述" in line:
            scene_description = line.split("：", 1)[-1].strip() if "：" in line else line
            in_objects = False
        elif line.startswith("2.") or "物体列表" in line:
            in_objects = True
        elif in_objects and line.startswith("-"):
            body = line.lstrip("- ").strip()
            confidence = 0.8
            if "高" in body:
                confidence = 0.9
            elif "低" in body:
                confidence = 0.5
            label = body.split("（")[0].strip()
            objects.append({"id": str(len(objects) + 1), "label": label, "confidence": confidence})

    return {
        "scene_description": scene_description,
        "objects": objects,
        "raw": text,
        "timestamp": datetime.now(),
    }


@app.get("/api/detection/result")
async def get_detection_result():
    """从最新场景分析中返回检测结果（轻量版，直接调 describe_scene）。"""
    result = await describe_scene()
    return {
        "objects": result.get("objects", []),
        "timestamp": datetime.now(),
    }


@app.get("/api/settings")
async def get_settings():
    return {
        "language": "zh",
        "theme": "auto",
        "model": "qwen2.5vl",
        "websocket_url": "ws://localhost:8000/ws",
        "api_url": "http://localhost:8000/api",
        "refresh_rate": 10,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
