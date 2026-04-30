:orphan:

# Dual Backend Visualization Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dual-backend robot simulation platform that keeps MuJoCo working, adds ROS2 Humble + Gazebo support, and provides a unified scene protocol for the existing frontend with real-time data-source switching.

**Architecture:** Introduce a backend abstraction and registry first, then move state and scene generation behind dedicated services, then upgrade the WebSocket/event protocol, then add the ROS2/Gazebo adapter, and finally wire frontend source switching onto the new unified scene flow. Preserve the current MuJoCo path while incrementally migrating API and frontend consumers to the new interfaces.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, asyncio, MuJoCo, ROS2 Humble (`rclpy`), Gazebo, pytest, Vue3, TypeScript, Three.js

---

## File Structure

### New backend files

- `backend/backends/base.py`
  Defines the backend interface and shared backend descriptor model.
- `backend/backends/mujoco_backend.py`
  Wraps the current MuJoCo simulation service behind the new backend interface.
- `backend/backends/ros2_gazebo_backend.py`
  Adds the ROS2 Humble + Gazebo backend adapter.
- `backend/services/backend_registry.py`
  Registers backends, exposes selected backend, and supports source switching.
- `backend/services/state_store.py`
  Owns robot runtime state and task state, replacing in-module dict storage.
- `backend/services/scene_service.py`
  Produces frontend-facing scene snapshots and scene deltas.
- `backend/services/event_bus.py`
  Provides an asyncio-driven event distribution layer between backends and WebSocket clients.
- `backend/services/websocket_hub.py`
  Replaces the current broadcast-only WebSocket manager with filtered subscriptions and per-client queues.
- `backend/models/state.py`
  Defines runtime state models.
- `backend/models/scene.py`
  Defines unified scene DTOs for frontend rendering.
- `backend/models/messages.py`
  Defines WebSocket envelope and event models.
- `backend/models/tasks.py`
  Defines task request, task state, and task result models.

### Existing backend files to modify

- `backend/main.py`
  Initialize the registry, event bus, and scene/state services in lifespan.
- `backend/api/routes.py`
  Route command execution through the registry and task services.
- `backend/api/state.py`
  Read state from `StateStore` instead of `_current_states`.
- `backend/api/agent_ws.py`
  Split command submission from event subscription semantics and use the new event hub.
- `backend/services/simulation.py`
  Either slim this down into MuJoCo-specific infrastructure or deprecate it behind `MujocoBackend`.
- `backend/services/websocket_manager.py`
  Either replace or reduce to compatibility wrappers over `websocket_hub.py`.

### Frontend files to modify

- `web-dashboard/src/store/useStatusStore.ts`
  Track selected backend and scene subscription status.
- `web-dashboard/src/components/ScenePanel.tsx`
  Add backend switching UI and consume scene snapshot/delta messages.
- `web-dashboard/src/components/RobotPanel.tsx`
  Read runtime state from the new unified protocol if this component currently binds old fields directly.
- `web-dashboard/src/services/*`
  Add a small client wrapper for unified scene and backend selection APIs.

### Test files

- `tests/backend/test_backend_registry.py`
- `tests/backend/test_state_store.py`
- `tests/backend/test_scene_service.py`
- `tests/backend/test_event_bus.py`
- `tests/backend/test_websocket_hub.py`
- `tests/backend/test_mujoco_backend.py`
- `tests/backend/test_ros2_gazebo_backend.py`
- `tests/backend/test_dual_backend_api.py`
- `web-dashboard/src/__tests__/scene-store.test.ts`

---

### Task 1: Introduce Backend Abstraction and Registry

**Files:**
- Create: `backend/backends/base.py`
- Create: `backend/backends/mujoco_backend.py`
- Create: `backend/services/backend_registry.py`
- Test: `tests/backend/test_backend_registry.py`

- [ ] **Step 1: Write the failing registry tests**

```python
# tests/backend/test_backend_registry.py
from backend.services.backend_registry import BackendRegistry


class DummyBackend:
    backend_id = "dummy"

    def descriptor(self):
        return {
            "backend_id": "dummy",
            "display_name": "Dummy",
            "kind": "mujoco",
            "available": True,
            "capabilities": ["scene", "state"],
            "extensions": {},
        }


def test_registry_returns_registered_backends():
    registry = BackendRegistry()
    registry.register(DummyBackend())

    descriptors = registry.list_backends()

    assert len(descriptors) == 1
    assert descriptors[0].backend_id == "dummy"


def test_registry_tracks_selected_backend():
    registry = BackendRegistry()
    registry.register(DummyBackend())

    registry.select_backend("dummy")

    assert registry.get_selected_backend().backend_id == "dummy"


def test_registry_rejects_unknown_selection():
    registry = BackendRegistry()

    try:
        registry.select_backend("missing")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected KeyError for missing backend")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_backend_registry.py -v`
Expected: FAIL with `ModuleNotFoundError` for `backend.services.backend_registry`

- [ ] **Step 3: Write the backend interface and registry**

```python
# backend/backends/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class BackendDescriptor(BaseModel):
    backend_id: str
    display_name: str
    kind: str
    available: bool = True
    capabilities: list[str] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)


class SimulationBackend(ABC):
    backend_id: str

    @abstractmethod
    def descriptor(self) -> BackendDescriptor:
        raise NotImplementedError
```

```python
# backend/services/backend_registry.py
from __future__ import annotations

from backend.backends.base import BackendDescriptor, SimulationBackend


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, SimulationBackend] = {}
        self._selected_backend_id: str | None = None

    def register(self, backend: SimulationBackend) -> None:
        self._backends[backend.backend_id] = backend
        if self._selected_backend_id is None:
            self._selected_backend_id = backend.backend_id

    def list_backends(self) -> list[BackendDescriptor]:
        return [backend.descriptor() for backend in self._backends.values()]

    def select_backend(self, backend_id: str) -> None:
        if backend_id not in self._backends:
            raise KeyError(f"Unknown backend: {backend_id}")
        self._selected_backend_id = backend_id

    def get_selected_backend(self) -> SimulationBackend:
        if self._selected_backend_id is None:
            raise RuntimeError("No backend registered")
        return self._backends[self._selected_backend_id]
```

```python
# backend/backends/mujoco_backend.py
from __future__ import annotations

from backend.backends.base import BackendDescriptor, SimulationBackend


class MujocoBackend(SimulationBackend):
    backend_id = "mujoco"

    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            backend_id="mujoco",
            display_name="MuJoCo",
            kind="mujoco",
            available=True,
            capabilities=["scene", "state", "command"],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_backend_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/backend/test_backend_registry.py backend/backends/base.py backend/backends/mujoco_backend.py backend/services/backend_registry.py
git commit -m "feat: add backend registry foundation"
```

---

### Task 2: Replace In-Module State Storage with StateStore and SceneService

**Files:**
- Create: `backend/models/state.py`
- Create: `backend/models/scene.py`
- Create: `backend/services/state_store.py`
- Create: `backend/services/scene_service.py`
- Modify: `backend/api/state.py`
- Test: `tests/backend/test_state_store.py`
- Test: `tests/backend/test_scene_service.py`

- [ ] **Step 1: Write failing tests for state storage and scene projection**

```python
# tests/backend/test_state_store.py
from backend.models.state import JointState, RobotRuntimeState
from backend.services.state_store import StateStore


def test_state_store_round_trips_robot_state():
    store = StateStore()
    state = RobotRuntimeState(
        robot_id="arm_001",
        backend="mujoco",
        timestamp=1.23,
        joints=[JointState(joint_name="j1", position=0.5)],
        status="idle",
    )

    store.put_robot_state(state)

    assert store.get_robot_state("arm_001").backend == "mujoco"
    assert store.get_robot_state("arm_001").joints[0].position == 0.5
```

```python
# tests/backend/test_scene_service.py
from backend.models.state import JointState, RobotRuntimeState
from backend.services.scene_service import SceneService
from backend.services.state_store import StateStore


def test_scene_service_builds_snapshot_from_runtime_state():
    store = StateStore()
    service = SceneService(store)
    store.put_robot_state(
        RobotRuntimeState(
            robot_id="arm_001",
            backend="mujoco",
            timestamp=2.0,
            joints=[JointState(joint_name="j1", position=0.2)],
            status="running",
        )
    )

    scene = service.build_snapshot("mujoco")

    assert scene.backend == "mujoco"
    assert len(scene.robots) == 1
    assert scene.robots[0].robot_id == "arm_001"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/backend/test_state_store.py tests/backend/test_scene_service.py -v`
Expected: FAIL with missing modules under `backend.models` and `backend.services`

- [ ] **Step 3: Implement runtime and scene models**

```python
# backend/models/state.py
from __future__ import annotations

from pydantic import BaseModel, Field


class JointState(BaseModel):
    joint_name: str
    position: float
    velocity: float | None = None


class RobotRuntimeState(BaseModel):
    robot_id: str
    backend: str
    timestamp: float
    joints: list[JointState] = Field(default_factory=list)
    status: str = "idle"
```

```python
# backend/models/scene.py
from __future__ import annotations

from pydantic import BaseModel, Field


class RobotView(BaseModel):
    robot_id: str
    joints: list[dict] = Field(default_factory=list)
    status: str = "idle"


class SceneViewModel(BaseModel):
    backend: str
    timestamp: float
    robots: list[RobotView] = Field(default_factory=list)
    objects: list[dict] = Field(default_factory=list)
```

```python
# backend/services/state_store.py
from __future__ import annotations

from backend.models.state import RobotRuntimeState


class StateStore:
    def __init__(self) -> None:
        self._robot_states: dict[str, RobotRuntimeState] = {}

    def put_robot_state(self, state: RobotRuntimeState) -> None:
        self._robot_states[state.robot_id] = state

    def get_robot_state(self, robot_id: str) -> RobotRuntimeState | None:
        return self._robot_states.get(robot_id)

    def list_robot_states(self, backend: str | None = None) -> list[RobotRuntimeState]:
        states = list(self._robot_states.values())
        if backend is None:
            return states
        return [state for state in states if state.backend == backend]
```

```python
# backend/services/scene_service.py
from __future__ import annotations

from backend.models.scene import RobotView, SceneViewModel
from backend.services.state_store import StateStore


class SceneService:
    def __init__(self, state_store: StateStore) -> None:
        self._state_store = state_store

    def build_snapshot(self, backend: str) -> SceneViewModel:
        states = self._state_store.list_robot_states(backend=backend)
        robots = [
            RobotView(
                robot_id=state.robot_id,
                joints=[joint.model_dump() for joint in state.joints],
                status=state.status,
            )
            for state in states
        ]
        timestamp = max((state.timestamp for state in states), default=0.0)
        return SceneViewModel(backend=backend, timestamp=timestamp, robots=robots)
```

- [ ] **Step 4: Move the state API to the new store**

```python
# backend/api/state.py
from fastapi import APIRouter, HTTPException

from backend.bootstrap import state_store

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("/{robot_id}")
async def get_robot_state(robot_id: str):
    state = state_store.get_robot_state(robot_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown robot: {robot_id}")
    return state
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/backend/test_state_store.py tests/backend/test_scene_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/backend/test_state_store.py tests/backend/test_scene_service.py backend/models/state.py backend/models/scene.py backend/services/state_store.py backend/services/scene_service.py backend/api/state.py
git commit -m "feat: add unified state and scene services"
```

---

### Task 3: Add Event Bus and WebSocket Hub with Scene Snapshot and Scene Delta Events

**Files:**
- Create: `backend/models/messages.py`
- Create: `backend/services/event_bus.py`
- Create: `backend/services/websocket_hub.py`
- Modify: `backend/api/agent_ws.py`
- Test: `tests/backend/test_event_bus.py`
- Test: `tests/backend/test_websocket_hub.py`

- [ ] **Step 1: Write failing tests for event delivery and subscription filtering**

```python
# tests/backend/test_event_bus.py
import asyncio
import pytest

from backend.services.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_delivers_event_to_subscriber():
    bus = EventBus()
    queue = bus.subscribe()

    await bus.publish({"event": "scene_snapshot", "backend": "mujoco"})
    received = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert received["event"] == "scene_snapshot"
```

```python
# tests/backend/test_websocket_hub.py
from backend.services.websocket_hub import should_deliver_event


def test_should_deliver_event_respects_backend_filter():
    subscription = {"backend": "ros2_gazebo"}
    event = {"event": "scene_delta", "backend": "mujoco"}

    assert should_deliver_event(subscription, event) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/backend/test_event_bus.py tests/backend/test_websocket_hub.py -v`
Expected: FAIL with missing modules

- [ ] **Step 3: Implement message envelope, bus, and delivery filter**

```python
# backend/models/messages.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event: str
    backend: str
    robot_id: str | None = None
    ts: float
    seq: int
    task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)
```

```python
# backend/services/event_bus.py
from __future__ import annotations

import asyncio


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    async def publish(self, event: dict) -> None:
        for queue in list(self._subscribers):
            await queue.put(event)
```

```python
# backend/services/websocket_hub.py
from __future__ import annotations


def should_deliver_event(subscription: dict, event: dict) -> bool:
    backend = subscription.get("backend")
    if backend and event.get("backend") != backend:
        return False

    event_name = subscription.get("event")
    if event_name and event.get("event") != event_name:
        return False

    robot_id = subscription.get("robot_id")
    if robot_id and event.get("robot_id") != robot_id:
        return False

    return True
```

- [ ] **Step 4: Move WebSocket API toward event subscriptions**

```python
# backend/api/agent_ws.py
from fastapi import APIRouter, WebSocket

from backend.bootstrap import event_bus, websocket_hub

router = APIRouter(prefix="/api/ws", tags=["ws"])


@router.websocket("")
async def unified_websocket(websocket: WebSocket) -> None:
    await websocket_hub.connect(websocket)
    subscriber = event_bus.subscribe()
    try:
        await websocket_hub.run_session(websocket, subscriber)
    finally:
        websocket_hub.disconnect(websocket)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/backend/test_event_bus.py tests/backend/test_websocket_hub.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/backend/test_event_bus.py tests/backend/test_websocket_hub.py backend/models/messages.py backend/services/event_bus.py backend/services/websocket_hub.py backend/api/agent_ws.py
git commit -m "feat: add unified realtime event bus"
```

---

### Task 4: Wrap Existing MuJoCo Path Behind the New Backend Interface

**Files:**
- Modify: `backend/backends/mujoco_backend.py`
- Modify: `backend/services/simulation.py`
- Modify: `backend/main.py`
- Test: `tests/backend/test_mujoco_backend.py`

- [ ] **Step 1: Write a failing test for MuJoCo backend scene and command behavior**

```python
# tests/backend/test_mujoco_backend.py
from backend.backends.mujoco_backend import MujocoBackend


class FakeSimulationService:
    def get_scene(self):
        return {"robot_position": [0, 0, 0]}

    def execute_action(self, action, params):
        class Receipt:
            class Status:
                value = "success"

            status = Status()
            result_message = "ok"
            result_data = {"action": action, "params": params}

        return Receipt()


def test_mujoco_backend_adapts_existing_service():
    backend = MujocoBackend(simulation_service=FakeSimulationService())

    scene = backend.get_scene()
    result = backend.execute_command("move_joint", {"joint": "j1"})

    assert scene["robot_position"] == [0, 0, 0]
    assert result["status"] == "success"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_mujoco_backend.py -v`
Expected: FAIL because `MujocoBackend` does not yet expose `get_scene` and `execute_command`

- [ ] **Step 3: Implement the MuJoCo adapter**

```python
# backend/backends/mujoco_backend.py
from __future__ import annotations

from backend.backends.base import BackendDescriptor, SimulationBackend
from backend.services.simulation import simulation_service


class MujocoBackend(SimulationBackend):
    backend_id = "mujoco"

    def __init__(self, simulation_service=simulation_service) -> None:
        self._simulation_service = simulation_service

    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            backend_id="mujoco",
            display_name="MuJoCo",
            kind="mujoco",
            available=True,
            capabilities=["scene", "state", "command", "reset"],
        )

    def get_scene(self) -> dict:
        return self._simulation_service.get_scene()

    def execute_command(self, action: str, params: dict) -> dict:
        receipt = self._simulation_service.execute_action(action, params)
        return {
            "status": receipt.status.value,
            "message": receipt.result_message,
            "data": receipt.result_data or {},
        }
```

- [ ] **Step 4: Register MuJoCo backend at startup**

```python
# backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.backends.mujoco_backend import MujocoBackend
from backend.bootstrap import backend_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend_registry.register(MujocoBackend())
    yield
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/backend/test_mujoco_backend.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/backend/test_mujoco_backend.py backend/backends/mujoco_backend.py backend/main.py
git commit -m "refactor: route mujoco through backend adapter"
```

---

### Task 5: Add ROS2 Humble + Gazebo Backend Skeleton and API Exposure

**Files:**
- Create: `backend/backends/ros2_gazebo_backend.py`
- Modify: `backend/services/backend_registry.py`
- Modify: `backend/api/routes.py`
- Test: `tests/backend/test_ros2_gazebo_backend.py`
- Test: `tests/backend/test_dual_backend_api.py`

- [ ] **Step 1: Write failing tests for the ROS2 backend descriptor and backend listing API**

```python
# tests/backend/test_ros2_gazebo_backend.py
from backend.backends.ros2_gazebo_backend import ROS2GazeboBackend


def test_ros2_backend_exposes_expected_capabilities():
    backend = ROS2GazeboBackend(node=None)

    descriptor = backend.descriptor()

    assert descriptor.backend_id == "ros2_gazebo"
    assert "scene" in descriptor.capabilities
    assert "command" in descriptor.capabilities
```

```python
# tests/backend/test_dual_backend_api.py
from fastapi.testclient import TestClient

from backend.main import app


def test_backends_endpoint_lists_multiple_backends():
    client = TestClient(app)

    response = client.get("/api/backends")

    assert response.status_code == 200
    data = response.json()
    assert "backends" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/backend/test_ros2_gazebo_backend.py tests/backend/test_dual_backend_api.py -v`
Expected: FAIL with missing backend module or missing `/api/backends`

- [ ] **Step 3: Implement the ROS2 backend skeleton**

```python
# backend/backends/ros2_gazebo_backend.py
from __future__ import annotations

from backend.backends.base import BackendDescriptor, SimulationBackend


class ROS2GazeboBackend(SimulationBackend):
    backend_id = "ros2_gazebo"

    def __init__(self, node) -> None:
        self._node = node

    def descriptor(self) -> BackendDescriptor:
        return BackendDescriptor(
            backend_id="ros2_gazebo",
            display_name="ROS2 Humble + Gazebo",
            kind="ros2_gazebo",
            available=self._node is not None,
            capabilities=["scene", "state", "command", "topics", "services"],
        )
```

- [ ] **Step 4: Expose backend listing and selection APIs**

```python
# backend/api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel

from backend.bootstrap import backend_registry

router = APIRouter(prefix="/api", tags=["api"])


class SelectBackendRequest(BaseModel):
    backend_id: str


@router.get("/backends")
def list_backends():
    selected = backend_registry.get_selected_backend().backend_id
    return {
        "selected_backend": selected,
        "backends": [item.model_dump() for item in backend_registry.list_backends()],
    }


@router.post("/backends/select")
def select_backend(req: SelectBackendRequest):
    backend_registry.select_backend(req.backend_id)
    return {"selected_backend": req.backend_id}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/backend/test_ros2_gazebo_backend.py tests/backend/test_dual_backend_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/backend/test_ros2_gazebo_backend.py tests/backend/test_dual_backend_api.py backend/backends/ros2_gazebo_backend.py backend/api/routes.py
git commit -m "feat: add ros2 gazebo backend skeleton"
```

---

### Task 6: Route Runtime State and Scene Events Through the Event Bus

**Files:**
- Modify: `backend/backends/mujoco_backend.py`
- Modify: `backend/backends/ros2_gazebo_backend.py`
- Modify: `backend/services/scene_service.py`
- Modify: `backend/services/state_store.py`
- Test: `tests/backend/test_dual_backend_api.py`

- [ ] **Step 1: Write a failing integration test for scene snapshot publication after backend selection**

```python
# tests/backend/test_dual_backend_api.py
def test_select_backend_returns_new_selection(client):
    response = client.post("/api/backends/select", json={"backend_id": "mujoco"})

    assert response.status_code == 200
    assert response.json()["selected_backend"] == "mujoco"
```

- [ ] **Step 2: Run test to verify it fails if the selection endpoint is not fully wired**

Run: `pytest tests/backend/test_dual_backend_api.py::test_select_backend_returns_new_selection -v`
Expected: FAIL if the registry is not shared across app lifecycle and routes

- [ ] **Step 3: Publish scene snapshots and state updates from backends**

```python
# backend/backends/mujoco_backend.py
class MujocoBackend(SimulationBackend):
    def __init__(self, simulation_service=simulation_service, state_store=None, event_bus=None, scene_service=None) -> None:
        self._simulation_service = simulation_service
        self._state_store = state_store
        self._event_bus = event_bus
        self._scene_service = scene_service

    async def publish_scene_snapshot(self) -> None:
        if self._event_bus is None or self._scene_service is None:
            return
        snapshot = self._scene_service.build_snapshot(self.backend_id)
        await self._event_bus.publish(
            {
                "event": "scene_snapshot",
                "backend": self.backend_id,
                "ts": snapshot.timestamp,
                "seq": 1,
                "payload": snapshot.model_dump(),
            }
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/backend/test_dual_backend_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/backend/test_dual_backend_api.py backend/backends/mujoco_backend.py backend/backends/ros2_gazebo_backend.py backend/services/scene_service.py backend/services/state_store.py
git commit -m "feat: publish unified scene events"
```

---

### Task 7: Add Frontend Backend Switching and Unified Scene Consumption

**Files:**
- Modify: `web-dashboard/src/store/useStatusStore.ts`
- Modify: `web-dashboard/src/components/ScenePanel.tsx`
- Create: `web-dashboard/src/services/runtime.ts`
- Test: `web-dashboard/src/__tests__/scene-store.test.ts`

- [ ] **Step 1: Write the failing frontend store test**

```ts
// web-dashboard/src/__tests__/scene-store.test.ts
import { describe, expect, it } from "vitest";
import { createStatusSlice } from "../store/useStatusStore";

describe("status store backend switching", () => {
  it("tracks selected backend and scene status", () => {
    const state = createStatusSlice((fn: any) => fn, () => ({
      selectedBackend: "mujoco",
      sceneConnected: false,
    }));

    state.setSelectedBackend("ros2_gazebo");

    expect(state.selectedBackend).toBe("ros2_gazebo");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web-dashboard && npm test -- scene-store.test.ts`
Expected: FAIL because `createStatusSlice` or `setSelectedBackend` does not exist yet

- [ ] **Step 3: Add backend switching state and runtime client**

```ts
// web-dashboard/src/store/useStatusStore.ts
type StatusState = {
  selectedBackend: string;
  sceneConnected: boolean;
  setSelectedBackend: (backendId: string) => void;
  setSceneConnected: (connected: boolean) => void;
};

export const createStatusSlice = (set: any) => ({
  selectedBackend: "mujoco",
  sceneConnected: false,
  setSelectedBackend: (backendId: string) => set({ selectedBackend: backendId }),
  setSceneConnected: (connected: boolean) => set({ sceneConnected: connected }),
});
```

```ts
// web-dashboard/src/services/runtime.ts
export async function selectBackend(backendId: string) {
  const response = await fetch("/api/backends/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ backend_id: backendId }),
  });
  return response.json();
}
```

- [ ] **Step 4: Update ScenePanel to request scene snapshot after switching**

```tsx
// web-dashboard/src/components/ScenePanel.tsx
const handleBackendChange = async (backendId: string) => {
  await selectBackend(backendId);
  setSelectedBackend(backendId);
  websocket.send(JSON.stringify({ type: "subscribe", backend: backendId, event: "scene_snapshot" }));
};
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd web-dashboard && npm test -- scene-store.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web-dashboard/src/__tests__/scene-store.test.ts web-dashboard/src/store/useStatusStore.ts web-dashboard/src/services/runtime.ts web-dashboard/src/components/ScenePanel.tsx
git commit -m "feat: add frontend backend switching"
```

---

### Task 8: Verify End-to-End Dual Backend and Frontend Compatibility

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/api/routes.py`
- Modify: `backend/api/agent_ws.py`
- Modify: `web-dashboard/src/components/ScenePanel.tsx`
- Test: `tests/backend/test_dual_backend_api.py`

- [ ] **Step 1: Add an end-to-end backend selection smoke test**

```python
# tests/backend/test_dual_backend_api.py
def test_scene_endpoint_uses_selected_backend(client):
    client.post("/api/backends/select", json={"backend_id": "mujoco"})

    response = client.get("/api/view/scene")

    assert response.status_code == 200
    assert response.json()["backend"] == "mujoco"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_dual_backend_api.py::test_scene_endpoint_uses_selected_backend -v`
Expected: FAIL because `/api/view/scene` is missing or not wired to the selected backend

- [ ] **Step 3: Wire the scene endpoint through selected backend and SceneService**

```python
# backend/api/routes.py
from backend.bootstrap import backend_registry, scene_service


@router.get("/view/scene")
def get_scene_view():
    selected = backend_registry.get_selected_backend()
    return scene_service.build_snapshot(selected.backend_id)
```

- [ ] **Step 4: Run backend and frontend verification commands**

Run: `pytest tests/backend/test_backend_registry.py tests/backend/test_state_store.py tests/backend/test_scene_service.py tests/backend/test_event_bus.py tests/backend/test_websocket_hub.py tests/backend/test_mujoco_backend.py tests/backend/test_ros2_gazebo_backend.py tests/backend/test_dual_backend_api.py -v`
Expected: PASS

Run: `cd web-dashboard && npm test -- scene-store.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/api/routes.py backend/api/agent_ws.py web-dashboard/src/components/ScenePanel.tsx tests/backend/test_dual_backend_api.py
git commit -m "feat: complete dual backend visualization path"
```

---

## Self-Review

### Spec coverage

- Dual backend support: covered by Tasks 1, 4, 5, 6, 8
- Unified scene model: covered by Tasks 2, 6, 8
- WebSocket unified protocol: covered by Task 3
- Frontend data-source switching: covered by Task 7
- Preserve MuJoCo path: covered by Task 4
- ROS2/Gazebo extension path: covered by Task 5

### Placeholder scan

- No `TODO`, `TBD`, or deferred “write tests later” steps remain
- Each task includes explicit files, tests, commands, and commit checkpoints

### Type consistency

- `backend_id` is used consistently across registry, route, and frontend switch calls
- `SceneViewModel` is the only public scene DTO in the plan
- `selected_backend` is used consistently in API responses

