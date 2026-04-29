# Embodied Agent Sim/Real Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the project into a single execution mainline, make simulation debugging production-usable, and safely enable real-robot command execution with observability and auditability.

**Architecture:** Build one authoritative chain (`Task -> Planner -> Executor -> BackendAdapter -> Feedback`) shared by REST and WebSocket surfaces. Keep simulation and real robot as backend adapters under the same protocol and state machine. Enforce safety, approval, and traceability as cross-cutting gates.

**Tech Stack:** Python 3.10+, FastAPI, WebSocket, MuJoCo, React + TypeScript + Zustand, Pytest

---

## Phase 0: Architecture Convergence (Week 1)

### Task P0-1: Unify Authoritative Execution Entry

**Files:**
- Create: `backend/models/task_protocol.py`
- Create: `backend/services/task_execution_service.py`
- Modify: `backend/api/chat.py`
- Modify: `backend/api/agent_ws.py`
- Test: `tests/backend/test_execution_unified_entry.py`

- [ ] **Step 1: Write failing integration test for REST/WS behavior parity**

```python
# tests/backend/test_execution_unified_entry.py
# Assert same task yields equivalent event sequence + final result
# through /api/chat and /api/agent/ws.
```

- [ ] **Step 2: Run test to confirm failure**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/backend/test_execution_unified_entry.py -q`
Expected: FAIL (unified service missing)

- [ ] **Step 3: Implement protocol models**

```python
# backend/models/task_protocol.py
# TaskRequest, ActionCommand, ExecutionEvent, TaskResult
# Include protocol_version="v1".
```

- [ ] **Step 4: Implement shared execution service**

```python
# backend/services/task_execution_service.py
# async execute_task(request: TaskRequest) -> TaskResult
# single business path used by all API surfaces
```

- [ ] **Step 5: Refactor API endpoints to call shared service**

```python
# backend/api/chat.py and backend/api/agent_ws.py
# Parse/format only; no duplicate execution logic.
```

- [ ] **Step 6: Re-run test and verify pass**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/backend/test_execution_unified_entry.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/models/task_protocol.py backend/services/task_execution_service.py backend/api/chat.py backend/api/agent_ws.py tests/backend/test_execution_unified_entry.py
git commit -m "refactor: unify task execution entry across REST and WS"
```

### Task P0-2: Standardize Event Protocol

**Files:**
- Modify: `backend/services/agent_bridge.py`
- Modify: `backend/services/websocket_hub.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/hooks/useAgentWebSocket.ts`
- Modify: `frontend/src/store/useSyncStore.ts`
- Test: `tests/backend/test_event_protocol_v1.py`

- [ ] **Step 1: Add failing protocol contract test**

```python
# tests/backend/test_event_protocol_v1.py
# Ensure each event includes trace_id, step, type, timestamp, payload, status, error_code.
```

- [ ] **Step 2: Run test to confirm failure**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/backend/test_event_protocol_v1.py -q`
Expected: FAIL (fields missing/inconsistent)

- [ ] **Step 3: Refactor backend event emitters to v1 schema**

```python
# agent_bridge/websocket_hub emit only ExecutionEvent v1
```

- [ ] **Step 4: Refactor frontend parser/store to consume v1 schema**

```ts
// useAgentWebSocket + useSyncStore parse stable payload shape
```

- [ ] **Step 5: Re-run protocol test and frontend type-check**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/backend/test_event_protocol_v1.py -q`
Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/agent_bridge.py backend/services/websocket_hub.py frontend/src/types.ts frontend/src/hooks/useAgentWebSocket.ts frontend/src/store/useSyncStore.ts tests/backend/test_event_protocol_v1.py
git commit -m "feat: standardize execution event protocol v1"
```

---

## Phase 1: Simulation Debugger Productization (Weeks 2-3)

### Task P1-1: Trace Storage and Replay

**Files:**
- Create: `backend/services/trace_store.py`
- Modify: `backend/services/task_execution_service.py`
- Create: `backend/api/traces.py`
- Modify: `backend/main.py`
- Test: `tests/backend/test_trace_store.py`
- Test: `tests/backend/test_trace_replay_api.py`

- [ ] **Step 1: Write failing tests for trace persistence and replay APIs**
- [ ] **Step 2: Run tests to confirm failure**
- [ ] **Step 3: Implement trace store (append-only JSONL with trace_id index)**
- [ ] **Step 4: Persist all execution events and final result from unified service**
- [ ] **Step 5: Add `/api/traces/{trace_id}` and `/api/traces/{trace_id}/replay` routes**
- [ ] **Step 6: Re-run tests and verify pass**
- [ ] **Step 7: Commit**

### Task P1-2: Interactive Debug Controls (step/pause/resume/abort)

**Files:**
- Modify: `backend/api/agent_ws.py`
- Modify: `backend/services/task_execution_service.py`
- Modify: `frontend/src/components/AgentPanel.tsx`
- Modify: `frontend/src/store/useStatusStore.ts`
- Modify: `frontend/src/store/useSyncStore.ts`
- Test: `tests/backend/test_agent_ws_controls.py`

- [ ] **Step 1: Add failing WS control test**
- [ ] **Step 2: Implement control messages and execution state transitions**
- [ ] **Step 3: Add UI controls and state indicators**
- [ ] **Step 4: Verify test + manual scenario run**
- [ ] **Step 5: Commit**

### Task P1-3: Simulation Stability Hardening

**Files:**
- Modify: `backend/services/simulation.py`
- Modify: `simulation/mujoco/mujoco_driver.py`
- Modify: `backend/services/state_store.py`
- Test: `tests/backend/test_simulation_state_machine.py`
- Test: `tests/backend/test_simulation_timeout_recovery.py`

- [ ] **Step 1: Add failing tests for timeout, recovery, and state machine transitions**
- [ ] **Step 2: Implement explicit execution states (`idle/running/paused/aborted/error`)**
- [ ] **Step 3: Add timeout guards and forced recovery to safe state**
- [ ] **Step 4: Re-run tests and verify pass**
- [ ] **Step 5: Commit**

---

## Phase 2: Task-Level Embodied Intelligence (Weeks 4-6)

### Task P2-1: Task State Machine with Replanning

**Files:**
- Create: `agents/core/task_state_machine.py`
- Modify: `backend/services/task_execution_service.py`
- Modify: `agents/cognition/planning.py`
- Modify: `agents/cognition/reasoning.py`
- Test: `tests/test_task_state_machine.py`
- Test: `tests/test_task_replanning.py`

- [ ] **Step 1: Add failing tests for `planned->executing->verifying->replanning->done/failed`**
- [ ] **Step 2: Implement state machine and bounded retry policy**
- [ ] **Step 3: Integrate planner/reasoner with state machine loop**
- [ ] **Step 4: Re-run tests and verify pass**
- [ ] **Step 5: Commit**

### Task P2-2: Observation Refresh Closed Loop

**Files:**
- Modify: `backend/services/agent_bridge.py`
- Modify: `backend/services/simulation.py`
- Modify: `agents/core/types.py`
- Test: `tests/backend/test_observation_refresh_loop.py`

- [ ] **Step 1: Add failing test that observation updates after every action**
- [ ] **Step 2: Enforce observation refresh in execution loop**
- [ ] **Step 3: Feed refreshed observation into next reasoning step**
- [ ] **Step 4: Re-run test and verify pass**
- [ ] **Step 5: Commit**

### Task P2-3: Approval and Safety Policy Gates

**Files:**
- Modify: `agents/policy/validation_pipeline.py`
- Modify: `agents/human_oversight/engine.py`
- Modify: `backend/api/agent_ws.py`
- Modify: `frontend/src/components/AgentPanel.tsx`
- Test: `tests/test_policy_risk_levels.py`
- Test: `tests/backend/test_approval_flow.py`

- [ ] **Step 1: Add failing tests for low/medium/high risk behavior**
- [ ] **Step 2: Implement risk classification + approval-required states**
- [ ] **Step 3: Add approve/reject actions to WS and UI**
- [ ] **Step 4: Re-run tests and verify pass**
- [ ] **Step 5: Commit**

---

## Phase 3: Real-Robot Debugging and Control (Weeks 7-10)

### Task P3-1: RealRobot Backend Adapter

**Files:**
- Create: `backend/backends/real_robot_backend.py`
- Modify: `backend/services/backend_registry.py`
- Modify: `backend/api/routes.py`
- Create: `config/real_robot.yaml`
- Test: `tests/backend/test_real_backend_contract.py`

- [ ] **Step 1: Add failing backend contract test (same interface as MujocoBackend)**
- [ ] **Step 2: Implement connection lifecycle (init/heartbeat/reconnect/shutdown)**
- [ ] **Step 3: Implement command dispatch with completion acknowledgement**
- [ ] **Step 4: Re-run tests and verify pass**
- [ ] **Step 5: Commit**

### Task P3-2: Real-Robot Safety Guard

**Files:**
- Create: `backend/services/safety_guard.py`
- Modify: `backend/backends/real_robot_backend.py`
- Modify: `config/safety_limits.yaml`
- Modify: `agents/policy/validation_pipeline.py`
- Test: `tests/backend/test_safety_guard.py`
- Test: `tests/backend/test_emergency_stop_priority.py`

- [ ] **Step 1: Add failing tests for workspace/speed violations and E-stop preemption**
- [ ] **Step 2: Implement pre-dispatch guard checks**
- [ ] **Step 3: Implement highest-priority E-stop path**
- [ ] **Step 4: Re-run tests and verify pass**
- [ ] **Step 5: Commit**

### Task P3-3: Real-Mode AuthZ and Audit

**Files:**
- Create: `backend/api/auth.py`
- Modify: `backend/api/agent_ws.py`
- Modify: `backend/services/trace_store.py`
- Modify: `frontend/src/components/SettingsPanel.tsx`
- Test: `tests/backend/test_real_mode_authz.py`
- Test: `tests/backend/test_audit_integrity.py`

- [ ] **Step 1: Add failing authz/audit tests**
- [ ] **Step 2: Implement role checks (`viewer/operator/approver/admin`)**
- [ ] **Step 3: Enforce token requirement in real mode**
- [ ] **Step 4: Persist operator identity in trace/audit logs**
- [ ] **Step 5: Re-run tests and verify pass**
- [ ] **Step 6: Commit**

---

## Cross-Phase Verification Gates

- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/backend -q`
- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests -q`
- [ ] `bash scripts/start_dev.sh --headless --backend` smoke run
- [ ] Frontend build: `cd frontend && npm run build`
- [ ] For P3: real-robot smoke checklist (connect, home, single-step, estop, recover)

---

## Release Milestones

- [ ] `v0.4-unified-mainline` (P0 complete)
- [ ] `v0.5-sim-debugger` (P1 complete)
- [ ] `v0.6-task-closed-loop` (P2 complete)
- [ ] `v0.7-real-robot-beta` (P3 complete)

---

## Definition of Done

- [ ] Single natural-language task can execute through one authoritative pipeline.
- [ ] Execution is fully observable with structured real-time events and trace replay.
- [ ] Simulation debugging supports step/pause/resume/abort and stable recovery.
- [ ] Real robot can be controlled through the same protocol with safety and approval gates.
- [ ] Real-mode operations are authenticated and auditable end-to-end.
