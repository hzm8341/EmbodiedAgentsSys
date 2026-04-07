# VLAPlus Web Scene Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个最小可用的 Web Demo，通过浏览器摄像头获取单帧图像，发送到后端调用 `VLAPlus.analyze_scene`，并在网页上展示场景描述和物体列表，用于测试当前项目的图像理解能力。

**Architecture:** 使用 FastAPI 提供一个 `/analyze` 接口接收 `multipart/form-data`（图片 + 文本问题），在后端将图片转换为 `np.ndarray` 后调用现有的 `VLAPlus` 组件；同时由 FastAPI 提供静态页面 `index.html`，该页面通过 `getUserMedia` 打开摄像头，截图成 JPEG 后调用 `/analyze` 接口，并显示返回的 JSON 结果。整体为单进程单机 demo，不依赖 ROS2。

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, NumPy, 浏览器 `getUserMedia` + 原生 HTML/JavaScript。

---

### Task 1: 添加 Web Demo 后端脚本骨架

**Files:**
- Create: `examples/vla_plus_web_demo.py`

**Step 1: 创建 FastAPI 应用与基础路由**

在 `examples/vla_plus_web_demo.py` 中：
- 导入 `FastAPI`, `UploadFile`, `File`, `Form` 和 `uvicorn`。
- 创建 `app = FastAPI()`。
- 添加简单的健康检查路由 `GET /healthz`，返回 `{"status": "ok"}`。

**Step 2: 预留 VLAPlus 初始化占位**

- 导入 `VLAPlus` 与 `VLAPlusConfig`，在模块级创建一个懒加载的 `get_vla_plus()` 函数，首次调用时初始化 `VLAPlus` 实例（默认 `device="cpu"`，方便本地快速测试），后续请求复用同一实例。

**Step 3: 手动运行测试**

运行：

```bash
PYTHONPATH=. python examples/vla_plus_web_demo.py
```

（先不真正启动 uvicorn，只验证模块可以成功导入和创建 `app` 与 `VLAPlus`，无 ImportError 或运行时异常。）

---

### Task 2: 实现 `/analyze` 接口逻辑

**Files:**
- Modify: `examples/vla_plus_web_demo.py`

**Step 1: 定义请求模型与响应模型（可选轻量化）**

- 使用 Pydantic 定义一个响应模型 `SceneAnalysisResponse`，字段包括：
  - `scene_description: str`
  - `objects: list[dict]`
  - `target_object: Optional[str]`
  - `grasp_candidates: list[dict]`

**Step 2: 实现 `POST /analyze` 接口**

- 路由签名大致如下：

```python
@app.post("/analyze", response_model=SceneAnalysisResponse)
async def analyze_scene(
    image: UploadFile = File(...),
    question: str = Form("画面里面有什么？"),
):
    ...
```

- 在实现中：
  - 读取上传的图片字节；使用 Pillow（推荐）或 OpenCV 将其解码为 `np.ndarray`，保证形状为 `(H, W, 3)` 且 `dtype=uint8`。
  - 调用 `vla = get_vla_plus()` 获取实例。
  - `result = await vla.analyze_scene(image_array, question)`。
  - 将结果打包成 `SceneAnalysisResponse` 返回。
  - 适当添加异常处理，出现错误时返回 `HTTPException(status_code=500, detail=...)`。

**Step 3: 手动测试接口（无前端）**

- 使用 `uvicorn` 启动服务，例如：

```bash
PYTHONPATH=. uvicorn examples.vla_plus_web_demo:app --reload --port 8000
```

- 用 `curl` 或 `httpie` 发送一个本地图像测试：

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "image=@tests/assets/example.jpg" \
  -F "question=画面里面有什么？"
```

- 确认返回 JSON 包含 `scene_description`、`objects` 字段且无错误。

---

### Task 3: 提供静态 HTML 前端页面

**Files:**
- Create: `examples/static/index.html`
- Modify: `examples/vla_plus_web_demo.py`（挂载静态文件和根路由）

**Step 1: 编写 `index.html` 结构**

在 `examples/static/index.html` 中：
- 包含以下元素：
  - `<video id="video" autoplay playsinline></video>`：实时显示摄像头画面。
  - `<canvas id="canvas" style="display:none;"></canvas>`：用于截图。
  - `<input id="question" type="text" value="画面里面有什么？" />`。
  - `<button id="analyze-btn">分析当前画面</button>`。
  - `<pre id="result"></pre>`：显示返回结果（或使用更美观的 `<div>`）。
- 引入一段 `<script>`，包含初始化摄像头和调用后端的逻辑。

**Step 2: 使用 `getUserMedia` 打开摄像头**

- 在 JS 中：
  - 调用 `navigator.mediaDevices.getUserMedia({ video: true })`。
  - 将返回的流赋值给 `video.srcObject`。
  - 处理权限被拒绝或错误的情况，给出提示。

**Step 3: 实现“分析当前画面”按钮逻辑**

- 在按钮点击事件中：
  - 将 `video` 当前帧画到 `canvas`，`canvas.width/height` 与视频宽高一致。
  - 调用 `canvas.toBlob()`（或 `toDataURL` 转 Blob）生成 JPEG。
  - 使用 `FormData` 构造请求：

```javascript
const formData = new FormData();
formData.append("image", blob, "frame.jpg");
formData.append("question", questionInput.value || "画面里面有什么？");
```

  - 使用 `fetch("/analyze", { method: "POST", body: formData })` 调用后端。
  - 将返回 JSON 格式化后显示在 `#result` 中，例如 `JSON.stringify(data, null, 2)`。

**Step 4: 在 FastAPI 中挂载静态文件与根路由**

- 在 `vla_plus_web_demo.py` 中：
  - 使用 `StaticFiles` 将 `examples/static` 目录挂载到 `/static`（或根路径）。
  - 提供 `GET /` 路由返回 `index.html`（通过 `FileResponse` 或 `HTMLResponse` 读取文件）。

---

### Task 4: 集成体验与文档说明

**Files:**
- Modify: `TEST_MANUAL.md` 或新增一个短小使用说明条目（可选）
- Modify: `README.md`（仅添加一行链接，可选）

**Step 1: 在测试手册中添加“Web 图像理解 Demo”章节（可选）**

- 在 `TEST_MANUAL.md` 中添加一小节，说明：
  - 如何安装 FastAPI / Uvicorn（例如通过 `pip install "fastapi[standard]"`）。
  - 如何启动 demo：

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. uvicorn examples.vla_plus_web_demo:app --reload --port 8000
```

  - 如何在浏览器访问 `http://localhost:8000` 并授权摄像头，点击按钮查看结果。

**Step 2: 验证端到端流程**

- 启动 demo 后：
  - 打开浏览器访问页面，确认摄像头画面正常显示。
  - 使用默认问题“画面里面有什么？”点击“分析当前画面”，确认后端被调用，无 500 错误。
  - 在结果区域看到非空的 `scene_description` 和 `objects` 列表（内容受当前模型/Mock 行为影响，但结构应正确）。

---

### Task 5: 依赖与环境注意事项（可根据需要执行）

**Files:**
- Modify: `pyproject.toml`（可选，不一定要把 demo 依赖写进库核心依赖）

**Step 1: 记录 Web Demo 的可选依赖**

- 出于不污染主库依赖的考虑，可以只在文档中写明需要：
  - `fastapi`
  - `uvicorn[standard]`
  - `pillow`（用于解码图片，若项目内已有其他图像依赖可复用）

**Step 2: 若你希望通过 extras 管理 demo 依赖（可选）**

- 在 `pyproject.toml` 中添加 `[project.optional-dependencies]`（例如 `"web-demo" = ["fastapi", "uvicorn[standard]", "pillow"]`），方便将来一次性安装。

