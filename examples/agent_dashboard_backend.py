import asyncio
import base64
from datetime import datetime
from fastapi import FastAPI, WebSocket
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


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    timestamp: datetime


class Settings(BaseModel):
    language: str
    theme: str
    model: str
    websocket_url: str
    api_url: str
    refresh_rate: int


MOCK_CAMERA_FRAME = base64.b64encode(b"mock_image_data").decode()
MOCK_DETECTIONS = [
    {"id": "1", "label": "cube", "confidence": 0.95, "bbox": [0.1, 0.2, 0.3, 0.4]},
    {"id": "2", "label": "cup", "confidence": 0.87, "bbox": [0.5, 0.3, 0.2, 0.3]},
]


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response_text = f"收到消息: {request.message}"
    return ChatResponse(response=response_text, timestamp=datetime.now())


@app.get("/api/camera/frame")
async def get_camera_frame():
    return {
        "frame": MOCK_CAMERA_FRAME,
        "timestamp": datetime.now(),
        "fps": 30,
    }


@app.get("/api/detection/result")
async def get_detection_result():
    return {
        "objects": MOCK_DETECTIONS,
        "timestamp": datetime.now(),
    }


@app.get("/api/settings", response_model=Settings)
async def get_settings():
    return Settings(
        language="zh",
        theme="auto",
        model="Qwen3L",
        websocket_url="ws://localhost:8000/ws",
        api_url="http://localhost:8000/api",
        refresh_rate=30,
    )


@app.put("/api/settings")
async def update_settings(settings: Settings):
    return {"status": "updated"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(0.1)
            data = {
                "type": "camera_frame",
                "frame": MOCK_CAMERA_FRAME,
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_json(data)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
