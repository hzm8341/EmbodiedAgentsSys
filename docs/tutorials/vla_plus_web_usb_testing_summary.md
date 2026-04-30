:orphan:

# VLA+ 图像理解测试总结

**版本**: v1.0  
**日期**: 2026-03-13  
**适用**: EmbodiedAgentsSys 图像理解能力测试（Web Demo + USB 相机）

本文档汇总本次会话中完成的所有改动与测试步骤，便于下次快速复现。

---

## 1. 背景与目标

- **目标**：在本地测试项目的图像理解能力——打开网页、接入相机画面，输入「画面里面有什么？」等问题，由模型返回场景描述和物体列表。
- **方案**：采用 **方案 A（FastAPI + 单页前端）**，后改为 **方案 B（后端使用 USB 相机抓帧）**，前端只发问题文本并展示结果。

---

## 2. 已实现功能概览

| 功能 | 说明 |
|------|------|
| Web 图像理解 Demo | FastAPI 后端 + 单页 HTML，调用 `VLAPlus.analyze_scene` 做场景理解 |
| 后端 USB 相机 | 使用 OpenCV `VideoCapture(0, cv2.CAP_V4L2)` 在每次请求时抓取单帧，转 RGB 后送 VLAPlus |
| GPU 推理 | VLAPlus 默认 `device="cuda"`，无 GPU 时可改为 `"cpu"` |
| 接口 | `POST /analyze` 仅接收 `question`（表单），返回 `scene_description`、`objects`、`target_object`、`grasp_candidates` |

---

## 3. 相关文件与结构

```
EmbodiedAgentsSys/
├── examples/
│   ├── vla_plus_web_demo.py    # FastAPI 应用：/healthz、/analyze、/、USB 抓帧 + VLAPlus
│   └── static/
│       └── index.html          # 前端：问题输入框 +「分析当前画面」按钮，结果 JSON 展示
├── agents/
│   ├── components/
│   │   └── vla_plus.py         # VLAPlus.analyze_scene(image, instruction)
│   └── config_vla_plus.py      # VLAPlusConfig(device="cuda")
├── scripts/
│   └── test_vla_plus_manual.py # 一键手动集成测试（不依赖 pytest）
├── tests/
│   └── conftest.py             # 已修复：worktree 不存在时回退为正常 import
└── docs/
    ├── tutorials/
    │   ├── vla_plus_manual_testing.md   # VLA+ 手动测试手册（含 Sugarcoat 安装与 pytest）
    │   └── vla_plus_web_usb_testing_summary.md  # 本文档
    └── plans/
        └── 2026-03-13-vla-plus-web-scene-viewer-plan.md  # 原始实现计划
```

---

## 4. 环境与依赖

### 4.1 Python 依赖（Web Demo）

在项目所用 Python 环境中安装：

```bash
pip install "fastapi[standard]" uvicorn pillow opencv-python
```

- `fastapi`、`uvicorn`：Web 服务  
- `pillow`：若将来恢复「上传图片」接口时可用来解码  
- `opencv-python`：USB 摄像头抓帧（`cv2.VideoCapture`）

### 4.2 可选：Sugarcoat（仅跑 pytest 或完整 ROS 流程时需要）

若需运行 VLA+ 相关 **pytest**，需先安装并激活 Sugarcoat（见 `docs/tutorials/vla_plus_manual_testing.md`）：

```bash
# 方式一：apt（Ubuntu/ROS）
sudo apt install ros-humble-automatika-ros-sugar

# 方式二：源码
mkdir -p ~/ros-sugar-ws/src && cd ~/ros-sugar-ws/src
git clone https://github.com/automatika-robotics/sugarcoat
cd ..
pip install numpy opencv-python-headless "attrs>=23.2.0" jinja2 msgpack msgpack-numpy setproctitle pyyaml toml
colcon build
source install/setup.bash
```

**每个新终端** 若跑 pytest，需先：

```bash
source /opt/ros/humble/setup.bash
# 若为源码安装 Sugarcoat：
source ~/ros-sugar-ws/install/setup.bash
```

---

## 5. 测试步骤（下次复现按此执行）

### 5.1 Web Demo（USB 相机 + 图像理解）——推荐

1. **确认 USB 相机已连接**，且在系统中为默认设备（通常为 `index=0`）。  
   若需指定其他 index，可修改 `examples/vla_plus_web_demo.py` 中 `_capture_usb_frame(cam_index=0)` 或后续扩展为环境变量/配置。

2. **启动服务**（在项目根目录）：

   ```bash
   cd /media/hzm/data_disk/EmbodiedAgentsSys
   PYTHONPATH=. uvicorn examples.vla_plus_web_demo:app --reload --port 8000
   ```

3. **浏览器访问**：  
   `http://127.0.0.1:8000`

4. **操作**：  
   - 在「问题」输入框中输入或保留默认「画面里面有什么？」  
   - 点击「分析当前画面」  
   - 后端会从 USB 相机抓取当前帧，调用 VLAPlus 分析，右侧显示 `scene_description`、`objects` 等 JSON 结果。

5. **无 GPU 时**：  
   在 `vla_plus_web_demo.py` 中将 `VLAPlusConfig(device="cuda")` 改为 `VLAPlusConfig(device="cpu")`。

### 5.2 手动集成脚本（不依赖浏览器）

在已配置好 Python 与项目依赖的环境中：

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. python3 scripts/test_vla_plus_manual.py
```

预期：输出多组 ✅/❌ 检查，最后为 VLAPlus 完整 pipeline 结果（场景描述、物体数、抓取候选等）。可用于验证 VLA+ 组件在无 Web、无 USB 时的逻辑是否正确。

### 5.3 可选：pytest 自动化测试

若已安装并激活 Sugarcoat，且需跑单元测试：

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
source /opt/ros/humble/setup.bash
source ~/ros-sugar-ws/install/setup.bash   # 若为源码安装

# 禁用全局 pytest 插件，避免与 dash/plotly 等冲突
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python3 -m pytest \
  tests/test_vla_plus_config.py \
  tests/test_data_structures.py \
  tests/test_sam3_segmenter.py \
  tests/test_qwen3l_processor.py \
  tests/test_collision_checker.py \
  tests/test_vla_plus.py \
  -v
```

**说明**：若仍出现 `❌ CRITICAL ERROR: 'automatika-ros-sugar' not found`，多为 Sugarcoat 内部/ROS 环境检查未通过，与「Python 能 import automatika_ros_sugar」并不矛盾。此时可优先用 **5.1 Web Demo** 与 **5.2 手动脚本** 验证图像理解与 pipeline 功能。

---

## 6. 已修复问题记录

| 问题 | 处理 |
|------|------|
| f-string 括号错误导致 SyntaxError | `detail=f"…（index={cam_index)})"` 中多写了一个 `)`，已改为 `（index={cam_index}）`（全角括号） |
| tests/conftest.py 从不存在 worktree 加载配置导致 FileNotFoundError | 改为：若 worktree 路径不存在则回退为 `import agents.config_vla_plus`，保证在当前仓库可跑 pytest |
| pytest 加载 dash 插件缺 plotly 报错 | 使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 禁用全局插件 |
| Sugarcoat 自检报 CRITICAL ERROR 但 Python 可 import | 属 Sugarcoat/ROS 环境层问题，不影响用 Web Demo 与手动脚本做功能验证 |

---

## 7. 常见问题速查

- **Q: 启动 uvicorn 报 “无法打开 USB 摄像头（index=0）”**  
  A: 检查相机是否被其他进程占用、是否插好、权限（如 `v4l2` 组）。多相机时可改 `cam_index` 或后续加配置项。

- **Q: 想用浏览器摄像头而不是 USB**  
  A: 需恢复旧版逻辑：前端用 `getUserMedia` + canvas 截帧上传图片，后端 `POST /analyze` 接收 `image` + `question`，用 Pillow 解码为 numpy 再调 `analyze_scene`。当前版本已移除该路径，仅保留后端 USB 抓帧。

- **Q: 如何切换 GPU/CPU**  
  A: 编辑 `examples/vla_plus_web_demo.py` 中 `get_vla_plus()` 内 `VLAPlusConfig(device="cuda")` 为 `"cpu"` 或通过环境变量扩展。

---

## 8. 参考文档

- [VLA+ 手动测试手册](vla_plus_manual_testing.md) — 配置、Sugarcoat 安装、各模块手测与 pytest 说明  
- [VLA+ Web Scene Viewer 实现计划](../plans/2026-03-13-vla-plus-web-scene-viewer-plan.md) — 原始设计与任务拆解  
- 项目 README：`/media/hzm/data_disk/EmbodiedAgentsSys/README.md`

完成以上步骤即可在下次测试时快速复现「USB 相机 → 网页按钮 → VLAPlus 场景理解」的完整流程。
