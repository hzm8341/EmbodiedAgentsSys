# Vuer URDF 可视化系统实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Vuer 3D 可视化系统，支持加载 eyoubot URDF 并在网页上显示机器人模型。

**Architecture:** 系统由三个独立组件组成：Vuer Server（端口8012）负责3D渲染，FastAPI Backend（端口8000）提供REST API和WebSocket，Web Dashboard（端口5173）作为前端界面。数据流通过FastAPI中转。

**Tech Stack:** Python (Vuer, FastAPI, Pydantic), Vue 3 + TypeScript + Vite

---

## Phase 1: Vuer Server 基础搭建

### Task 1: 创建 vuer_server 目录结构

**Files:**
- Create: `vuer_server/__init__.py`
- Create: `vuer_server/requirements.txt`

**Step 1: Create directory and files**

```bash
mkdir -p vuer_server
touch vuer_server/__init__.py
```

**Step 2: Write requirements.txt**

```
vuer>=0.10.0
numpy
pyzmq
pydantic
fastapi
websockets
```

**Step 3: Commit**

```bash
git add vuer_server/
git commit -m "feat(vuer_server): create initial directory structure"
```

---

### Task 2: 迁移 constants.py（坐标系转换常量）

**Files:**
- Create: `vuer_server/constants.py`
- Copy from: `/media/hzm/Data/OpenWBT/deploy/teleop/open_television/constants.py`

**Step 1: Copy the file**

从 OpenWBT 复制 `constants.py` 到 `vuer_server/constants.py`

**Step 2: Commit**

```bash
git add vuer_server/constants.py
git commit -m "feat(vuer_server): migrate constants.py from OpenWBT"
```

---

### Task 3: 迁移 television.py（Vuer 核心类）

**Files:**
- Create: `vuer_server/television.py`
- Copy from: `/media/hzm/Data/OpenWBT/deploy/teleop/open_television/television.py`

**Step 1: Copy the file**

从 OpenWBT 复制 `television.py` 到 `vuer_server/television.py`

**Step 2: Modify imports**

将 `from deploy.teleop.open_television.television import TeleVision` 改为相对导入或保持原样

**Step 3: Commit**

```bash
git add vuer_server/television.py
git commit -m "feat(vuer_server): migrate television.py from OpenWBT"
```

---

### Task 4: 迁移 tv_wrapper.py（URDF 封装）

**Files:**
- Create: `vuer_server/tv_wrapper.py`
- Copy from: `/media/hzm/Data/OpenWBT/deploy/teleop/open_television/tv_wrapper.py`

**Step 1: Copy the file**

从 OpenWBT 复制 `tv_wrapper.py` 到 `vuer_server/tv_wrapper.py`

**Step 2: Modify imports**

更新相对导入路径

**Step 3: Commit**

```bash
git add vuer_server/tv_wrapper.py
git commit -m "feat(vuer_server): migrate tv_wrapper.py from OpenWBT"
```

---

### Task 5: 创建 urdf_loader.py（URDF 解析）

**Files:**
- Create: `vuer_server/urdf_loader.py`

**Step 1: Write the module**

```python
"""URDF loader for Vuer Server."""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel


class LinkInfo(BaseModel):
    name: str
    visual_geometry: Optional[str] = None
    collision_geometry: Optional[str] = None
    material_color: Optional[List[float]] = None
    inertial_mass: Optional[float] = None


class JointInfo(BaseModel):
    name: str
    type: str  # revolute, fixed, prismatic, etc.
    parent: str
    child: str
    axis: Optional[List[float]] = None
    origin_xyz: Optional[List[float]] = None
    origin_rpy: Optional[List[float]] = None
    limit_lower: Optional[float] = None
    limit_upper: Optional[float] = None


class URDFModel(BaseModel):
    name: str
    links: List[LinkInfo]
    joints: List[JointInfo]


class URDFLoader:
    """Loads and parses URDF files."""

    def __init__(self, urdf_dir: Path):
        self.urdf_dir = Path(urdf_dir)

    def load(self, urdf_path: str) -> URDFModel:
        """Load URDF file and return structured model."""
        tree = ET.parse(urdf_path)
        root = tree.getroot()

        links = []
        joints = []

        for element in root:
            tag = element.tag.lower()
            if tag == 'link':
                links.append(self._parse_link(element))
            elif tag == 'joint':
                joints.append(self._parse_joint(element))

        return URDFModel(
            name=root.get('name', 'unknown'),
            links=links,
            joints=joints
        )

    def _parse_link(self, elem: ET.Element) -> LinkInfo:
        name = elem.get('name', '')
        visual_geom = None
        collision_geom = None
        color = None
        mass = None

        for child in elem:
            tag = child.tag.lower()
            if tag == 'visual':
                geom = child.find('geometry')
                if geom is not None:
                    mesh = geom.find('mesh')
                    if mesh is not None:
                        visual_geom = mesh.get('filename')
                material = child.find('material')
                if material is not None:
                    color_elem = material.find('color')
                    if color_elem is not None:
                        rgba = color_elem.get('rgba', '').split()
                        color = [float(x) for x in rgba] if rgba else None
            elif tag == 'collision':
                geom = child.find('geometry')
                if geom is not None:
                    mesh = geom.find('mesh')
                    if mesh is not None:
                        collision_geom = mesh.get('filename')
            elif tag == 'inertial':
                mass_elem = child.find('mass')
                if mass_elem is not None:
                    mass = float(mass_elem.get('value', 0))

        return LinkInfo(
            name=name,
            visual_geometry=visual_geom,
            collision_geometry=collision_geom,
            material_color=color,
            inertial_mass=mass
        )

    def _parse_joint(self, elem: ET.Element) -> JointInfo:
        name = elem.get('name', '')
        joint_type = elem.get('type', 'fixed')
        parent = elem.find('parent')
        child = elem.find('child')
        axis = elem.find('axis')
        origin = elem.find('origin')
        limit = elem.find('limit')

        parent_name = parent.get('link') if parent is not None else ''
        child_name = child.get('link') if child is not None else ''

        axis_xyz = None
        if axis is not None:
            axis_xyz = [float(x) for x in axis.get('xyz', '0 0 0').split()]

        origin_xyz = None
        origin_rpy = None
        if origin is not None:
            xyz = origin.get('xyz')
            rpy = origin.get('rpy')
            if xyz:
                origin_xyz = [float(x) for x in xyz.split()]
            if rpy:
                origin_rpy = [float(x) for x in rpy.split()]

        limit_lower = None
        limit_upper = None
        if limit is not None:
            limit_lower = float(limit.get('lower', 0))
            limit_upper = float(limit.get('upper', 0))

        return JointInfo(
            name=name,
            type=joint_type,
            parent=parent_name,
            child=child_name,
            axis=axis_xyz,
            origin_xyz=origin_xyz,
            origin_rpy=origin_rpy,
            limit_lower=limit_lower,
            limit_upper=limit_upper
        )
```

**Step 2: Run basic import test**

```bash
cd vuer_server && python -c "from urdf_loader import URDFLoader; print('OK')"
```

**Step 3: Commit**

```bash
git add vuer_server/urdf_loader.py
git commit -m "feat(vuer_server): add URDF loader"
```

---

### Task 6: 创建 vuer_server main.py（启动脚本）

**Files:**
- Create: `vuer_server/server.py`

**Step 1: Write server.py**

```python
"""Vuer Server main entry point."""
import argparse
from pathlib import Path
from urdf_loader import URDFLoader


def main():
    parser = argparse.ArgumentParser(description='Vuer URDF Server')
    parser.add_argument('--urdf-dir', type=str, default='../assets/eyoubot',
                        help='Directory containing URDF files')
    parser.add_argument('--port', type=int, default=8012,
                        help='WebSocket port')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind')
    args = parser.parse_args()

    print(f"Vuer Server starting on {args.host}:{args.port}")
    print(f"URDF directory: {args.urdf_dir}")

    urdf_loader = URDFLoader(Path(args.urdf_dir))
    urdf_path = Path(args.urdf_dir) / "eu_ca_describtion_lbs6.urdf"

    if urdf_path.exists():
        model = urdf_loader.load(str(urdf_path))
        print(f"Loaded robot: {model.name} with {len(model.links)} links and {len(model.joints)} joints")
    else:
        print(f"URDF file not found: {urdf_path}")

    print("Vuer Server placeholder - TODO: integrate with Vuer")


if __name__ == '__main__':
    main()
```

**Step 2: Test run**

```bash
python vuer_server/server.py --help
python vuer_server/server.py
```

**Step 3: Commit**

```bash
git add vuer_server/server.py
git commit -m "feat(vuer_server): add main server entry point"
```

---

## Phase 2: FastAPI Backend 扩展

### Task 7: 创建 URDF API 路由

**Files:**
- Create: `backend/api/urdf.py`

**Step 1: Write the API module**

```python
"""URDF API endpoints."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from vuer_server.urdf_loader import URDFLoader, URDFModel

router = APIRouter(prefix="/api/urdf", tags=["urdf"])

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


class URDFListItem(BaseModel):
    robot_id: str
    name: str
    urdf_path: str


class URDFLoadRequest(BaseModel):
    robot_id: str


@router.get("/list", response_model=List[URDFListItem])
async def list_urdf_models():
    """List all available URDF models."""
    models = []

    if not ASSETS_DIR.exists():
        return models

    for robot_dir in ASSETS_DIR.iterdir():
        if robot_dir.is_dir():
            urdf_files = list(robot_dir.glob("*.urdf"))
            for urdf_file in urdf_files:
                loader = URDFLoader(robot_dir)
                try:
                    model = loader.load(str(urdf_file))
                    models.append(URDFListItem(
                        robot_id=robot_dir.name,
                        name=model.name,
                        urdf_path=str(urdf_file.relative_to(ASSETS_DIR))
                    ))
                except Exception:
                    continue

    return models


@router.get("/{robot_id}", response_model=URDFModel)
async def get_urdf_model(robot_id: str):
    """Get URDF model structure."""
    robot_dir = ASSETS_DIR / robot_id

    if not robot_dir.exists():
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

    urdf_files = list(robot_dir.glob("*.urdf"))
    if not urdf_files:
        raise HTTPException(status_code=404, detail=f"No URDF found for {robot_id}")

    loader = URDFLoader(robot_dir)
    model = loader.load(str(urdf_files[0]))

    return model


@router.post("/load")
async def load_urdf(request: URDFLoadRequest):
    """Load a specific URDF model."""
    robot_dir = ASSETS_DIR / request.robot_id

    if not robot_dir.exists():
        raise HTTPException(status_code=404, detail=f"Robot {request.robot_id} not found")

    urdf_files = list(robot_dir.glob("*.urdf"))
    if not urdf_files:
        raise HTTPException(status_code=404, detail=f"No URDF found")

    loader = URDFLoader(robot_dir)
    model = loader.load(str(urdf_files[0]))

    return {"status": "loaded", "robot_id": request.robot_id, "model": model}
```

**Step 2: Test import**

```bash
cd /media/hzm/Data/EmbodiedAgentsSys && python -c "from backend.api.urdf import router; print('OK')"
```

**Step 3: Commit**

```bash
git add backend/api/urdf.py
git commit -m "feat(backend): add URDF API endpoints"
```

---

### Task 8: 创建 WebSocket 管理器

**Files:**
- Create: `backend/services/websocket_manager.py`

**Step 1: Write WebSocket manager**

```python
"""WebSocket connection manager."""
from typing import Dict, List, Set
from fastapi import WebSocket
import asyncio
import json


class WebSocketManager:
    """Manages WebSocket connections for robot state updates."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, robot_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if robot_id not in self.active_connections:
            self.active_connections[robot_id] = set()
        self.active_connections[robot_id].add(websocket)

    def disconnect(self, websocket: WebSocket, robot_id: str):
        """Remove a WebSocket connection."""
        if robot_id in self.active_connections:
            self.active_connections[robot_id].discard(websocket)
            if not self.active_connections[robot_id]:
                del self.active_connections[robot_id]

    async def send_state(self, robot_id: str, state: dict):
        """Broadcast state to all connections for a robot."""
        if robot_id not in self.active_connections:
            return

        message = json.dumps(state)
        disconnected = []

        for websocket in self.active_connections[robot_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws, robot_id)

    async def broadcast(self, message: str):
        """Broadcast message to all connections."""
        for robot_id in self.active_connections:
            await self.send_state(robot_id, {"type": "broadcast", "data": message})


manager = WebSocketManager()
```

**Step 2: Test import**

```bash
python -c "from backend.services.websocket_manager import manager; print('OK')"
```

**Step 3: Commit**

```bash
git add backend/services/websocket_manager.py
git commit -m "feat(backend): add WebSocket manager"
```

---

### Task 9: 创建状态 API 路由

**Files:**
- Create: `backend/api/state.py`

**Step 1: Write state API**

```python
"""Robot state API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.services.websocket_manager import manager

router = APIRouter(prefix="/api/state", tags=["state"])


class JointState(BaseModel):
    joint_name: str
    position: float
    velocity: Optional[float] = None


class RobotState(BaseModel):
    robot_id: str
    joints: List[JointState]
    timestamp: float


_current_states: dict = {}


@router.get("/{robot_id}", response_model=RobotState)
async def get_robot_state(robot_id: str):
    """Get current state of a robot."""
    if robot_id not in _current_states:
        return RobotState(
            robot_id=robot_id,
            joints=[],
            timestamp=0.0
        )
    return _current_states[robot_id]


@router.post("/{robot_id}")
async def update_robot_state(robot_id: str, state: RobotState):
    """Update robot state (called by simulation process)."""
    _current_states[robot_id] = state
    await manager.send_state(robot_id, state.dict())
    return {"status": "updated"}


@router.websocket("/ws/{robot_id}")
async def websocket_state(websocket: WebSocket, robot_id: str):
    """WebSocket endpoint for real-time state updates."""
    await manager.connect(websocket, robot_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_state(robot_id, {"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, robot_id)
```

**Step 2: Test import**

```bash
python -c "from backend.api.state import router; print('OK')"
```

**Step 3: Commit**

```bash
git add backend/api/state.py
git commit -m "feat(backend): add state API endpoints"
```

---

### Task 10: 更新 backend main.py

**Files:**
- Modify: `backend/main.py`

**Step 1: Read current main.py**

```bash
cat backend/main.py
```

**Step 2: Update main.py**

```python
"""FastAPI backend main entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import urdf, state

app = FastAPI(title="EmbodiedAgentsSys Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(urdf.router)
app.include_router(state.router)


@app.get("/")
async def root():
    return {"message": "EmbodiedAgentsSys Backend", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 3: Test startup**

```bash
cd /media/hzm/Data/EmbodiedAgentsSys && python -c "from backend.main import app; print('OK')"
```

**Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): update main.py with URDF and state routes"
```

---

## Phase 3: 迁移 eyoubot 资源文件

### Task 11: 复制 eyoubot URDF 和 meshes

**Files:**
- Create: `assets/eyoubot/eu_ca_describtion_lbs6.urdf`
- Create: `assets/eyoubot/meshes/*`

**Step 1: Copy files**

```bash
mkdir -p assets/eyoubot/meshes
cp /media/hzm/Data/OpenWBT/deploy/assets/eyoubot/eu_ca_describtion_lbs6.urdf assets/eyoubot/
cp /media/hzm/Data/OpenWBT/deploy/assets/eyoubot/meshes/* assets/eyoubot/meshes/
```

**Step 2: Verify copy**

```bash
ls -la assets/eyoubot/
ls assets/eyoubot/meshes/ | head -10
```

**Step 3: Commit**

```bash
git add assets/eyoubot/
git commit -m "feat(assets): migrate eyoubot URDF and meshes from OpenWBT"
```

---

## Phase 4: Web Dashboard 集成

### Task 12: 创建 URDFViewer 组件

**Files:**
- Create: `web-dashboard/src/components/URDFViewer.vue`

**Step 1: Write URDFViewer.vue**

```vue
<template>
  <div class="urdf-viewer">
    <div class="viewer-header">
      <h3>3D Viewer</h3>
      <div class="controls">
        <button @click="resetView">Reset</button>
        <button @click="toggleGrid">Grid: {{ showGrid ? 'ON' : 'OFF' }}</button>
        <button @click="togglePerspective">
          {{ isPerspective ? 'Perspective' : 'Orthographic' }}
        </button>
      </div>
    </div>
    <div class="viewer-content">
      <iframe
        ref="vuerFrame"
        :src="vuerUrl"
        class="vuer-iframe"
        allow="xr-spatial-tracking"
      ></iframe>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  robotId: string
  vuerPort: number
}>()

const showGrid = ref(true)
const isPerspective = ref(true)

const vuerUrl = computed(() => `http://localhost:${props.vuerPort}`)

const resetView = () => {
  // Post message to Vuer iframe
}

const toggleGrid = () => {
  showGrid.value = !showGrid.value
}

const togglePerspective = () => {
  isPerspective.value = !isPerspective.value
}
</script>

<style scoped>
.urdf-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
}

.controls {
  display: flex;
  gap: 8px;
}

.controls button {
  padding: 4px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}

.controls button:hover {
  background: #e0e0e0;
}

.viewer-content {
  flex: 1;
  position: relative;
}

.vuer-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
```

**Step 2: Commit**

```bash
git add web-dashboard/src/components/URDFViewer.vue
git commit -m "feat(web): add URDFViewer component"
```

---

### Task 13: 创建 ModelTree 组件

**Files:**
- Create: `web-dashboard/src/components/ModelTree.vue`

**Step 1: Write ModelTree.vue**

```vue
<template>
  <div class="model-tree">
    <div class="tree-header">
      <h3>Model Tree</h3>
      <div class="tree-actions">
        <button @click="showAll">Show All</button>
        <button @click="hideAll">Hide All</button>
      </div>
    </div>
    <div class="tree-content">
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <TreeNode
        v-else
        v-for="link in model?.links || []"
        :key="link.name"
        :node="link"
        :expanded="expandedNodes"
        :hiddenNodes="hiddenNodes"
        @toggle="toggleNode"
        @visibility="toggleVisibility"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import TreeNode from './TreeNode.vue'

const props = defineProps<{
  robotId: string
}>()

const model = ref(null)
const loading = ref(false)
const error = ref(null)
const expandedNodes = ref(new Set())
const hiddenNodes = ref(new Set())

const loadModel = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`/api/urdf/${props.robotId}`)
    model.value = await response.json()
  } catch (e) {
    error.value = 'Failed to load model'
  } finally {
    loading.value = false
  }
}

watch(() => props.robotId, loadModel, { immediate: true })

const toggleNode = (name) => {
  if (expandedNodes.value.has(name)) {
    expandedNodes.value.delete(name)
  } else {
    expandedNodes.value.add(name)
  }
}

const toggleVisibility = (name) => {
  if (hiddenNodes.value.has(name)) {
    hiddenNodes.value.delete(name)
  } else {
    hiddenNodes.value.add(name)
  }
}

const showAll = () => {
  hiddenNodes.value.clear()
}

const hideAll = () => {
  model.value?.links?.forEach(link => {
    hiddenNodes.value.add(link.name)
  })
}
</script>

<style scoped>
.model-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
}

.tree-actions {
  display: flex;
  gap: 8px;
}

.tree-actions button {
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 12px;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.loading, .error {
  padding: 16px;
  text-align: center;
  color: #666;
}

.error {
  color: #d32f2f;
}
</style>
```

**Step 2: Commit**

```bash
git add web-dashboard/src/components/ModelTree.vue
git commit -m "feat(web): add ModelTree component"
```

---

### Task 14: 创建 TreeNode 组件

**Files:**
- Create: `web-dashboard/src/components/TreeNode.vue`

**Step 1: Write TreeNode.vue**

```vue
<template>
  <div class="tree-node">
    <div
      class="node-label"
      :style="{ paddingLeft: depth * 16 + 'px' }"
    >
      <span v-if="hasChildren" class="expand-icon" @click="$emit('toggle', node.name)">
        {{ expanded ? '▼' : '▶' }}
      </span>
      <span v-else class="expand-icon spacer"></span>
      <input
        type="checkbox"
        :checked="!hidden"
        @change="$emit('visibility', node.name)"
      />
      <span class="node-name">{{ node.name }}</span>
    </div>
    <div v-if="hasChildren && expanded" class="node-children">
      <TreeNode
        v-for="child in getChildren()"
        :key="child.name"
        :node="child"
        :depth="depth + 1"
        :expanded="expanded"
        :hidden="hidden"
        :all-nodes="allNodes"
        @toggle="$emit('toggle', $event)"
        @visibility="$emit('visibility', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  node: any
  depth: number
  expanded: boolean
  hidden: boolean
  allNodes: any[]
}>()

defineEmits(['toggle', 'visibility'])

const hasChildren = computed(() => {
  return props.allNodes?.some(n => n.parent === props.node.name)
})

const getChildren = () => {
  return props.allNodes?.filter(n => n.parent === props.node.name) || []
}
</script>

<style scoped>
.tree-node {
  user-select: none;
}

.node-label {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
  cursor: pointer;
}

.node-label:hover {
  background: #f0f0f0;
}

.expand-icon {
  width: 16px;
  font-size: 10px;
  color: #666;
}

.expand-icon.spacer {
  visibility: hidden;
}

.node-name {
  font-size: 13px;
}
</style>
```

**Step 2: Commit**

```bash
git add web-dashboard/src/components/TreeNode.vue
git commit -m "feat(web): add TreeNode component"
```

---

### Task 15: 更新 App.vue 集成组件

**Files:**
- Modify: `web-dashboard/src/App.vue`

**Step 1: Read current App.vue**

```bash
cat web-dashboard/src/App.vue
```

**Step 2: Update App.vue**

```vue
<template>
  <div class="app">
    <header class="app-header">
      <h1>EmbodiedAgentsSys</h1>
    </header>
    <main class="app-main">
      <aside class="sidebar">
        <div class="robot-selector">
          <label>Robot:</label>
          <select v-model="selectedRobot" @change="onRobotChange">
            <option v-for="robot in robots" :key="robot.robot_id" :value="robot.robot_id">
              {{ robot.name }}
            </option>
          </select>
        </div>
        <ModelTree v-if="selectedRobot" :robotId="selectedRobot" />
      </aside>
      <section class="content">
        <URDFViewer
          v-if="selectedRobot"
          :robotId="selectedRobot"
          :vuerPort="8012"
        />
        <div v-else class="placeholder">
          Select a robot to view its model
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ModelTree from './components/ModelTree.vue'
import URDFViewer from './components/URDFViewer.vue'

const robots = ref([])
const selectedRobot = ref('')

const loadRobots = async () => {
  const response = await fetch('/api/urdf/list')
  robots.value = await response.json()
  if (robots.value.length > 0) {
    selectedRobot.value = robots.value[0].robot_id
  }
}

const onRobotChange = () => {
  // Trigger model reload
}

onMounted(loadRobots)
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  padding: 16px;
  background: #1976d2;
  color: white;
}

.app-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #ddd;
  overflow: hidden;
}

.robot-selector {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid #ddd;
}

.robot-selector select {
  flex: 1;
  padding: 4px;
}

.content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  color: #999;
}
</style>
```

**Step 2: Commit**

```bash
git add web-dashboard/src/App.vue
git commit -m "feat(web): integrate URDF components into App.vue"
```

---

## Phase 5: 集成测试

### Task 16: 端到端测试

**Step 1: Start backend**

```bash
cd /media/hzm/Data/EmbodiedAgentsSys
python -m backend.main
```

**Step 2: Test API endpoints**

```bash
curl http://localhost:8000/api/urdf/list
curl http://localhost:8000/api/urdf/eyoubot
curl http://localhost:8000/health
```

**Step 3: Verify expected output**

Expected: JSON with eyoubot model data

**Step 4: Commit all remaining changes**

```bash
git status
git add -A
git commit -m "feat: complete Vuer URDF visualization system"
```

---

## 验收检查清单

- [ ] `python -m backend.main` 启动成功，端口 8000
- [ ] `GET /api/urdf/list` 返回 eyoubot 模型
- [ ] `GET /api/urdf/eyoubot` 返回完整模型结构
- [ ] `python vuer_server/server.py` 可启动（占位符）
- [ ] Web Dashboard 可显示 ModelTree
- [ ] Web Dashboard 可显示 URDFViewer iframe
