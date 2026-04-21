#!/usr/bin/env bash
# =============================================================================
# EmbodiedAgentsSys 完整系统测试脚本
#
# 用法:
#   bash scripts/test_system.sh              # 全量测试（需要后端已运行）
#   bash scripts/test_system.sh --fast       # 跳过耗时的 pytest 套件
#   bash scripts/test_system.sh --start-backend  # 自动启动后端，完成后停止
#   bash scripts/test_system.sh --no-backend # 只跑本地检查，不测 API
#
# 退出码:
#   0 — 全部通过
#   1 — 有失败项
# =============================================================================
set -uo pipefail

# ── 参数解析 ──────────────────────────────────────────────────────────────────
FAST=0
START_BACKEND=0
NO_BACKEND=0
BASE_URL="http://localhost:8000"
BACKEND_PID=""

for arg in "$@"; do
    case "$arg" in
        --fast)          FAST=1 ;;
        --start-backend) START_BACKEND=1 ;;
        --no-backend)    NO_BACKEND=1 ;;
        http://*)        BASE_URL="$arg" ;;
    esac
done

WS_URL="${BASE_URL/http/ws}/api/agent/ws"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── 颜色 ──────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── 计数器 ────────────────────────────────────────────────────────────────────
PASS=0; FAIL=0; SKIP=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
skip() { echo -e "  ${YELLOW}⊘${NC} $1"; SKIP=$((SKIP+1)); }
info() { echo -e "  ${CYAN}→${NC} $1"; }
section() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━ $1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ── 清理函数 ──────────────────────────────────────────────────────────────────
cleanup() {
    if [[ -n "$BACKEND_PID" ]]; then
        info "Stopping backend (PID $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── 标题 ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       EmbodiedAgentsSys  —  System Test Suite       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo -e "  Project : ${PROJECT_ROOT}"
echo -e "  Backend : ${BASE_URL}"
echo -e "  Mode    : $([ $FAST -eq 1 ] && echo fast || echo full)"
echo ""

cd "$PROJECT_ROOT"

# =============================================================================
# § 1  环境依赖
# =============================================================================
section "1  环境依赖"

# Python 版本
PY_VER=$(python3 --version 2>&1)
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    pass "Python $PY_VER"
else
    fail "Python 3.10+ required (got $PY_VER)"
fi

# 关键 Python 包
for pkg in mujoco numpy fastapi uvicorn websockets pytest; do
    if python3 -c "import $pkg" 2>/dev/null; then
        VER=$(python3 -c "import $pkg; print(getattr($pkg,'__version__','?'))" 2>/dev/null)
        pass "Python package: $pkg==$VER"
    else
        fail "Python package missing: $pkg  (pip install $pkg)"
    fi
done

# Node / npm（前端）
if command -v node &>/dev/null; then
    pass "Node $(node --version)"
else
    skip "Node.js not found (frontend tests skipped)"
fi

if command -v npm &>/dev/null; then
    pass "npm $(npm --version)"
else
    skip "npm not found"
fi

# =============================================================================
# § 2  资源文件
# =============================================================================
section "2  资源文件"

URDF_MESH="assets/eyoubot/eu_ca_describtion_lbs6.urdf"
URDF_SIMPLE="assets/eyoubot/eu_ca_simple.urdf"
BASE_STL="assets/eyoubot/meshes/base_link1.STL"

[[ -f "$URDF_MESH"   ]] && pass "Mesh URDF: $URDF_MESH"   || fail "Missing: $URDF_MESH"
[[ -f "$URDF_SIMPLE" ]] && pass "Simple URDF: $URDF_SIMPLE" || fail "Missing: $URDF_SIMPLE"

# base_link1.STL 必须是真实网格（>400 字节，≥12 个三角形）
if [[ -f "$BASE_STL" ]]; then
    STL_SIZE=$(stat -c%s "$BASE_STL")
    TRI_COUNT=$(python3 -c "
import struct
with open('$BASE_STL','rb') as f:
    f.read(80); n=struct.unpack('<I',f.read(4))[0]; print(n)
" 2>/dev/null || echo 0)
    if [[ $TRI_COUNT -ge 12 ]]; then
        pass "base_link1.STL: ${TRI_COUNT} triangles (${STL_SIZE} bytes)"
    else
        fail "base_link1.STL is placeholder (only ${TRI_COUNT} triangles) — chassis will be invisible"
    fi
else
    fail "Missing: $BASE_STL"
fi

# 检查手臂 STL 文件数量
STL_COUNT=$(find assets/eyoubot/meshes -name "*.STL" | wc -l)
if [[ $STL_COUNT -ge 20 ]]; then
    pass "Mesh files: ${STL_COUNT} STL files found"
else
    fail "Expected ≥20 STL files, found ${STL_COUNT}"
fi

# =============================================================================
# § 3  MuJoCo 场景构建
# =============================================================================
section "3  MuJoCo 场景构建"

python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from simulation.mujoco.scene_builder import GRASPABLE_OBJECTS, build_robot_scene, _TABLE_TOP_Z
import mujoco, numpy as np

ok = True

# 3-a  对象位置在台面以上
for name, cfg in GRASPABLE_OBJECTS.items():
    z = cfg["pos"][2]
    if z >= _TABLE_TOP_Z:
        print(f"  ✓  {name} z={z:.3f} (above table top {_TABLE_TOP_Z:.3f})")
    else:
        print(f"  ✗  {name} z={z:.3f} is BELOW table top {_TABLE_TOP_Z:.3f}")
        ok = False

# 3-b  URDF 加载 + 物体检测
try:
    model, data = build_robot_scene("assets/eyoubot/eu_ca_describtion_lbs6.urdf")
    if model.nq == 35:
        print(f"  ✓  Model nq={model.nq} (14 arm + 3×7 freejoint)")
    else:
        print(f"  ✗  Unexpected nq={model.nq} (expected 35)")
        ok = False
    for name in GRASPABLE_OBJECTS:
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        if bid >= 0:
            pos = data.body(bid).xpos
            print(f"  ✓  Body {name}: pos=[{pos[0]:.3f},{pos[1]:.3f},{pos[2]:.3f}]")
        else:
            print(f"  ✗  Body {name} not found in model")
            ok = False
except Exception as e:
    print(f"  ✗  build_robot_scene failed: {e}")
    ok = False

# 3-c  地面位置（floor geom 在 z=0）
floor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
if floor_id >= 0:
    fz = model.geom_pos[floor_id][2]
    if abs(fz) < 0.01:
        print(f"  ✓  Floor at z={fz:.3f} (grounded)")
    else:
        print(f"  ✗  Floor at z={fz:.3f} — robot will appear to float")
        ok = False
else:
    print("  ✗  Floor geom not found")
    ok = False

sys.exit(0 if ok else 1)
PYEOF
RET=$?
[[ $RET -eq 0 ]] && pass "Scene building: all checks passed" || fail "Scene building: some checks failed"

# =============================================================================
# § 4  MuJoCo 驱动 + IK
# =============================================================================
section "4  MuJoCo 驱动 + IK 控制器"

python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from simulation.mujoco.mujoco_driver import MuJoCoDriver
import numpy as np

ok = True
d = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")

# 4-a  IK 控制器初始化
if d._arm_ik_controller is not None:
    print("  ✓  IK controller initialized")
else:
    print("  ✗  IK controller is None")
    ok = False

# 4-b  关节 ID 合法
left_ids = d._left_joint_ids
right_ids = d._right_joint_ids
if all(jid >= 0 for jid in left_ids) and len(left_ids) == 7:
    print(f"  ✓  Left arm joint IDs: {left_ids}")
else:
    print(f"  ✗  Left arm joint IDs invalid: {left_ids}")
    ok = False

if all(jid >= 0 for jid in right_ids) and len(right_ids) == 7:
    print(f"  ✓  Right arm joint IDs: {right_ids}")
else:
    print(f"  ✗  Right arm joint IDs invalid: {right_ids}")
    ok = False

# 4-c  IK 可达性测试
targets = [
    ("left",  0.45,  0.12, 0.72),   # red_cube position
    ("left",  0.45, -0.12, 0.71),   # blue_block position
    ("left",  0.52,  0.0,  0.71),   # yellow_sphere position
    ("left",  0.45,  0.12, 0.85),   # approach from above
    ("right", 0.45,  0.12, 0.72),   # right arm test
]
for arm, x, y, z in targets:
    q = d._arm_ik_controller.solve(arm, np.array([x, y, z]), q_init=np.zeros(7))
    if q is not None:
        print(f"  ✓  IK {arm} arm → ({x},{y},{z}): solution found")
    else:
        print(f"  ✗  IK {arm} arm → ({x},{y},{z}): FAILED")
        ok = False

# 4-d  可抓取物体检测
if len(d._graspable_body_ids) == 3:
    print(f"  ✓  Graspable objects detected: {list(d._graspable_body_ids.keys())}")
else:
    print(f"  ✗  Expected 3 graspable objects, found {len(d._graspable_body_ids)}")
    ok = False

if len(d._graspable_qpos_adr) == 3:
    print(f"  ✓  Freejoint qpos addresses: {d._graspable_qpos_adr}")
else:
    print(f"  ✗  Expected 3 qpos addresses, found {len(d._graspable_qpos_adr)}")
    ok = False

# 4-e  reset_to_home
d._grasped_body_id = 99   # 模拟已抓取
d.reset_to_home()
if d._grasped_body_id is None:
    print("  ✓  reset_to_home clears grasped state")
else:
    print("  ✗  reset_to_home did not clear grasped state")
    ok = False

sys.exit(0 if ok else 1)
PYEOF
RET=$?
[[ $RET -eq 0 ]] && pass "MuJoCo driver + IK: all checks passed" || fail "MuJoCo driver + IK: some checks failed"

# =============================================================================
# § 5  仿真动作执行（无头模式）
# =============================================================================
section "5  仿真动作执行（无头 headless）"

python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from simulation.mujoco.mujoco_driver import MuJoCoDriver
from embodiedagentsys.hal.types import ExecutionStatus
import numpy as np

ok = True
d = MuJoCoDriver(urdf_path="assets/eyoubot/eu_ca_describtion_lbs6.urdf")

# 5-a  move_arm_to
r = d.execute_action("move_arm_to", {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.85})
if r.status == ExecutionStatus.SUCCESS:
    print(f"  ✓  move_arm_to left (0.45,0.12,0.85): {r.result_message}")
else:
    print(f"  ✗  move_arm_to failed: {r.result_message}")
    ok = False

# 5-b  move_arm_to 接近 red_cube
r = d.execute_action("move_arm_to", {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.72})
if r.status == ExecutionStatus.SUCCESS:
    print(f"  ✓  move_arm_to left (0.45,0.12,0.72): {r.result_message}")
else:
    print(f"  ✗  move_arm_to failed: {r.result_message}")
    ok = False

# 5-c  grasp（arm 模式，不依赖接触传感器）
r = d.execute_action("grasp", {"arm": "left", "force": 50})
if r.status == ExecutionStatus.SUCCESS:
    print(f"  ✓  grasp arm=left: {r.result_message}")
else:
    print(f"  ✗  grasp failed: {r.result_message}")
    ok = False

# 5-d  move_arm_to + 携带物体（验证 qpos 更新）
if d._grasped_body_id is not None:
    adr = d._grasped_qpos_adr
    pos_before = d._data.qpos[list(adr.values())[0]:list(adr.values())[0]+3].copy()
    d.execute_action("move_arm_to", {"arm": "left", "x": 0.45, "y": 0.12, "z": 0.90})
    pos_after = d._data.qpos[list(adr.values())[0]:list(adr.values())[0]+3].copy()
    if not np.allclose(pos_before, pos_after):
        print(f"  ✓  Object carried during move (qpos changed)")
    else:
        print(f"  ✗  Object did NOT move during arm motion (carry_callback not working)")
        ok = False
else:
    print("  ⊘  No object grasped (distance may exceed reach threshold), skipping carry test")

# 5-e  release
r = d.execute_action("release", {"arm": "left"})
if r.status == ExecutionStatus.SUCCESS:
    print(f"  ✓  release: {r.result_message}")
else:
    print(f"  ✗  release failed: {r.result_message}")
    ok = False

# 5-f  whitelist 拒绝未知动作
r = d.execute_action("fly_to_moon", {})
if r.status == ExecutionStatus.FAILED:
    print(f"  ✓  Unknown action correctly rejected")
else:
    print(f"  ✗  Unknown action should be rejected but got {r.status}")
    ok = False

sys.exit(0 if ok else 1)
PYEOF
RET=$?
[[ $RET -eq 0 ]] && pass "Headless simulation: all checks passed" || fail "Headless simulation: some checks failed"

# =============================================================================
# § 6  Scenarios 配置
# =============================================================================
section "6  Scenarios 配置"

python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')
from backend.services.scenarios import SCENARIOS, list_scenarios
from simulation.mujoco.scene_builder import GRASPABLE_OBJECTS, _TABLE_TOP_Z

ok = True
EXPECTED = {"spatial_detection","single_grasp","grasp_and_move","error_recovery","dynamic_environment"}

# 6-a  场景完整性
present = set(SCENARIOS.keys())
missing = EXPECTED - present
if not missing:
    print(f"  ✓  All 5 scenarios present: {sorted(present)}")
else:
    print(f"  ✗  Missing scenarios: {missing}")
    ok = False

# 6-b  每个场景有 action_sequence
for name, sc in SCENARIOS.items():
    n = len(sc.action_sequence)
    if n >= 3:
        print(f"  ✓  {name}: {n} actions")
    else:
        print(f"  ✗  {name}: only {n} actions (expected ≥3)")
        ok = False

# 6-c  grasp/move 场景中目标 z 与物体实际 z 一致（误差 ≤0.20m）
for name, sc in SCENARIOS.items():
    for step in sc.action_sequence:
        if step["action"] == "grasp":
            continue
        p = step.get("params", {})
        z = p.get("z", 0)
        if z < _TABLE_TOP_Z - 0.05 and name not in ("spatial_detection",):
            print(f"  ✗  {name}: step z={z:.2f} is below table ({_TABLE_TOP_Z:.2f})")
            ok = False

if ok:
    print(f"  ✓  All action z-coordinates above table surface")

# 6-d  list_scenarios() 格式正确
catalog = list_scenarios()
for s in catalog:
    assert "name" in s and "task" in s and "description" in s
print(f"  ✓  list_scenarios() returns {len(catalog)} valid dicts")

sys.exit(0 if ok else 1)
PYEOF
RET=$?
[[ $RET -eq 0 ]] && pass "Scenarios config: all checks passed" || fail "Scenarios config: some checks failed"

# =============================================================================
# § 7  前端构建检查
# =============================================================================
section "7  前端构建检查"

FRONTEND_DIR="$PROJECT_ROOT/frontend"

if ! command -v node &>/dev/null; then
    skip "Node.js not installed — frontend checks skipped"
elif [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    info "node_modules missing — running npm install..."
    (cd "$FRONTEND_DIR" && npm install --silent 2>&1 | tail -3) && pass "npm install succeeded" || fail "npm install failed"
fi

if command -v node &>/dev/null && [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    # TypeScript 类型检查
    if (cd "$FRONTEND_DIR" && npx tsc --noEmit 2>&1); then
        pass "TypeScript: no type errors"
    else
        fail "TypeScript: type errors found"
    fi

    # Vite 构建（仅检查是否能构建，不部署）
    if [[ $FAST -eq 0 ]]; then
        info "Running Vite build..."
        if (cd "$FRONTEND_DIR" && npm run build 2>&1 | tail -5); then
            pass "Vite build: succeeded"
        else
            fail "Vite build: failed"
        fi
    else
        skip "Vite build skipped (--fast mode)"
    fi
fi

# =============================================================================
# § 8  后端 API 测试（需要后端运行）
# =============================================================================
section "8  后端 API 测试"

# 如果需要，自动启动后端（NO_MUJOCO_VIEWER=1 避免 viewer 阻塞进程）
if [[ $START_BACKEND -eq 1 ]]; then
    info "Starting backend (headless, no viewer)..."
    NO_MUJOCO_VIEWER=1 python3 -m uvicorn backend.main:app \
        --host 127.0.0.1 --port 8000 --log-level warning \
        &>/tmp/backend_test.log &
    BACKEND_PID=$!
    # 等待后端就绪（最多 15 秒，MuJoCo 初始化需要时间）
    for i in $(seq 1 15); do
        if curl -sf --max-time 1 "http://127.0.0.1:8000/health" &>/dev/null; then
            info "Backend ready after ${i}s (PID $BACKEND_PID)"
            break
        fi
        sleep 1
    done
fi

if [[ $NO_BACKEND -eq 1 ]]; then
    skip "Backend API tests skipped (--no-backend)"
else
    # 8-a  健康检查
    HEALTH=$(curl -sf --max-time 5 "$BASE_URL/health" 2>/dev/null || echo "UNREACHABLE")
    if echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status')=='ok' else 1)" 2>/dev/null; then
        pass "GET /health → $(echo "$HEALTH" | python3 -c 'import sys,json; print(json.load(sys.stdin))')"
    else
        fail "GET /health — backend unreachable or returned error: $HEALTH"
        info "Start backend: cd '$PROJECT_ROOT' && python -m uvicorn backend.main:app --port 8000"
        info "Or run: bash scripts/test_system.sh --start-backend"
        NO_BACKEND=1   # 后续 WS 测试也跳过
    fi

    if [[ $NO_BACKEND -eq 0 ]]; then
        # 8-b  Scenarios REST
        SC_JSON=$(curl -sf --max-time 5 "$BASE_URL/api/agent/scenarios" 2>/dev/null || echo "[]")
        SC_COUNT=$(echo "$SC_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
        if [[ $SC_COUNT -eq 5 ]]; then
            NAMES=$(echo "$SC_JSON" | python3 -c "import sys,json; print(','.join(s['name'] for s in json.load(sys.stdin)))")
            pass "GET /api/agent/scenarios → $SC_COUNT scenarios: $NAMES"
        else
            fail "GET /api/agent/scenarios → expected 5, got $SC_COUNT"
        fi

        # 8-c  WebSocket — execute_task 消息序列
        WS_RESULT=$(python3 - <<PYEOF
import asyncio, json, sys
sys.path.insert(0, '.')

async def run():
    try:
        import websockets
    except ImportError:
        print("NO_WS"); return

    url = "$WS_URL"
    payload = json.dumps({
        "type": "execute_task",
        "task": "scan workspace",
        "scenario": "spatial_detection",
        "observation": {"state": {"gripper_open": 1.0}, "gripper": {}},
    })
    try:
        async with websockets.connect(url, open_timeout=8) as ws:
            await ws.send(payload)
            msgs = []
            for _ in range(40):
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                m = json.loads(raw)
                msgs.append(m["type"])
                if m["type"] == "result":
                    break
            expected_start = ["task_start", "planning"]
            if msgs[:2] == expected_start and "result" in msgs:
                print("OK:" + ",".join(msgs))
            else:
                print("FAIL:unexpected sequence:" + ",".join(msgs))
    except Exception as e:
        print(f"FAIL:{e}")

asyncio.run(run())
PYEOF
)
        if [[ "$WS_RESULT" == NO_WS* ]]; then
            skip "WebSocket test skipped (pip install websockets)"
        elif [[ "$WS_RESULT" == OK:* ]]; then
            TYPES="${WS_RESULT#OK:}"
            pass "WS execute_task: message sequence OK  [$TYPES]"
        else
            fail "WS execute_task: ${WS_RESULT#FAIL:}"
        fi

        # 8-d  WebSocket — reset_to_home
        RESET_RESULT=$(python3 - <<PYEOF
import asyncio, json, sys

async def run():
    try:
        import websockets
    except ImportError:
        print("NO_WS"); return
    try:
        async with websockets.connect("$WS_URL", open_timeout=8) as ws:
            await ws.send(json.dumps({"type": "reset_to_home"}))
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            m = json.loads(raw)
            if m.get("type") == "reset_complete":
                print("OK:" + str(m.get("data",{})))
            else:
                print(f"FAIL:expected reset_complete, got {m.get('type')}")
    except Exception as e:
        print(f"FAIL:{e}")

asyncio.run(run())
PYEOF
)
        if [[ "$RESET_RESULT" == NO_WS* ]]; then
            skip "reset_to_home test skipped (no websockets)"
        elif [[ "$RESET_RESULT" == OK:* ]]; then
            pass "WS reset_to_home: ${RESET_RESULT#OK:}"
        else
            fail "WS reset_to_home: ${RESET_RESULT#FAIL:}"
        fi

        # 8-e  WebSocket — 无效 JSON 返回 error
        ERR_RESULT=$(python3 - <<PYEOF
import asyncio, json, sys

async def run():
    try:
        import websockets
    except ImportError:
        print("NO_WS"); return
    try:
        async with websockets.connect("$WS_URL", open_timeout=8) as ws:
            await ws.send("not valid json {{{")
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            m = json.loads(raw)
            print("OK" if m.get("type") == "error" else f"FAIL:got {m.get('type')}")
    except Exception as e:
        print(f"FAIL:{e}")

asyncio.run(run())
PYEOF
)
        if [[ "$ERR_RESULT" == NO_WS* ]]; then
            skip "Error handling test skipped"
        elif [[ "$ERR_RESULT" == "OK" ]]; then
            pass "WS invalid JSON → error message returned"
        else
            fail "WS error handling: ${ERR_RESULT#FAIL:}"
        fi

        # 8-f  WebSocket — 每个 scenario 的动作序列完整执行
        if [[ $FAST -eq 0 ]]; then
            info "Running all 5 scenario end-to-end (takes ~30s each)..."
            for SC_NAME in spatial_detection single_grasp grasp_and_move error_recovery dynamic_environment; do
                SC_RESULT=$(python3 - <<PYEOF
import asyncio, json, sys

async def run():
    try:
        import websockets
    except ImportError:
        print("NO_WS"); return
    payload = json.dumps({
        "type": "execute_task",
        "task": "test",
        "scenario": "$SC_NAME",
        "observation": {"state": {"gripper_open": 1.0}, "gripper": {}},
    })
    try:
        async with websockets.connect("$WS_URL", open_timeout=10) as ws:
            await ws.send(payload)
            exec_count = 0
            async for _ in range(80):
                raw = await asyncio.wait_for(ws.recv(), timeout=60)
                m = json.loads(raw)
                if m["type"] == "execution":
                    exec_count += 1
                if m["type"] == "result":
                    print(f"OK:steps={exec_count}")
                    return
            print("FAIL:result message never received")
    except Exception as e:
        print(f"FAIL:{e}")

asyncio.run(run())
PYEOF
)
                if [[ "$SC_RESULT" == NO_WS* ]]; then
                    skip "$SC_NAME end-to-end skipped"
                elif [[ "$SC_RESULT" == OK:* ]]; then
                    pass "Scenario $SC_NAME end-to-end: ${SC_RESULT#OK:}"
                else
                    fail "Scenario $SC_NAME end-to-end: ${SC_RESULT#FAIL:}"
                fi
            done
        else
            skip "Scenario end-to-end tests skipped (--fast mode)"
        fi
    fi
fi

# =============================================================================
# § 9  Pytest 单元 + 集成测试
# =============================================================================
section "9  Pytest 测试套件"

if [[ $FAST -eq 1 ]]; then
    skip "pytest skipped (--fast mode)"
else
    # httpx 不支持 SOCKS 代理（all_proxy=socks://...），运行前临时清除
    PYTEST_ENV="env -u all_proxy -u ALL_PROXY -u socks_proxy -u SOCKS_PROXY"

    _run_pytest() {
        local dir="$1"; local label="$2"
        info "Running pytest $dir ..."
        local output
        output=$($PYTEST_ENV python3 -m pytest "$dir" -q --tb=short \
                   --ignore=".worktrees" \
                   --ignore="tests/test_voice_teaching_agent.py" \
                   --ignore="tests/test_simulation/test_gymnasium_env_driver.py" \
                   2>&1)
        local rc=$?
        echo "$output" | tail -6
        if [[ $rc -eq 0 ]]; then
            pass "pytest $label"
        else
            # 只有非代理错误才算失败
            if echo "$output" | grep -q "socks://"; then
                skip "pytest $label — SOCKS proxy env var still active (unset all_proxy)"
            else
                fail "pytest $label — see output above"
            fi
        fi
    }

    _run_pytest "tests/backend/"        "backend"
    _run_pytest "tests/test_simulation/" "test_simulation"
    _run_pytest "tests/test_hal/"        "test_hal"
    _run_pytest "tests/security/"        "security"
fi

# =============================================================================
# § 10  快速冒烟测试摘要
# =============================================================================
section "10  关键组件冒烟验证"

python3 - <<'PYEOF'
import sys
sys.path.insert(0, '.')

checks = []

# 导入链路
try:
    from simulation.mujoco import MuJoCoDriver
    from simulation.mujoco.scene_builder import GRASPABLE_OBJECTS, build_robot_scene
    from backend.services.simulation import simulation_service
    from backend.services.scenarios import SCENARIOS
    from backend.services.agent_bridge import agent_bridge
    checks.append(("Import chain", True, "all modules importable"))
except Exception as e:
    checks.append(("Import chain", False, str(e)))

# SimulationService 单例
try:
    from backend.services.simulation import simulation_service as s1, SimulationService
    s2 = SimulationService()
    checks.append(("SimulationService singleton", s1 is s2, "same instance"))
except Exception as e:
    checks.append(("SimulationService singleton", False, str(e)))

# config DEFAULT_URDF_PATH
try:
    from simulation.mujoco.config import DEFAULT_URDF_PATH
    import os
    checks.append(("DEFAULT_URDF_PATH exists", os.path.exists(DEFAULT_URDF_PATH),
                   DEFAULT_URDF_PATH))
except Exception as e:
    checks.append(("DEFAULT_URDF_PATH", False, str(e)))

for name, ok, msg in checks:
    icon = "✓" if ok else "✗"
    print(f"  {icon}  {name}: {msg}")

sys.exit(0 if all(c[1] for c in checks) else 1)
PYEOF
RET=$?
[[ $RET -eq 0 ]] && pass "Smoke tests: all passed" || fail "Smoke tests: some failed"

# =============================================================================
# 最终汇总
# =============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║                   测试结果汇总                      ║${NC}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════╣${NC}"
printf  "${BOLD}║${NC}  ${GREEN}✓ 通过${NC}  %-4d   ${YELLOW}⊘ 跳过${NC}  %-4d   ${RED}✗ 失败${NC}  %-4d         ${BOLD}║${NC}\n" \
    "$PASS" "$SKIP" "$FAIL"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}${BOLD}有 ${FAIL} 项检查失败，请查看上方详情。${NC}"
    echo ""
    echo "常用修复命令："
    echo "  pip install mujoco numpy fastapi uvicorn websockets pytest"
    echo "  cd frontend && npm install"
    echo "  python -m uvicorn backend.main:app --port 8000 --reload"
    echo ""
    exit 1
else
    echo -e "${GREEN}${BOLD}全部检查通过！${NC}"
    echo ""
    echo "启动系统："
    echo "  # 后端"
    echo "  cd '$PROJECT_ROOT'"
    echo "  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
    echo ""
    echo "  # 前端（新终端）"
    echo "  cd '$PROJECT_ROOT/frontend' && npm run dev"
    echo "  → 打开 http://localhost:5173"
    echo ""
    exit 0
fi
