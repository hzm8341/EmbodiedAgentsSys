import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.components.vla_plus import VLAPlus
from agents.config_vla_plus import VLAPlusConfig


app = FastAPI(title="VLAPlus Web Scene Viewer")


class SceneAnalysisResponse(BaseModel):
    scene_description: str
    objects: List[Dict[str, Any]]
    target_object: Optional[str] = None
    grasp_candidates: List[Dict[str, Any]]


_vla_plus_instance: Optional[VLAPlus] = None


def get_vla_plus() -> VLAPlus:
    """Lazily initialize and return a shared VLAPlus instance."""
    global _vla_plus_instance
    if _vla_plus_instance is None:
        # 默认使用 GPU（cuda），用于真实模型测试；如无 GPU 可改为 "cpu"
        config = VLAPlusConfig(device="cuda")
        _vla_plus_instance = VLAPlus(config=config)
    return _vla_plus_instance


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


def _capture_usb_frame(cam_index: int = 0) -> np.ndarray:
    """
    从本地 USB 摄像头抓取单帧图像（BGR 格式）。

    为了简化 demo，这里每次 /analyze 调用时临时打开摄像头、读取一帧后立即释放。
    如需高性能实时流，可以改为长期持有 VideoCapture 并在后台循环抓帧。
    """
    cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise HTTPException(
            status_code=500,
            detail=f"无法打开 USB 摄像头（index={cam_index}）",
        )
    try:
        ret, frame = cap.read()
        if not ret or frame is None:
            raise HTTPException(status_code=500, detail="从 USB 摄像头读取帧失败")
        return frame
    finally:
        cap.release()


@app.post("/analyze", response_model=SceneAnalysisResponse)
async def analyze_scene(
    question: str = Form("画面里面有什么？"),
) -> SceneAnalysisResponse:
    """
    使用本机 USB 摄像头采集当前帧并调用 VLAPlus 进行场景理解。
    """
    # Step 1: 从 USB 摄像头抓取当前帧（BGR）
    bgr = _capture_usb_frame(cam_index=0)

    # Step 2: 转为 RGB numpy 数组 (H, W, 3), uint8
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # Step 3: 调用 VLAPlus 进行场景理解
    vla = get_vla_plus()

    # VLAPlus.analyze_scene 是异步方法，这里确保在事件循环中调用
    result = await vla.analyze_scene(rgb, question)

    return SceneAnalysisResponse(
        scene_description=result.get("scene_description", ""),
        objects=result.get("objects", []),
        target_object=result.get("target_object"),
        grasp_candidates=result.get("grasp_candidates", []),
    )


static_dir = Path(__file__).parent / "static"
if static_dir.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(static_dir)),
        name="static",
    )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """
    Serve the demo HTML page.
    """
    index_path = static_dir / "index.html"
    if not index_path.is_file():
        # 简单提示，避免 404
        return HTMLResponse(
            "<h1>VLAPlus Web Scene Viewer</h1><p>index.html not found in /examples/static.</p>",
            status_code=200,
        )
    return FileResponse(str(index_path))


if __name__ == "__main__":
    import uvicorn

    # 直接运行该脚本即可启动 demo:
    # PYTHONPATH=. python examples/vla_plus_web_demo.py
    uvicorn.run("examples.vla_plus_web_demo:app", host="0.0.0.0", port=8000, reload=True)

