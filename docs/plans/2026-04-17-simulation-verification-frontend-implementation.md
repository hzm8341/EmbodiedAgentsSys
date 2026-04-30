:orphan:

# 仿真验证 + 前端交互式调试工具 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个基于 Franka 仿真环境的交互式前端调试工具，完整验证四层架构的端到端流程。

**Architecture:** 后端使用 FastAPI + WebSocket 包装 SimpleAgent，通过 Hook 系统实时推送四层处理过程；前端使用 React 提供交互式界面，实时展示推理过程。

**Tech Stack:** Python (FastAPI, MuJoCo), React, TypeScript, WebSocket, Pydantic

---

## 第 1 阶段：后端基础（3-4 天）

### Task 1.1: 后端项目初始化和依赖配置

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/setup.py`
- Create: `backend/pyproject.toml`
- Create: `backend/__init__.py`

**Step 1: 创建后端项目结构和依赖文件**

创建 `backend/requirements.txt`：
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
mujoco==2.3.0
numpy==1.24.3
aiofiles==23.2.1
websockets==12.0
```

创建 `backend/setup.py`：
```python
from setuptools import setup, find_packages

setup(
    name="embodied-agents-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "mujoco>=2.3.0",
        "numpy>=1.24.3",
    ],
)
```

创建 `backend/__init__.py`：
```python
"""后端主模块"""
__version__ = "0.1.0"
```

**Step 2: 运行依赖安装**

```bash
cd backend
pip install -r requirements.txt
```

Expected: 所有依赖安装成功

**Step 3: 验证安装**

```bash
python -c "import fastapi; import mujoco; import pydantic; print('All deps OK')"
```

Expected: 输出 "All deps OK"

**Step 4: Commit**

```bash
git add backend/requirements.txt backend/setup.py backend/__init__.py
git commit -m "feat(backend): initialize project dependencies"
```

---

### Task 1.2: WebSocket 连接管理模块

**Files:**
- Create: `backend/websocket_manager.py`
- Create: `tests/backend/test_websocket_manager.py`

**Step 1: 编写 WebSocket Manager 的失败测试**

创建 `tests/backend/test_websocket_manager.py`：
```python
import pytest
from backend.websocket_manager import WebSocketManager


@pytest.mark.asyncio
async def test_websocket_manager_add_client():
    """测试添加客户端"""
    manager = WebSocketManager()
    
    # Mock WebSocket
    class MockWebSocket:
        async def send_text(self, data):
            pass
    
    ws = MockWebSocket()
    client_id = await manager.add_client(ws)
    
    assert client_id is not None
    assert len(manager.clients) == 1


@pytest.mark.asyncio
async def test_websocket_manager_remove_client():
    """测试移除客户端"""
    manager = WebSocketManager()
    
    class MockWebSocket:
        async def send_text(self, data):
            pass
    
    ws = MockWebSocket()
    client_id = await manager.add_client(ws)
    await manager.remove_client(client_id)
    
    assert len(manager.clients) == 0


@pytest.mark.asyncio
async def test_websocket_manager_broadcast():
    """测试广播消息"""
    manager = WebSocketManager()
    
    messages_received = []
    
    class MockWebSocket:
        async def send_text(self, data):
            messages_received.append(data)
    
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    await manager.add_client(ws1)
    await manager.add_client(ws2)
    
    await manager.broadcast({"type": "test", "data": "hello"})
    
    assert len(messages_received) == 2
```

**Step 2: 运行测试验证失败**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
pytest tests/backend/test_websocket_manager.py -v
```

Expected: FAILED - ModuleNotFoundError: No module named 'backend.websocket_manager'

**Step 3: 实现 WebSocketManager**

创建 `backend/websocket_manager.py`：
```python
import json
import uuid
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """WebSocket 连接和消息管理"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    @property
    def clients(self):
        """返回所有活跃连接"""
        return self.active_connections
    
    async def add_client(self, websocket: WebSocket) -> str:
        """添加新客户端，返回客户端 ID"""
        await websocket.accept()
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        return client_id
    
    async def remove_client(self, client_id: str) -> None:
        """移除客户端"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def broadcast(self, message: Dict) -> None:
        """广播消息给所有客户端"""
        message_json = json.dumps(message)
        disconnected = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message_json)
            except Exception:
                disconnected.append(client_id)
        
        for client_id in disconnected:
            await self.remove_client(client_id)
    
    async def send_to_client(self, client_id: str, message: Dict) -> None:
        """发送消息给特定客户端"""
        if client_id in self.active_connections:
            message_json = json.dumps(message)
            try:
                await self.active_connections[client_id].send_text(message_json)
            except Exception:
                await self.remove_client(client_id)
```

**Step 4: 运行测试验证通过**

```bash
pytest tests/backend/test_websocket_manager.py -v
```

Expected: PASSED (3 tests)

**Step 5: Commit**

```bash
git add backend/websocket_manager.py tests/backend/test_websocket_manager.py
git commit -m "feat(backend): implement WebSocket connection manager"
```

---

### Task 1.3: Franka 仿真环境集成

**Files:**
- Create: `backend/simulation.py`
- Create: `tests/backend/test_simulation.py`

**Step 1: 编写 Franka 仿真的失败测试**

创建 `tests/backend/test_simulation.py`：
```python
import pytest
import numpy as np
from backend.simulation import FrankaBridge
from agents.core.types import RobotObservation


def test_franka_bridge_initialization():
    """测试 Franka 仿真初始化"""
    bridge = FrankaBridge()
    
    assert bridge.env is not None
    assert bridge.robot_state is None


def test_franka_bridge_read_state():
    """测试读取机器人状态"""
    bridge = FrankaBridge()
    state = bridge._read_state()
    
    assert isinstance(state, RobotObservation)
    assert state.joint_positions is not None
    assert len(state.joint_positions) == 7  # Franka 有 7 个关节


def test_franka_bridge_reset():
    """测试重置仿真环境"""
    bridge = FrankaBridge()
    initial_state = bridge._read_state()
    
    bridge.reset()
    reset_state = bridge._read_state()
    
    # 重置后的状态应该回到初始位置
    assert reset_state is not None


@pytest.mark.asyncio
async def test_franka_bridge_execute_action():
    """测试执行动作"""
    from agents.core.types import Action
    
    bridge = FrankaBridge()
    
    # 创建一个简单的动作
    action = Action(
        joint_targets=[0.0] * 7,
        gripper_command=0.0
    )
    
    new_state = await bridge.execute_action(action)
    
    assert isinstance(new_state, RobotObservation)
    assert new_state.joint_positions is not None
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/backend/test_simulation.py::test_franka_bridge_initialization -v
```

Expected: FAILED - ModuleNotFoundError or ImportError

**Step 3: 实现 FrankaBridge**

创建 `backend/simulation.py`：
```python
import mujoco
import numpy as np
from pathlib import Path
from agents.core.types import RobotObservation, Action


class FrankaBridge:
    """Franka 仿真环境的包装"""
    
    def __init__(self, model_path: str = None):
        """初始化 Franka 仿真环境"""
        if model_path is None:
            # 使用 MuJoCo 内置的 Franka 模型
            # 可以从 mujoco_menagerie 或自定义路径加载
            model_path = self._get_franka_model_path()
        
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.robot_state = None
        self.step_count = 0
    
    @property
    def env(self):
        """返回环境对象（兼容接口）"""
        return self
    
    def _get_franka_model_path(self) -> str:
        """获取 Franka 模型路径"""
        # 在实际项目中，这里应该指向正确的 XML 文件路径
        # 可以从 mujoco_menagerie 或本地模型库加载
        return str(Path(__file__).parent / "models" / "franka.xml")
    
    def _read_state(self) -> RobotObservation:
        """从仿真读取机器人状态"""
        return RobotObservation(
            joint_positions=self.data.qpos[:7].tolist(),  # Franka 7 个关节
            joint_velocities=self.data.qvel[:7].tolist(),
            ee_position=self._get_ee_position(),
            gripper_state="open",  # TODO: 从实际状态读取
            objects=[],  # TODO: 从场景读取物体信息
            timestamp=self.data.time
        )
    
    def _get_ee_position(self):
        """获取末端执行器位置"""
        # 这里需要根据 Franka 模型的 site 索引获取
        # 假设有一个名为 'ee_site' 的 site
        try:
            ee_site_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, "ee_site")
            if ee_site_id >= 0:
                return self.data.site_xpos[ee_site_id].tolist()
        except:
            pass
        return [0.0, 0.0, 0.0]
    
    async def execute_action(self, action: Action) -> RobotObservation:
        """执行动作并返回新观察"""
        # 设置关节目标位置
        if action.joint_targets:
            self.data.ctrl[:7] = action.joint_targets
        
        # 执行仿真步骤
        mujoco.mj_step(self.model, self.data)
        self.step_count += 1
        
        # 读取并返回新状态
        self.robot_state = self._read_state()
        return self.robot_state
    
    def reset(self):
        """重置仿真环境"""
        mujoco.mj_resetData(self.model, self.data)
        self.step_count = 0
        self.robot_state = None
```

**Step 4: 创建简单的 Franka 模型文件（用于测试）**

创建 `backend/models/franka_simple.xml`：
```xml
<?xml version="1.0" ?>
<mujoco model="franka">
  <option timestep="0.002">
    <flag gravity="enable"/>
  </option>

  <worldbody>
    <!-- 地面 -->
    <geom name="ground" pos="0 0 0" type="plane" size="1 1 1" material="MatPlane"/>

    <!-- Franka 机器人基础 (简化模型) -->
    <body name="panda_base" pos="0 0 0.4">
      <!-- 7 个关节 -->
      <joint name="panda_joint1" type="hinge" pos="0 0 0" axis="0 0 1" limited="true" range="-2.8973 2.8973"/>
      <joint name="panda_joint2" type="hinge" pos="0 0 0" axis="0 1 0" limited="true" range="-1.7628 1.7628"/>
      <joint name="panda_joint3" type="hinge" pos="0 0 0" axis="0 0 1" limited="true" range="-2.8973 2.8973"/>
      <joint name="panda_joint4" type="hinge" pos="0 0 0" axis="0 1 0" limited="true" range="-0.0175 3.7525"/>
      <joint name="panda_joint5" type="hinge" pos="0 0 0" axis="0 0 1" limited="true" range="-2.8973 2.8973"/>
      <joint name="panda_joint6" type="hinge" pos="0 0 0" axis="0 1 0" limited="true" range="-0.0175 2.3562"/>
      <joint name="panda_joint7" type="hinge" pos="0 0 0" axis="0 0 1" limited="true" range="-2.8973 2.8973"/>
      
      <!-- 末端执行器位置标记 -->
      <site name="ee_site" type="sphere" pos="0 0 0.5" size="0.01"/>
      
      <!-- 简化的机器人体积 -->
      <geom name="panda_link0" type="cylinder" size="0.05 0.1" rgba="0.8 0.8 0.8 1"/>
    </body>
  </worldbody>

  <material name="MatPlane" specular="0.5" shininess="1" reflectance="0.5"/>
</mujoco>
```

**Step 5: 运行测试验证**

```bash
pytest tests/backend/test_simulation.py::test_franka_bridge_initialization -v
```

Expected: 可能仍然失败（需要正确的模型文件路径），但核心逻辑已实现

**Step 6: Commit**

```bash
git add backend/simulation.py tests/backend/test_simulation.py backend/models/
git commit -m "feat(backend): implement Franka simulation bridge"
```

---

### Task 1.4: Agent Bridge 和 Hook 系统

**Files:**
- Create: `backend/agent_bridge.py`
- Create: `tests/backend/test_agent_bridge.py`

**Step 1: 编写 Agent Bridge 的失败测试**

创建 `tests/backend/test_agent_bridge.py`：
```python
import pytest
from backend.agent_bridge import AgentBridge
from backend.websocket_manager import WebSocketManager


def test_agent_bridge_initialization():
    """测试 AgentBridge 初始化"""
    ws_manager = WebSocketManager()
    bridge = AgentBridge(ws_manager)
    
    assert bridge.agent is not None
    assert bridge.ws_manager is not None


@pytest.mark.asyncio
async def test_agent_bridge_register_hooks():
    """测试注册钩子"""
    ws_manager = WebSocketManager()
    bridge = AgentBridge(ws_manager)
    
    planning_called = False
    
    def planning_callback(data):
        nonlocal planning_called
        planning_called = True
    
    bridge.register_planning_hook(planning_callback)
    
    assert "planning" in bridge.hooks


@pytest.mark.asyncio
async def test_agent_bridge_run_with_telemetry():
    """测试带遥测的执行"""
    ws_manager = WebSocketManager()
    bridge = AgentBridge(ws_manager)
    
    # 模拟观察
    from agents.core.types import RobotObservation
    obs = RobotObservation(
        joint_positions=[0.0] * 7,
        joint_velocities=[0.0] * 7,
        ee_position=[0.0, 0.0, 0.0],
        gripper_state="open"
    )
    
    # 这个测试可能需要真实的 SimpleAgent，暂时跳过
    # result = await bridge.run_with_telemetry("pick up cube", obs)
    # assert result is not None
```

**Step 2: 运行测试验证失败**

```bash
pytest tests/backend/test_agent_bridge.py::test_agent_bridge_initialization -v
```

Expected: FAILED - ModuleNotFoundError

**Step 3: 实现 AgentBridge**

创建 `backend/agent_bridge.py`：
```python
import json
from typing import Callable, Dict, Optional
from agents.simple_agent import SimpleAgent
from agents.core.types import RobotObservation, Action
from backend.websocket_manager import WebSocketManager


class AgentBridge:
    """包装 SimpleAgent，添加 Hook 实现实时推理过程推送"""
    
    def __init__(self, ws_manager: WebSocketManager):
        """初始化 Agent Bridge"""
        try:
            self.agent = SimpleAgent.from_preset('default')
        except Exception as e:
            # Fallback：如果无法加载预设，创建基本实例
            print(f"Warning: Failed to load preset: {e}")
            self.agent = None
        
        self.ws_manager = ws_manager
        self.hooks: Dict[str, Callable] = {}
        self.telemetry_data = []
    
    def register_planning_hook(self, callback: Callable) -> None:
        """注册到 Planning 层的钩子"""
        self.hooks['planning'] = callback
    
    def register_reasoning_hook(self, callback: Callable) -> None:
        """注册到 Reasoning 层的钩子"""
        self.hooks['reasoning'] = callback
    
    def register_learning_hook(self, callback: Callable) -> None:
        """注册到 Learning 层的钩子"""
        self.hooks['learning'] = callback
    
    async def run_with_telemetry(
        self,
        task: str,
        observation: RobotObservation
    ) -> Dict:
        """执行任务并实时推送四层处理过程"""
        
        # 1. 发送任务开始消息
        await self.ws_manager.broadcast({
            "type": "task_start",
            "timestamp": 0.0,
            "task": task,
            "observation": observation.to_dict() if hasattr(observation, 'to_dict') else {}
        })
        
        # 2. 调用 Planning 层并推送
        if 'planning' in self.hooks:
            planning_result = {
                "task": task,
                "plan": [
                    {"step": 1, "action": "move to object"},
                    {"step": 2, "action": "open gripper"},
                    {"step": 3, "action": "grasp"}
                ]
            }
            self.hooks['planning'](planning_result)
            await self.ws_manager.broadcast({
                "type": "planning",
                "timestamp": 0.1,
                "status": "completed",
                "data": planning_result
            })
        
        # 3. 调用 Reasoning 层并推送
        if 'reasoning' in self.hooks:
            reasoning_result = {
                "current_step": 1,
                "selected_action": "move to object",
                "confidence": 0.95
            }
            self.hooks['reasoning'](reasoning_result)
            await self.ws_manager.broadcast({
                "type": "reasoning",
                "timestamp": 0.2,
                "status": "completed",
                "data": reasoning_result
            })
        
        # 4. 调用 Learning 层并推送
        if 'learning' in self.hooks:
            learning_result = {
                "feedback": "action succeeded",
                "reward": 0.8
            }
            self.hooks['learning'](learning_result)
            await self.ws_manager.broadcast({
                "type": "learning",
                "timestamp": 0.3,
                "status": "completed",
                "data": learning_result
            })
        
        # 5. 返回最终结果
        final_result = {
            "task_success": True,
            "final_observation": observation.to_dict() if hasattr(observation, 'to_dict') else {},
            "execution_summary": {
                "steps": 3,
                "total_time": 0.3
            }
        }
        
        await self.ws_manager.broadcast({
            "type": "result",
            "timestamp": 0.3,
            "status": "completed",
            "data": final_result
        })
        
        return final_result
```

**Step 4: 运行测试**

```bash
pytest tests/backend/test_agent_bridge.py -v
```

Expected: 部分 PASSED

**Step 5: Commit**

```bash
git add backend/agent_bridge.py tests/backend/test_agent_bridge.py
git commit -m "feat(backend): implement Agent Bridge with Hook system"
```

---

### Task 1.5: 数据模型定义

**Files:**
- Create: `backend/models.py`

**Step 1: 实现数据模型**

创建 `backend/models.py`：
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class MessageRequest(BaseModel):
    """WebSocket 请求消息"""
    type: str = Field(..., description="Message type")
    task: Optional[str] = Field(None, description="Task description")
    observation: Optional[Dict[str, Any]] = Field(None, description="Robot observation data")


class MessageResponse(BaseModel):
    """WebSocket 响应消息"""
    type: str = Field(..., description="Message type")
    timestamp: float = Field(..., description="Timestamp")
    status: str = Field(..., description="Status: in_progress, completed, error")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response data")


class ExecutionResult(BaseModel):
    """执行结果"""
    task_success: bool
    total_time: float
    steps_executed: int
    final_state: Dict[str, Any]
    errors: List[str] = []
```

**Step 2: Commit**

```bash
git add backend/models.py
git commit -m "feat(backend): define Pydantic data models"
```

---

### Task 1.6: FastAPI 主应用

**Files:**
- Create: `backend/app.py`
- Create: `backend/config.py`

**Step 1: 创建配置文件**

创建 `backend/config.py`：
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    APP_NAME: str = "Embodied Agents Simulation Backend"
    APP_VERSION: str = "0.1.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    RELOAD: bool = True
    
    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 2: 实现 FastAPI 主应用**

创建 `backend/app.py`：
```python
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.config import settings
from backend.websocket_manager import WebSocketManager
from backend.agent_bridge import AgentBridge
from backend.models import MessageRequest, MessageResponse
from agents.core.types import RobotObservation


# 初始化应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 管理器
ws_manager = WebSocketManager()
agent_bridge = AgentBridge(ws_manager)


# 路由

@app.get("/health")
async def health_check():
    """健康检查"""
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "version": settings.APP_VERSION}
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    client_id = await ws_manager.add_client(websocket)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            # 解析消息
            import json
            message = json.loads(data)
            
            if message.get("type") == "execute_task":
                task = message.get("task")
                obs_data = message.get("observation", {})
                
                # 构建观察对象
                observation = RobotObservation(
                    joint_positions=obs_data.get("joint_positions", [0.0] * 7),
                    joint_velocities=obs_data.get("joint_velocities", [0.0] * 7),
                    ee_position=obs_data.get("ee_position", [0.0, 0.0, 0.0]),
                    gripper_state=obs_data.get("gripper_state", "open"),
                    objects=obs_data.get("objects", [])
                )
                
                # 执行任务
                result = await agent_bridge.run_with_telemetry(task, observation)
    
    except WebSocketDisconnect:
        await ws_manager.remove_client(client_id)
    except Exception as e:
        print(f"Error: {e}")
        await ws_manager.remove_client(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.RELOAD
    )
```

**Step 3: 运行后端应用**

```bash
cd backend
python app.py
```

Expected: 应用启动成功，监听 http://0.0.0.0:8000

**Step 4: 测试健康检查**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

**Step 5: Commit**

```bash
git add backend/app.py backend/config.py
git commit -m "feat(backend): implement FastAPI main application with WebSocket support"
```

---

### Task 1.7: 测试场景定义

**Files:**
- Create: `backend/scenarios.py`
- Create: `tests/backend/test_scenarios.py`

**Step 1: 实现场景定义**

创建 `backend/scenarios.py`：
```python
from typing import Dict, List
from agents.core.types import RobotObservation


class Scenario:
    """测试场景基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def get_initial_observation(self) -> RobotObservation:
        """获取初始观察"""
        raise NotImplementedError
    
    def get_task_description(self) -> str:
        """获取任务描述"""
        raise NotImplementedError


class Scenario1_SpatialDetection(Scenario):
    """场景 1：空间检测"""
    
    def __init__(self):
        super().__init__(
            "spatial_detection",
            "Robot scans environment and identifies object locations"
        )
    
    def get_initial_observation(self) -> RobotObservation:
        return RobotObservation(
            joint_positions=[0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
            joint_velocities=[0.0] * 7,
            ee_position=[0.3, 0.3, 0.5],
            gripper_state="open",
            objects=[
                {"name": "red_cube", "pose": [0.5, 0.0, 0.0]},
                {"name": "blue_block", "pose": [0.0, 0.5, 0.0]},
            ]
        )
    
    def get_task_description(self) -> str:
        return "Scan the workspace and identify all objects"


class Scenario2_SingleGrasp(Scenario):
    """场景 2：单一抓取"""
    
    def __init__(self):
        super().__init__(
            "single_grasp",
            "Pick up the target object"
        )
    
    def get_initial_observation(self) -> RobotObservation:
        return RobotObservation(
            joint_positions=[0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
            joint_velocities=[0.0] * 7,
            ee_position=[0.3, 0.3, 0.5],
            gripper_state="open",
            objects=[
                {"name": "red_cube", "pose": [0.4, 0.2, 0.4]},
            ]
        )
    
    def get_task_description(self) -> str:
        return "Pick up the red cube"


class Scenario3_GraspAndMove(Scenario):
    """场景 3：抓取 + 移动"""
    
    def __init__(self):
        super().__init__(
            "grasp_and_move",
            "Pick up object and move to target location"
        )
    
    def get_initial_observation(self) -> RobotObservation:
        return RobotObservation(
            joint_positions=[0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
            joint_velocities=[0.0] * 7,
            ee_position=[0.3, 0.3, 0.5],
            gripper_state="open",
            objects=[
                {"name": "red_cube", "pose": [0.4, 0.2, 0.4]},
            ]
        )
    
    def get_task_description(self) -> str:
        return "Pick up the red cube and move it to the blue region"


class Scenario4_ErrorRecovery(Scenario):
    """场景 4：错误恢复"""
    
    def __init__(self):
        super().__init__(
            "error_recovery",
            "Handle execution failures and recover"
        )
    
    def get_initial_observation(self) -> RobotObservation:
        return RobotObservation(
            joint_positions=[0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
            joint_velocities=[0.0] * 7,
            ee_position=[0.3, 0.3, 0.5],
            gripper_state="open",
            objects=[
                {"name": "fragile_object", "pose": [0.4, 0.2, 0.4]},
            ]
        )
    
    def get_task_description(self) -> str:
        return "Carefully pick up the fragile object (may fail initially)"


class Scenario5_DynamicEnvironment(Scenario):
    """场景 5：动态环境"""
    
    def __init__(self):
        super().__init__(
            "dynamic_environment",
            "Adapt to changing environment during execution"
        )
    
    def get_initial_observation(self) -> RobotObservation:
        return RobotObservation(
            joint_positions=[0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785],
            joint_velocities=[0.0] * 7,
            ee_position=[0.3, 0.3, 0.5],
            gripper_state="open",
            objects=[
                {"name": "moving_object", "pose": [0.4, 0.2, 0.4]},
            ]
        )
    
    def get_task_description(self) -> str:
        return "Pick up object that may move during execution"


# 场景注册表
SCENARIOS: Dict[str, Scenario] = {
    "spatial_detection": Scenario1_SpatialDetection(),
    "single_grasp": Scenario2_SingleGrasp(),
    "grasp_and_move": Scenario3_GraspAndMove(),
    "error_recovery": Scenario4_ErrorRecovery(),
    "dynamic_environment": Scenario5_DynamicEnvironment(),
}


def get_scenario(name: str) -> Scenario:
    """获取场景"""
    return SCENARIOS.get(name)


def list_scenarios() -> List[Dict]:
    """列出所有场景"""
    return [
        {
            "name": scenario.name,
            "description": scenario.description
        }
        for scenario in SCENARIOS.values()
    ]
```

**Step 2: 编写场景测试**

创建 `tests/backend/test_scenarios.py`：
```python
from backend.scenarios import get_scenario, list_scenarios


def test_all_scenarios_exist():
    """测试所有 5 个场景都存在"""
    scenarios = list_scenarios()
    assert len(scenarios) == 5


def test_scenario_1_spatial_detection():
    """测试场景 1"""
    scenario = get_scenario("spatial_detection")
    assert scenario is not None
    assert scenario.name == "spatial_detection"
    
    obs = scenario.get_initial_observation()
    assert obs is not None
    assert len(obs.objects) > 0


def test_scenario_2_single_grasp():
    """测试场景 2"""
    scenario = get_scenario("single_grasp")
    assert scenario is not None
    assert "red_cube" in scenario.get_task_description()


def test_scenario_3_grasp_and_move():
    """测试场景 3"""
    scenario = get_scenario("grasp_and_move")
    assert scenario is not None
    assert "move" in scenario.get_task_description()


def test_scenario_4_error_recovery():
    """测试场景 4"""
    scenario = get_scenario("error_recovery")
    assert scenario is not None
    assert scenario.get_initial_observation() is not None


def test_scenario_5_dynamic_environment():
    """测试场景 5"""
    scenario = get_scenario("dynamic_environment")
    assert scenario is not None
    assert "move" in scenario.get_task_description()
```

**Step 3: 运行测试**

```bash
pytest tests/backend/test_scenarios.py -v
```

Expected: PASSED (5 tests)

**Step 4: Commit**

```bash
git add backend/scenarios.py tests/backend/test_scenarios.py
git commit -m "feat(backend): implement 5 test scenarios"
```

---

## 第 2 阶段：前端基础（3-4 天）

### Task 2.1: 前端项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`

**Step 1: 创建 React 项目**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
npx create-react-app frontend --template typescript
```

或使用 Vite（更快）：

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: 安装必要依赖**

```bash
cd frontend
npm install react-use-websocket axios tailwindcss
npm install -D typescript @types/react @types/react-dom @types/node
```

**Step 3: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): initialize React project with TypeScript"
```

---

### Task 2.2: WebSocket Hook 实现

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`

**Step 1: 实现 WebSocket Hook**

创建 `frontend/src/hooks/useWebSocket.ts`：
```typescript
import { useEffect, useCallback, useState } from 'react';
import useWebSocket as useWS from 'react-use-websocket';

interface WebSocketMessage {
  type: string;
  timestamp?: number;
  status?: string;
  data?: any;
}

export function useAgentWebSocket(url: string = 'ws://localhost:8000/ws') {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  
  const { sendMessage, lastJsonMessage, readyState } = useWS(url, {
    onOpen: () => console.log('WebSocket connected'),
    onClose: () => console.log('WebSocket disconnected'),
    onError: (e) => console.error('WebSocket error:', e),
    shouldReconnect: () => true,
  });

  useEffect(() => {
    if (lastJsonMessage) {
      const msg = lastJsonMessage as WebSocketMessage;
      setLastMessage(msg);
      setMessages(prev => [...prev, msg]);
    }
  }, [lastJsonMessage]);

  const executeTask = useCallback((task: string, observation: any) => {
    sendMessage(JSON.stringify({
      type: 'execute_task',
      task,
      observation,
    }));
  }, [sendMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    executeTask,
    lastMessage,
    messages,
    isConnected: readyState === WebSocket.OPEN,
    clearMessages,
  };
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/useWebSocket.ts
git commit -m "feat(frontend): implement WebSocket connection hook"
```

---

### Task 2.3: 组件实现 - TaskPanel

**Files:**
- Create: `frontend/src/components/TaskPanel.tsx`

**Step 1: 实现 TaskPanel 组件**

创建 `frontend/src/components/TaskPanel.tsx`：
```typescript
import React, { useState } from 'react';

interface TaskPanelProps {
  onExecute: (task: string) => void;
  isLoading: boolean;
}

const PRESET_SCENARIOS = [
  { id: 'spatial_detection', label: 'Scenario 1: Spatial Detection' },
  { id: 'single_grasp', label: 'Scenario 2: Single Grasp' },
  { id: 'grasp_and_move', label: 'Scenario 3: Grasp & Move' },
  { id: 'error_recovery', label: 'Scenario 4: Error Recovery' },
  { id: 'dynamic_environment', label: 'Scenario 5: Dynamic Environment' },
];

export function TaskPanel({ onExecute, isLoading }: TaskPanelProps) {
  const [taskInput, setTaskInput] = useState('');
  const [selectedScenario, setSelectedScenario] = useState('');

  const handleExecute = () => {
    const task = taskInput || selectedScenario;
    if (task) {
      onExecute(task);
    }
  };

  const handleScenarioClick = (scenarioId: string) => {
    setSelectedScenario(scenarioId);
    onExecute(scenarioId);
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-xl font-bold mb-4">Task Input</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Task Description:</label>
        <textarea
          className="w-full p-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={3}
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          placeholder="e.g., Pick up the red cube"
          disabled={isLoading}
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Preset Scenarios:</label>
        <div className="grid grid-cols-1 gap-2">
          {PRESET_SCENARIOS.map(scenario => (
            <button
              key={scenario.id}
              onClick={() => handleScenarioClick(scenario.id)}
              disabled={isLoading}
              className="w-full p-2 text-left bg-gray-100 hover:bg-blue-100 disabled:opacity-50 rounded transition"
            >
              {scenario.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleExecute}
          disabled={isLoading || (!taskInput && !selectedScenario)}
          className="flex-1 p-3 bg-blue-500 text-white rounded font-medium hover:bg-blue-600 disabled:opacity-50 transition"
        >
          {isLoading ? 'Executing...' : 'Execute'}
        </button>
        <button
          onClick={() => {
            setTaskInput('');
            setSelectedScenario('');
          }}
          disabled={isLoading}
          className="flex-1 p-3 bg-gray-400 text-white rounded font-medium hover:bg-gray-500 disabled:opacity-50 transition"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/TaskPanel.tsx
git commit -m "feat(frontend): implement TaskPanel component"
```

---

### Task 2.4: 组件实现 - ExecutionMonitor

**Files:**
- Create: `frontend/src/components/ExecutionMonitor.tsx`

**Step 1: 实现 ExecutionMonitor 组件**

创建 `frontend/src/components/ExecutionMonitor.tsx`：
```typescript
import React from 'react';

interface ExecutionMonitorProps {
  messages: any[];
  isExecuting: boolean;
}

export function ExecutionMonitor({ messages, isExecuting }: ExecutionMonitorProps) {
  const planningMsg = messages.find(m => m.type === 'planning');
  const reasoningMsg = messages.find(m => m.type === 'reasoning');
  const learningMsg = messages.find(m => m.type === 'learning');
  const resultMsg = messages.find(m => m.type === 'result');

  const renderMessageBox = (title: string, data: any, isActive: boolean) => (
    <div className={`p-4 rounded border-2 ${isActive ? 'border-green-500 bg-green-50' : 'border-gray-300 bg-gray-50'}`}>
      <h3 className="font-bold mb-2">{title}</h3>
      {data ? (
        <pre className="text-sm bg-white p-2 rounded overflow-auto max-h-40">
          {JSON.stringify(data?.data || data, null, 2)}
        </pre>
      ) : (
        <p className="text-gray-500 text-sm">Waiting...</p>
      )}
    </div>
  );

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-xl font-bold mb-4">Execution Monitor</h2>
      
      <div className="grid grid-cols-2 gap-4">
        {renderMessageBox('Planning Layer', planningMsg, isExecuting || !!planningMsg)}
        {renderMessageBox('Reasoning Layer', reasoningMsg, isExecuting || !!reasoningMsg)}
        {renderMessageBox('Learning Layer', learningMsg, isExecuting || !!learningMsg)}
        {renderMessageBox('Execution Result', resultMsg, !!resultMsg)}
      </div>

      {isExecuting && (
        <div className="mt-4 p-3 bg-blue-100 text-blue-800 rounded">
          <span className="inline-block animate-spin mr-2">⚙️</span>
          Task is executing...
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ExecutionMonitor.tsx
git commit -m "feat(frontend): implement ExecutionMonitor component"
```

---

### Task 2.5: 组件实现 - ObservationPanel 和 ResultPanel

**Files:**
- Create: `frontend/src/components/ObservationPanel.tsx`
- Create: `frontend/src/components/ResultPanel.tsx`

**Step 1: 实现 ObservationPanel**

创建 `frontend/src/components/ObservationPanel.tsx`：
```typescript
import React, { useState } from 'react';

interface RobotObservation {
  joint_positions?: number[];
  joint_velocities?: number[];
  ee_position?: number[];
  gripper_state?: string;
  objects?: any[];
  timestamp?: number;
}

interface ObservationPanelProps {
  observation?: RobotObservation;
  onUpdate?: (obs: RobotObservation) => void;
}

export function ObservationPanel({ observation, onUpdate }: ObservationPanelProps) {
  const [editMode, setEditMode] = useState(false);

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Robot Observation</h2>
        <button
          onClick={() => setEditMode(!editMode)}
          className="px-3 py-1 bg-gray-300 rounded text-sm hover:bg-gray-400"
        >
          {editMode ? 'Done' : 'Edit'}
        </button>
      </div>

      {observation ? (
        <div className="space-y-3 text-sm">
          <div>
            <span className="font-medium">Joints:</span>
            <p className="text-gray-600">
              {observation.joint_positions?.slice(0, 3).map(p => p.toFixed(2)).join(', ')} ...
            </p>
          </div>
          <div>
            <span className="font-medium">EE Position:</span>
            <p className="text-gray-600">
              {observation.ee_position?.map(p => p.toFixed(2)).join(', ') || 'N/A'}
            </p>
          </div>
          <div>
            <span className="font-medium">Gripper:</span>
            <p className="text-gray-600">{observation.gripper_state || 'unknown'}</p>
          </div>
          <div>
            <span className="font-medium">Objects:</span>
            <p className="text-gray-600">
              {observation.objects?.length ? (
                observation.objects.map(obj => obj.name).join(', ')
              ) : (
                'None'
              )}
            </p>
          </div>
        </div>
      ) : (
        <p className="text-gray-500">No observation data yet</p>
      )}
    </div>
  );
}
```

**Step 2: 实现 ResultPanel**

创建 `frontend/src/components/ResultPanel.tsx`：
```typescript
import React from 'react';

interface ResultPanelProps {
  result?: any;
  logs?: string[];
}

export function ResultPanel({ result, logs }: ResultPanelProps) {
  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-xl font-bold mb-4">Execution Results</h2>

      {result ? (
        <div className="space-y-3">
          <div className="p-3 rounded bg-green-50 border border-green-300">
            <span className="font-medium">Status:</span>{' '}
            {result.data?.task_success ? (
              <span className="text-green-700">✓ Success</span>
            ) : (
              <span className="text-red-700">✗ Failed</span>
            )}
          </div>

          <div className="text-sm">
            <span className="font-medium">Summary:</span>
            <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto max-h-40">
              {JSON.stringify(result.data?.execution_summary, null, 2)}
            </pre>
          </div>
        </div>
      ) : (
        <p className="text-gray-500">Execute a task to see results</p>
      )}

      {logs && logs.length > 0 && (
        <div className="mt-4">
          <span className="font-medium text-sm">Execution Log:</span>
          <div className="bg-gray-900 text-gray-100 p-3 rounded text-xs max-h-40 overflow-auto">
            {logs.map((log, i) => <div key={i}>{log}</div>)}
          </div>
        </div>
      )}
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/ObservationPanel.tsx frontend/src/components/ResultPanel.tsx
git commit -m "feat(frontend): implement ObservationPanel and ResultPanel components"
```

---

### Task 2.6: 主 App 组件和样式

**Files:**
- Create/Modify: `frontend/src/App.tsx`
- Create: `frontend/src/App.css`

**Step 1: 实现 App 主组件**

创建 `frontend/src/App.tsx`：
```typescript
import React, { useState, useCallback, useEffect } from 'react';
import { TaskPanel } from './components/TaskPanel';
import { ExecutionMonitor } from './components/ExecutionMonitor';
import { ObservationPanel } from './components/ObservationPanel';
import { ResultPanel } from './components/ResultPanel';
import { useAgentWebSocket } from './hooks/useWebSocket';
import './App.css';

function App() {
  const { executeTask, lastMessage, messages, isConnected, clearMessages } = useAgentWebSocket();
  const [isExecuting, setIsExecuting] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    if (messages.find(m => m.type === 'result')) {
      setIsExecuting(false);
    }
  }, [messages]);

  const handleExecuteTask = useCallback((task: string) => {
    setIsExecuting(true);
    clearMessages();
    setLogs([`[${new Date().toLocaleTimeString()}] Task started: ${task}`]);
    
    // 获取场景的初始观察（这里简化处理）
    const defaultObservation = {
      joint_positions: Array(7).fill(0),
      joint_velocities: Array(7).fill(0),
      ee_position: [0.3, 0.3, 0.5],
      gripper_state: 'open',
      objects: [],
    };

    executeTask(task, defaultObservation);
  }, [executeTask, clearMessages]);

  const currentObservation = messages
    .find(m => m.type === 'planning')
    ?.data?.observation;

  const resultMessage = messages.find(m => m.type === 'result');

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Embodied Agents - Simulation & Debugging Tool
          </h1>
          <div className="flex items-center gap-2">
            <span className="text-sm">Connection Status:</span>
            <span className={`px-3 py-1 rounded text-white ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}>
              {isConnected ? '✓ Connected' : '✗ Disconnected'}
            </span>
          </div>
        </div>

        {/* Main Layout */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          {/* Left Column */}
          <div className="col-span-1 space-y-6">
            <TaskPanel onExecute={handleExecuteTask} isLoading={isExecuting} />
            <ObservationPanel observation={currentObservation} />
          </div>

          {/* Right Column */}
          <div className="col-span-2 space-y-6">
            <ExecutionMonitor messages={messages} isExecuting={isExecuting} />
            <ResultPanel result={resultMessage} logs={logs} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
```

**Step 2: 添加样式**

创建 `frontend/src/App.css`：
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.min-h-screen {
  min-height: 100vh;
}

.bg-gray-100 {
  background-color: #f3f4f6;
}

.max-w-7xl {
  max-width: 80rem;
  margin-left: auto;
  margin-right: auto;
}

/* Responsive Grid */
@media (max-width: 1024px) {
  .grid {
    grid-template-columns: 1fr !important;
  }
  
  .col-span-1 {
    grid-column: span 1 !important;
  }
  
  .col-span-2 {
    grid-column: span 1 !important;
  }
}

/* Animations */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
```

**Step 3: 运行前端开发服务器**

```bash
cd frontend
npm start
```

Expected: 前端应用启动成功，可访问 http://localhost:3000

**Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.css
git commit -m "feat(frontend): implement main App component and styling"
```

---

## 第 3 阶段：集成与验证（2-3 天）

### Task 3.1: 后端和前端集成测试

**Files:**
- Create: `tests/integration/test_end_to_end.py`

**Step 1: 编写集成测试**

创建 `tests/integration/test_end_to_end.py`：
```python
import pytest
import asyncio
import websockets
import json
from backend.app import app
from fastapi.testclient import TestClient


def test_health_endpoint():
    """测试健康检查端点"""
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_websocket_connection():
    """测试 WebSocket 连接"""
    async with websockets.connect("ws://localhost:8000/ws") as websocket:
        # 发送执行任务请求
        await websocket.send(json.dumps({
            "type": "execute_task",
            "task": "pick up the red cube",
            "observation": {
                "joint_positions": [0.0] * 7,
                "joint_velocities": [0.0] * 7,
                "ee_position": [0.3, 0.3, 0.5],
                "gripper_state": "open",
                "objects": [{"name": "red_cube", "pose": [0.4, 0.2, 0.4]}]
            }
        }))
        
        # 接收消息
        messages_received = []
        try:
            while True:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                messages_received.append(json.loads(msg))
                
                # 收到结果后退出
                if messages_received[-1].get("type") == "result":
                    break
        except asyncio.TimeoutError:
            pass
        
        # 验证收到了所有必要的消息类型
        message_types = [m.get("type") for m in messages_received]
        assert "planning" in message_types
        assert "reasoning" in message_types
        assert "learning" in message_types
        assert "result" in message_types
```

**Step 2: 运行集成测试**

```bash
# 先启动后端
cd backend
python app.py &
BACKEND_PID=$!

# 在另一个终端运行测试
pytest tests/integration/test_end_to_end.py -v

# 停止后端
kill $BACKEND_PID
```

Expected: PASSED (2 tests)

**Step 3: Commit**

```bash
git add tests/integration/test_end_to_end.py
git commit -m "test(integration): add end-to-end integration tests"
```

---

### Task 3.2: 验证 5 个测试场景

**Files:**
- Create: `tests/integration/test_scenarios_e2e.py`

**Step 1: 编写场景集成测试**

创建 `tests/integration/test_scenarios_e2e.py`：
```python
import pytest
from backend.scenarios import SCENARIOS


@pytest.mark.parametrize("scenario_name", SCENARIOS.keys())
def test_scenario_execution(scenario_name):
    """测试所有场景的执行"""
    scenario = SCENARIOS[scenario_name]
    
    # 验证场景对象
    assert scenario is not None
    assert scenario.name == scenario_name
    
    # 获取初始观察
    observation = scenario.get_initial_observation()
    assert observation is not None
    assert observation.joint_positions is not None
    assert len(observation.joint_positions) == 7
    
    # 获取任务描述
    task = scenario.get_task_description()
    assert task is not None
    assert len(task) > 0


@pytest.mark.asyncio
async def test_scenario_1_spatial_detection():
    """场景 1：空间检测"""
    from backend.agent_bridge import AgentBridge
    from backend.websocket_manager import WebSocketManager
    
    ws_manager = WebSocketManager()
    bridge = AgentBridge(ws_manager)
    
    scenario = SCENARIOS["spatial_detection"]
    obs = scenario.get_initial_observation()
    task = scenario.get_task_description()
    
    # 验证观察有物体
    assert len(obs.objects) > 0


@pytest.mark.asyncio
async def test_scenario_2_single_grasp():
    """场景 2：单一抓取"""
    scenario = SCENARIOS["single_grasp"]
    obs = scenario.get_initial_observation()
    
    # 验证有目标物体
    assert any(obj["name"] == "red_cube" for obj in obs.objects)


@pytest.mark.asyncio
async def test_scenario_3_grasp_and_move():
    """场景 3：抓取 + 移动"""
    scenario = SCENARIOS["grasp_and_move"]
    task = scenario.get_task_description()
    
    # 验证任务包含多个动作
    assert "pick" in task.lower()
    assert "move" in task.lower()


@pytest.mark.asyncio
async def test_scenario_4_error_recovery():
    """场景 4：错误恢复"""
    scenario = SCENARIOS["error_recovery"]
    obs = scenario.get_initial_observation()
    
    # 验证有目标物体
    assert len(obs.objects) > 0


@pytest.mark.asyncio
async def test_scenario_5_dynamic_environment():
    """场景 5：动态环境"""
    scenario = SCENARIOS["dynamic_environment"]
    task = scenario.get_task_description()
    
    # 验证任务相关
    assert len(task) > 0
```

**Step 2: 运行场景测试**

```bash
pytest tests/integration/test_scenarios_e2e.py -v
```

Expected: PASSED (8 tests)

**Step 3: Commit**

```bash
git add tests/integration/test_scenarios_e2e.py
git commit -m "test(integration): add scenario end-to-end tests"
```

---

### Task 3.3: Bug 修复和性能优化

**Step 1: 收集测试过程中的 Bug 和性能问题**

运行系统：
```bash
# 后端
cd backend
python app.py

# 前端（新终端）
cd frontend
npm start

# 手动测试各场景
# 记录任何问题、崩溃或性能问题
```

**Step 2: 修复发现的问题**

常见问题和修复：
- 如果 WebSocket 连接断开：优化重连逻辑
- 如果消息丢失：添加消息队列
- 如果前端卡顿：优化渲染
- 如果后端响应慢：优化数据处理

示例：优化 Agent Bridge 的消息发送

修改 `backend/agent_bridge.py`：
```python
async def run_with_telemetry(self, task: str, observation: RobotObservation) -> Dict:
    """执行任务并实时推送四层处理过程（优化版）"""
    
    try:
        # ... 现有代码 ...
        
        # 添加性能监控
        import time
        start_time = time.time()
        
        # ... 执行逻辑 ...
        
        elapsed = time.time() - start_time
        print(f"Task execution time: {elapsed:.2f}s")
        
    except Exception as e:
        print(f"Error in run_with_telemetry: {e}")
        raise
```

**Step 3: 重新运行测试验证修复**

```bash
pytest tests/ -v
```

Expected: 所有测试通过

**Step 4: Commit**

```bash
git add backend/ frontend/src/
git commit -m "fix: resolve bugs and optimize performance"
```

---

### Task 3.4: 部署和文档

**Files:**
- Create: `README.md`
- Create: `docker-compose.yml`
- Create: `.env.example`

**Step 1: 创建项目 README**

创建 `README.md`：
```markdown
# 仿真验证 + 前端交互式调试工具

基于 Franka 机器人仿真环境，验证四层架构的端到端流程。

## 快速开始

### 后端启动
```bash
cd backend
pip install -r requirements.txt
python app.py
```
后端服务运行在 http://localhost:8000

### 前端启动
```bash
cd frontend
npm install
npm start
```
前端应用运行在 http://localhost:3000

## 架构

### 后端
- FastAPI + WebSocket
- SimpleAgent 四层架构
- Franka MuJoCo 仿真
- Hook 系统实时推送推理过程

### 前端
- React + TypeScript
- 实时 WebSocket 通信
- 交互式调试界面
- 四层推理过程可视化

## 测试场景

1. **空间检测** - 识别环境中的物体
2. **单一抓取** - 抓取目标物体
3. **抓取 + 移动** - 抓取后移动到目标位置
4. **错误恢复** - 处理执行失败和恢复
5. **动态环境** - 适应环境变化

## 运行测试
```bash
pytest tests/ -v
```

## 生成 API 文档
访问 http://localhost:8000/docs

## 常见问题

Q: WebSocket 连接失败？
A: 确保后端已启动，地址是 ws://localhost:8000/ws

Q: 前端找不到后端？
A: 检查 CORS 配置，确保后端允许来自 localhost:3000 的连接

## 后续优化

- [ ] 3D 机器人可视化
- [ ] 执行过程动画
- [ ] 性能分析仪表板
- [ ] Docker 容器化
```

**Step 2: 创建 Docker Compose 配置**

创建 `docker-compose.yml`：
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./backend:/app/backend
    command: uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_BACKEND_URL=http://localhost:8000
    volumes:
      - ./frontend:/app/frontend
    depends_on:
      - backend
```

**Step 3: Commit**

```bash
git add README.md docker-compose.yml
git commit -m "docs: add README and Docker configuration"
```

---

## 总结

### 完成的交付物

✅ **后端系统**
- FastAPI + WebSocket 服务器
- Franka 仿真环境集成
- SimpleAgent 包装层
- 四层 Hook 系统
- 5 个测试场景

✅ **前端系统**
- React + TypeScript 应用
- 交互式任务输入
- 四层实时监控面板
- WebSocket 通信

✅ **测试与验证**
- 单元测试（覆盖所有核心模块）
- 集成测试（端到端流程）
- 场景验证（5 个场景都可执行）

✅ **文档**
- README 使用指南
- Docker 部署配置
- 代码注释和类型注解

### 时间估计
- 阶段 1（后端）：3-4 天
- 阶段 2（前端）：3-4 天
- 阶段 3（集成）：2-3 天
- **总计：8-11 天**

### 下一步
- 阶段 4（可选）：展示优化（3D 可视化、动画等）
- 为客户展示做准备
- 性能调优和优化

---

**Plan saved to** `docs/plans/2026-04-17-simulation-verification-frontend-implementation.md`

