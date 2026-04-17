#!/usr/bin/env python3
"""
MuJoCo 机械臂控制服务器
同时运行：
1. MuJoCo 原生 viewer (被动模式)
2. FastAPI 后端 (接收前端命令)
3. 命令转发到 MuJoCoDriver
"""

import sys
sys.path.insert(0, "/media/hzm/Data/EmbodiedAgentsSys")

import mujoco
import mujoco.viewer
import numpy as np
import threading
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from simulation.mujoco import MuJoCoDriver

# 全局变量
_driver = None
_viewer = None
_driver_lock = threading.Lock()
_initialized = threading.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan 事件处理"""
    global _driver
    # 初始化驱动：XML 用于仿真显示，URDF 用于 IK 求解
    model_path = "/media/hzm/Data/EmbodiedAgentsSys/assets/eyoubot/eu_ca_box.urdf"
    urdf_path = "/media/hzm/Data/EmbodiedAgentsSys/assets/eyoubot/eu_ca_describtion_lbs6.urdf"
    _driver = MuJoCoDriver(urdf_path=urdf_path, model_path=model_path)
    _driver.reset_to_home()  # 应用 home 姿态
    print(f"MuJoCo 驱动已初始化: nbody={_driver._model.nbody}, njnt={_driver._model.njnt}")
    print(f"末端检测: left={_driver._left_ee_name}, right={_driver._right_ee_name}")
    _initialized.set()
    yield
    # 清理
    if _viewer is not None:
        _viewer.close()


# 创建 FastAPI app
app = FastAPI(title="MuJoCo Arm Control API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: dict):
    """处理聊天命令"""
    global _driver, _viewer

    # 等待驱动初始化
    if not _initialized.is_set():
        return {"response": "系统正在初始化，请稍后", "status": "initializing"}

    message = request.get("message", "")
    print(f"收到命令: {message}")

    result = {"response": "", "status": "unknown"}

    import re

    # 匹配中文格式: "左臂移动到 X=0.1 Y=0 Z=0.2"
    arm_match = re.search(r'(左|右)臂', message)
    coord_match = re.search(r'X\s*=\s*([-\d.]+)\s*Y\s*=\s*([-\d.]+)\s*Z\s*=\s*([-\d.]+)', message)

    if arm_match and coord_match:
        arm = "left" if arm_match.group(1) == "左" else "right"
        x, y, z = float(coord_match.group(1)), float(coord_match.group(2)), float(coord_match.group(3))

        with _driver_lock:
            receipt = _driver.move_arm_to(arm, x, y, z)

        # 同步 viewer
        if _viewer is not None:
            _viewer.sync()

        result = {
            "response": f"已将{arm}臂移动到 ({x}, {y}, {z})",
            "status": receipt.status.value,
            "tool_calls": [{
                "tool": "move_arm_to",
                "params": {"arm": arm, "x": x, "y": y, "z": z},
                "result": {
                    "status": receipt.status.value,
                    "message": receipt.result_message
                }
            }]
        }
    else:
        result = {
            "response": "无法解析命令，格式应为：左臂移动到 X=0.1 Y=0 Z=0.2",
            "status": "failed"
        }

    return result


@app.post("/api/execute")
def execute(request: dict):
    """执行动作 (由 deepseek.ts 调用)"""
    global _driver, _viewer

    if not _initialized.is_set():
        return {"status": "error", "message": "系统正在初始化"}

    action = request.get("action", "")
    params = request.get("params", {})
    print(f"执行动作: {action}, 参数: {params}")

    try:
        # 处理 move_to (移动手臂 - 默认左臂)
        if action == "move_to":
            x = params.get("x", 0.0)
            y = params.get("y", 0.0)
            z = params.get("z", 0.0)
            # move_to 在这个简化版本中映射到 move_arm_to (左臂)
            with _driver_lock:
                receipt = _driver.move_arm_to("left", x, y, z)
            if _viewer is not None:
                _viewer.sync()
            return {
                "status": receipt.status.value,
                "message": receipt.result_message,
                "data": receipt.result_data or {}
            }

        # 处理 move_arm_to (移动指定臂)
        if action == "move_arm_to":
            arm = params.get("arm", "left")
            x = params.get("x", 0.0)
            y = params.get("y", 0.0)
            z = params.get("z", 0.0)
            with _driver_lock:
                receipt = _driver.move_arm_to(arm, x, y, z)
            if _viewer is not None:
                _viewer.sync()
            return {
                "status": receipt.status.value,
                "message": receipt.result_message,
                "data": receipt.result_data or {}
            }

        # 处理 move_relative
        if action == "move_relative":
            dx = params.get("dx", 0.0)
            dy = params.get("dy", 0.0)
            dz = params.get("dz", 0.0)
            with _driver_lock:
                receipt = _driver.execute_action("move_relative", {"dx": dx, "dy": dy, "dz": dz})
            if _viewer is not None:
                _viewer.sync()
            return {
                "status": receipt.status.value,
                "message": receipt.result_message,
                "data": receipt.result_data or {}
            }

        # 处理 grasp
        if action == "grasp":
            with _driver_lock:
                receipt = _driver.execute_action("grasp", params)
            if _viewer is not None:
                _viewer.sync()
            return {
                "status": receipt.status.value,
                "message": receipt.result_message,
                "data": receipt.result_data or {}
            }

        # 处理 release
        if action == "release":
            with _driver_lock:
                receipt = _driver.execute_action("release", params)
            if _viewer is not None:
                _viewer.sync()
            return {
                "status": receipt.status.value,
                "message": receipt.result_message,
                "data": receipt.result_data or {}
            }

        return {"status": "error", "message": f"Unknown action: {action}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/scene")
def scene():
    """获取场景状态"""
    if not _initialized.is_set():
        return {"robot_position": [0, 0, 0], "object_position": [0, 0, 0]}
    return _driver.get_scene()


@app.post("/api/reset")
def reset():
    """重置环境"""
    if not _initialized.is_set():
        return {"status": "error", "message": "系统正在初始化"}
    _driver.reset()
    return {"status": "success", "message": "环境已重置"}


def run_viewer_thread():
    """运行 MuJoCo viewer 线程"""
    global _driver, _viewer

    # 等待驱动初始化
    _initialized.wait()
    time.sleep(0.5)

    print("打开 MuJoCo 查看器窗口...")

    # 配置渲染效果 - 通过 model.vis.map 设置
    _driver._model.vis.map.shadowscale = 0.8  # 阴影缩放
    _driver._model.vis.map.fogstart = 5.0       # 雾效起始距离
    _driver._model.vis.map.fogend = 20.0        # 雾效结束距离
    _driver._model.vis.map.znear = 0.01         # 近裁剪面
    _driver._model.vis.map.zfar = 50.0           # 远裁剪面

    # 设置光照
    _driver._model.vis.map.stiffness = 0.5      # 光照强度

    _viewer = mujoco.viewer.launch_passive(_driver._model, _driver._data)

    # 减小关节坐标系轴长度
    _driver._model.vis.scale.jointlength = 0.02

    # 只启用关节坐标系显示，其他全部关闭
    _viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_JOINT] = 1
    _viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_STATIC] = 1  # 必须开启，否则躯干不显示

    print("MuJoCo 查看器已启动!")
    print("提示: 按 J 键显示关节坐标系")

    while _viewer.is_running():
        with _driver_lock:
            mujoco.mj_forward(_driver._model, _driver._data)
        _viewer.sync()
        time.sleep(0.001)

    print("Viewer 已关闭")


def main():
    # 启动 viewer 线程
    viewer_thread = threading.Thread(target=run_viewer_thread, daemon=True)
    viewer_thread.start()

    # 等待 viewer 启动
    time.sleep(1)

    # 启动 FastAPI
    print("启动 API 服务器 on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
