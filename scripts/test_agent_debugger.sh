#!/usr/bin/env bash
# Manual test script for the Agent Debugger (backend + WebSocket)
# Usage: bash scripts/test_agent_debugger.sh [backend_url]

set -euo pipefail

BASE="${1:-http://localhost:8000}"
WS_URL="${BASE/http/ws}/api/agent/ws"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

echo "============================================"
echo " Agent Debugger — Manual Test"
echo " Backend: $BASE"
echo "============================================"
echo ""

# ── 1. Health check ─────────────────────────────────────────────────────────
info "1. Health check"
HEALTH=$(curl -sf "$BASE/health" 2>/dev/null || echo "{}")
if echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('status') in ('ok','healthy') else 1)" 2>/dev/null; then
    STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status'))")
    ok "GET /health → status=$STATUS"
else
    fail "GET /health did not return status=healthy (is the backend running?)"
    echo ""
    echo "  Start backend with:"
    echo "  cd /media/hzm/data_disk/EmbodiedAgentsSys"
    echo "  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
    echo ""
    exit 1
fi

# ── 2. Scenarios REST endpoint ───────────────────────────────────────────────
info "2. Scenarios list  (GET /api/agent/scenarios)"
SCENARIOS_JSON=$(curl -sf "$BASE/api/agent/scenarios")
echo "   Response: $SCENARIOS_JSON" | python3 -c "
import sys, json
raw = sys.stdin.read().replace('   Response: ', '', 1)
data = json.loads(raw)
names = {s['name'] for s in data}
expected = {'spatial_detection','single_grasp','grasp_and_move','error_recovery','dynamic_environment'}
missing = expected - names
if missing:
    print('MISSING: ' + str(missing))
    sys.exit(1)
print('All 5 scenarios present: ' + ', '.join(sorted(names)))
" && ok "All 5 scenarios returned" || fail "Scenarios endpoint missing expected entries"

# ── 3. WebSocket — single task (Python inline) ───────────────────────────────
info "3. WebSocket task execution  (ws /api/agent/ws)"

RESULT=$(python3 - <<'PYEOF'
import asyncio, json, sys

async def run():
    try:
        import websockets
    except ImportError:
        print("NO_WEBSOCKETS")
        return

    url = "ws://localhost:8000/api/agent/ws"
    payload = json.dumps({
        "type": "execute_task",
        "task": "pick up the red cube",
        "observation": {"state": {"gripper_open": 1.0}, "gripper": {"position": 0.04}},
        "max_steps": 2,
    })

    messages = []
    async with websockets.connect(url, open_timeout=5) as ws:
        await ws.send(payload)
        for _ in range(30):
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            messages.append(msg["type"])
            if msg["type"] == "result":
                break

    # Validate sequence
    if messages[0] != "task_start":
        print("FAIL:first message is not task_start")
        return
    if messages[1] != "planning":
        print("FAIL:second message is not planning")
        return
    if messages[-1] != "result":
        print("FAIL:last message is not result")
        return
    step_types = messages[2:-1]
    expected_block = ["reasoning", "execution", "learning"]
    for i in range(0, len(step_types), 3):
        if step_types[i:i+3] != expected_block:
            print(f"FAIL:step block {i//3} sequence wrong: {step_types[i:i+3]}")
            return
    print("OK:" + ",".join(messages))

asyncio.run(run())
PYEOF
)

if [[ "$RESULT" == NO_WEBSOCKETS* ]]; then
    info "  'websockets' package not installed; skipping live WS test"
    info "  Install with: pip install websockets"
elif [[ "$RESULT" == OK:* ]]; then
    TYPES="${RESULT#OK:}"
    ok "WebSocket message sequence: $TYPES"
elif [[ "$RESULT" == FAIL:* ]]; then
    fail "WebSocket sequence error: ${RESULT#FAIL:}"
else
    fail "WebSocket test failed: $RESULT"
fi

# ── 4. WebSocket — error handling ────────────────────────────────────────────
info "4. WebSocket error handling  (invalid JSON)"

ERR_RESULT=$(python3 - <<'PYEOF'
import asyncio, json, sys

async def run():
    try:
        import websockets
    except ImportError:
        print("NO_WEBSOCKETS")
        return

    async with websockets.connect("ws://localhost:8000/api/agent/ws", open_timeout=5) as ws:
        await ws.send("not json at all")
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        msg = json.loads(raw)
        if msg.get("type") == "error":
            print("OK")
        else:
            print(f"FAIL:expected error type, got {msg.get('type')}")

asyncio.run(run())
PYEOF
)

if [[ "$ERR_RESULT" == NO_WEBSOCKETS* ]]; then
    info "  Skipped (no websockets package)"
elif [[ "$ERR_RESULT" == "OK" ]]; then
    ok "Invalid JSON correctly returns error message"
else
    fail "Error handling: $ERR_RESULT"
fi

# ── 5. Automated test suite summary ─────────────────────────────────────────
echo ""
echo "============================================"
echo " Results: ${PASS} passed, ${FAIL} failed"
echo "============================================"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}Some checks failed. See messages above.${NC}"
    EXIT_CODE=1
else
    echo -e "${GREEN}All manual checks passed!${NC}"
    EXIT_CODE=0
fi

echo ""
echo "─── Full automated test suite ──────────────"
echo "  pytest tests/backend/ tests/integration/ -v"
echo ""
echo "─── Frontend ───────────────────────────────"
echo "  cd frontend && npm run dev"
echo "  Open http://localhost:5173"
echo "  Verify: green ● Connected badge"
echo "  Click a scenario → Execute → watch 4 layer cards fill in real-time"
echo ""

exit $EXIT_CODE
