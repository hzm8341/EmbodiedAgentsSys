# MuJoCo Viewer + Frontend Integration Design

## Goal

When the user executes a task in the frontend debugger, the MuJoCo simulation window opens automatically and shows the robot performing smooth, real movements synchronized with the four-layer reasoning pipeline.

## Architecture

```
Frontend Execute (WebSocket)
    ↓
AgentBridge.run_with_telemetry()
    ├─ Planning  → plan with action_sequence per scenario
    └─ Per step:
        ├─ Reasoning → structured JSON action dict
        ├─ Execution → run_in_executor → SimulationService.execute_action()
        │                                   └─ MuJoCoDriver._animate_joints()
        │                                       └─ viewer.sync() × 40 frames → MuJoCo window
        └─ Learning → improvement suggestion
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Viewer launch | Auto on backend startup (FastAPI lifespan) | Simplest; launch_passive runs in its own render thread |
| Action format | Reasoning outputs structured JSON dict | No string parsing; deterministic; easy to test |
| Movement style | Smooth 40-frame interpolation at 60fps | Visual clarity for demos; ~0.67s per move |
| Threading | ThreadPoolExecutor(max_workers=1) | Single sim thread prevents mjData race conditions |

## Component Changes

### 1. `backend/main.py` — Lifespan hook

Add `lifespan` context manager to FastAPI app:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    simulation_service.initialize()
    simulation_service.launch_viewer()
    yield
    simulation_service.close_viewer()

app = FastAPI(lifespan=lifespan)
```

### 2. `backend/services/simulation.py` — Viewer lifecycle

```python
def launch_viewer(self):
    if self._driver is None:
        return
    self._viewer = mujoco.viewer.launch_passive(
        self._driver._model, self._driver._data
    )
    self._driver.set_viewer(self._viewer)

def close_viewer(self):
    if self._viewer:
        self._viewer.close()
        self._viewer = None
```

### 3. `simulation/mujoco/mujoco_driver.py` — Animation + viewer injection

New method `set_viewer(viewer)` stores the passive viewer handle.

New method `_animate_joints(joint_ids, q_start, q_target, n_frames=40)`:
- Interpolates joint positions over n_frames
- Calls `mujoco.mj_forward()` and `viewer.sync()` each frame
- Sleeps `1/60` s per frame (~60 fps, total ~0.67 s)

`move_arm_to()` replaces instant joint-set with `_animate_joints()`.

`_grasp()` / `_release()` add gripper joint open/close animation.

### 4. `agents/cognition/reasoning.py` — Structured action output

`DefaultReasoningLayer.generate_action()` returns `dict` instead of `str`:

```python
{"action": "move_arm_to", "params": {"arm": "left", "x": 0.4, "y": 0.0, "z": 0.5}}
{"action": "grasp",       "params": {"arm": "left", "force": 50}}
{"action": "move_arm_to", "params": {"arm": "left", "x": 0.4, "y": 0.0, "z": 0.6}}
```

Reads `plan["action_sequence"]` and `plan["current_step"]` to pick the right action per step.

### 5. `agents/cognition/planning.py` — Plan carries action sequence

`DefaultPlanningLayer.generate_plan()` includes `action_sequence` and tracks `current_step` (incremented each call or passed via observation).

### 6. `backend/services/scenarios.py` — Per-scenario action sequences

Each `Scenario` dataclass gains an `action_sequence: list[dict]` field:

| Scenario | Actions |
|----------|---------|
| `single_grasp` | move_arm_to(pre-grasp) → grasp → move_arm_to(lift) |
| `grasp_and_move` | move_arm_to(src) → grasp → move_arm_to(dst) |
| `spatial_detection` | move_arm_to(scan pos 1) → move_arm_to(scan pos 2) → move_arm_to(scan pos 3) |
| `error_recovery` | move_arm_to(target) → grasp(fails) → move_arm_to(retry) → grasp |
| `dynamic_environment` | move_arm_to(pos1) → move_arm_to(pos2) → move_arm_to(pos3) |

### 7. `backend/services/agent_bridge.py` — Real execution

Replace mock feedback with real simulation call:

```python
_sim_executor = ThreadPoolExecutor(max_workers=1)

# In run_with_telemetry execution step:
loop = asyncio.get_event_loop()
receipt = await loop.run_in_executor(
    _sim_executor,
    simulation_service.execute_action,
    action.get("action", ""),
    action.get("params", {}),
)
feedback = {
    "success": receipt.status.value == "success",
    "step": step,
    "action": action.get("action"),
    "result": receipt.result_message,
}
```

## Data Flow Per Step

```
plan = {"task": "single_grasp", "action_sequence": [...], "current_step": 0}
                                                                    ↓
reasoning → {"action": "move_arm_to", "params": {"arm":"left","x":0.4,"y":0.1,"z":0.3}}
                                                                    ↓
AgentBridge calls simulation_service.execute_action("move_arm_to", {...})
                                                                    ↓
MuJoCoDriver.move_arm_to("left", 0.4, 0.1, 0.3)
  → IK solve → q_solution
  → _animate_joints(joint_ids, q_start, q_solution, n_frames=40)
      → for i in 40: set qpos, mj_forward, viewer.sync(), sleep(1/60)
                                                                    ↓
MuJoCo window: robot arm moves smoothly to target over ~0.67s
                                                                    ↓
receipt.status = SUCCESS
feedback = {"success": True, "action": "move_arm_to", "result": "..."}
                                                                    ↓
WebSocket → frontend Execution card updates
```

## Error Handling

- If IK fails: `receipt.status = FAILED`, feedback `success=False`, frontend shows red, simulation stays in place
- If viewer not initialized (headless server): animation skips `sync()` but execution still runs
- If simulation not initialized: AgentBridge falls back to mock feedback (backward compatible)

## Testing

- Unit: `test_animate_joints` — verify joint interpolation without viewer
- Unit: `test_reasoning_structured_output` — verify dict output shape
- Integration: `test_agent_bridge_real_execution` — mock SimulationService, verify execute_action called with correct args
- Manual: Start backend → MuJoCo window opens → click `single_grasp` → Execute → watch arm move 3 steps
