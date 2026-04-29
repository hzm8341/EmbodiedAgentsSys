#!/usr/bin/env bash
# =============================================================================
# EmbodiedAgentsSys 手动测试启动脚本
#
# 用法:
#   bash scripts/start_dev.sh              # 启动后端(含MuJoCo viewer) + 前端
#   bash scripts/start_dev.sh --headless   # 启动后端(无viewer,仅终端) + 前端
#   bash scripts/start_dev.sh --backend    # 仅启动后端
#   bash scripts/start_dev.sh --frontend   # 仅启动前端
#   bash scripts/start_dev.sh --dashboard  # 使用 web-dashboard 作为前端
#
# 退出: Ctrl+C 同时关闭所有进程
# =============================================================================
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="$PROJECT_ROOT/.backend.log"
VUER_LOG="$PROJECT_ROOT/.vuer.log"
FRONTEND_LOG="$PROJECT_ROOT/.frontend.log"

HEADLESS=0
ONLY_BACKEND=0
ONLY_FRONTEND=0
DASHBOARD_FRONTEND=0
FRONTEND_DIR="$PROJECT_ROOT/frontend"
FRONTEND_URL="http://localhost:5173"
VUER_PORT=8012
VUER_URL="https://vuer.ai?ws=ws://localhost:8012"

for arg in "$@"; do
    case "$arg" in
        --headless)  HEADLESS=1 ;;
        --backend)   ONLY_BACKEND=1 ;;
        --frontend)  ONLY_FRONTEND=1 ;;
        --dashboard) DASHBOARD_FRONTEND=1 ;;
    esac
done

if [[ $DASHBOARD_FRONTEND -eq 1 ]]; then
    FRONTEND_DIR="$PROJECT_ROOT/web-dashboard"
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}正在关闭所有进程...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    echo -e "${GREEN}已退出${NC}"
}
trap cleanup EXIT INT TERM

cd "$PROJECT_ROOT"

# ── 打印标题 ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         EmbodiedAgentsSys  —  开发调试启动          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo -e "  项目目录: ${PROJECT_ROOT}"
echo ""

# ── 前置检查 ──────────────────────────────────────────────────────────────────
if ! python3 -c "import mujoco, fastapi, uvicorn" 2>/dev/null; then
    echo -e "${YELLOW}警告: 缺少 Python 依赖，请先执行:${NC}"
    echo "  pip install mujoco fastapi uvicorn websockets"
fi

if [[ $ONLY_FRONTEND -eq 0 ]]; then
    URDF="assets/eyoubot/eu_ca_describtion_lbs6.urdf"
    if [[ ! -f "$URDF" ]]; then
        echo -e "${YELLOW}警告: URDF 文件不存在: $URDF${NC}"
    fi
fi

start_vuer() {
    if [[ $ONLY_FRONTEND -eq 1 ]]; then
        return 0
    fi

    if ! python3 -c "import vuer" 2>/dev/null; then
        echo -e "${YELLOW}警告: 缺少 Vuer 依赖，URDF 页面将无法加载 3D 视图${NC}"
        echo "  pip install -r vuer_server/requirements.txt"
        return 0
    fi

    if fuser "${VUER_PORT}/tcp" &>/dev/null 2>&1; then
        echo -e "${CYAN}  → 端口 ${VUER_PORT} 被占用，正在清理...${NC}"
        fuser -k "${VUER_PORT}/tcp" 2>/dev/null || true
        sleep 1
    fi

    echo -e "${CYAN}→ 启动 Vuer URDF 视图服务...${NC}"
    (cd "$PROJECT_ROOT" && python3 vuer_server/server.py --host 0.0.0.0 --port "$VUER_PORT") > "$VUER_LOG" 2>&1 &
    PIDS+=($!)
    echo -e "  Vuer PID: ${PIDS[-1]}"
    echo -e "  日志文件: $VUER_LOG"

    echo -ne "  等待 Vuer 启动"
    for i in $(seq 1 20); do
        if curl -sf --max-time 1 "http://127.0.0.1:${VUER_PORT}/static/assets/eyoubot/eu_ca_describtion_lbs6.urdf" &>/dev/null; then
            VUER_URL="https://vuer.ai?ws=ws://localhost:${VUER_PORT}"
            echo ""
            echo -e "  ${GREEN}✓ Vuer 已就绪 (${i}s)${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [[ $i -eq 20 ]]; then
            echo ""
            echo -e "  ${YELLOW}⚠ Vuer 启动超时，请查看日志: tail -f $VUER_LOG${NC}"
        fi
    done
}

# ── 启动后端 ──────────────────────────────────────────────────────────────────
start_backend() {
    local viewer_env=""
    if [[ $HEADLESS -eq 1 ]]; then
        viewer_env="NO_MUJOCO_VIEWER=1"
        echo -e "${CYAN}→ 启动后端 (无头模式，无 MuJoCo 窗口)...${NC}"
    else
        echo -e "${CYAN}→ 启动后端 (含 MuJoCo 仿真窗口)...${NC}"
    fi

    # viewer 模式不加 --reload：GLFW 在 uvicorn fork 的子进程中无法正常初始化 X11
    # 清理残留的 8000 端口进程，避免端口冲突导致 viewer 闪退
    if fuser 8000/tcp &>/dev/null 2>&1; then
        echo -e "${CYAN}  → 端口 8000 被占用，正在清理...${NC}"
        fuser -k 8000/tcp 2>/dev/null || true
        sleep 1
    fi

    local reload_flag="--reload"
    if [[ $HEADLESS -eq 0 ]]; then
        reload_flag=""
    fi

    eval "env $viewer_env python3 -m uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        $reload_flag \
        --log-level info" > "$BACKEND_LOG" 2>&1 &
    PIDS+=($!)

    echo -e "  后端 PID: ${PIDS[-1]}"
    echo -e "  日志文件: $BACKEND_LOG"

    # 等待后端就绪（最多 20 秒）
    echo -ne "  等待后端启动"
    for i in $(seq 1 20); do
        if curl -sf --max-time 1 "http://127.0.0.1:8000/health" &>/dev/null; then
            echo ""
            echo -e "  ${GREEN}✓ 后端已就绪 (${i}s)${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [[ $i -eq 20 ]]; then
            echo ""
            echo -e "  ${YELLOW}⚠ 后端启动超时，请查看日志: tail -f $BACKEND_LOG${NC}"
        fi
    done
}

# ── 启动前端 ──────────────────────────────────────────────────────────────────
start_frontend() {
    if [[ ! -d "$FRONTEND_DIR" ]]; then
        echo -e "${YELLOW}错误: 前端目录不存在: $FRONTEND_DIR${NC}"
        return 1
    fi

    if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
        echo -e "${CYAN}→ 安装前端依赖 (npm install)...${NC}"
        (cd "$FRONTEND_DIR" && npm install --silent 2>&1 | tail -3)
    fi

    echo -e "${CYAN}→ 启动前端开发服务器...${NC}"
    (cd "$FRONTEND_DIR" && npm run dev) > "$FRONTEND_LOG" 2>&1 &
    PIDS+=($!)
    echo -e "  前端 PID: ${PIDS[-1]}"
    echo -e "  日志文件: $FRONTEND_LOG"

    # 等待 Vite 就绪
    echo -ne "  等待前端启动"
    for i in $(seq 1 20); do
        if grep -q "Local:" "$FRONTEND_LOG" 2>/dev/null; then
            FRONTEND_URL="$(grep "Local:" "$FRONTEND_LOG" | tail -1 | sed -E 's/.*(http:\/\/[^ ]+).*/\1/')"
            [[ -z "$FRONTEND_URL" ]] && FRONTEND_URL="http://localhost:5173"
            echo ""
            echo -e "  ${GREEN}✓ 前端已就绪 (${i}s)${NC}"
            break
        fi
        if curl -sf --max-time 1 "http://127.0.0.1:5173" &>/dev/null || curl -sf --max-time 1 "http://127.0.0.1:5174" &>/dev/null; then
            if curl -sf --max-time 1 "http://127.0.0.1:5174" &>/dev/null; then
                FRONTEND_URL="http://localhost:5174"
            else
                FRONTEND_URL="http://localhost:5173"
            fi
            echo ""
            echo -e "  ${GREEN}✓ 前端已就绪 (${i}s)${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [[ $i -eq 20 ]]; then
            echo ""
            echo -e "  ${YELLOW}⚠ 前端启动超时，请查看日志: tail -f $FRONTEND_LOG${NC}"
        fi
    done
}

# ── 执行启动 ──────────────────────────────────────────────────────────────────
[[ $ONLY_FRONTEND -eq 0 ]] && start_vuer
[[ $ONLY_FRONTEND -eq 0 ]] && start_backend
[[ $ONLY_BACKEND  -eq 0 ]] && start_frontend

# ── 打印访问地址 ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${BLUE}━━━ 服务地址 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  后端 API    : ${GREEN}http://localhost:8000${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  API 文档    : ${GREEN}http://localhost:8000/docs${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  健康检查    : ${GREEN}http://localhost:8000/health${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  URDF 视图   : ${GREEN}${VUER_URL}${NC}"
[[ $ONLY_BACKEND  -eq 0 ]] && echo -e "  前端调试器  : ${GREEN}${FRONTEND_URL}${NC}"
echo ""
echo -e "${BOLD}${BLUE}━━━ 手动测试清单 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}1. 基础连接${NC}"
echo -e "     → 打开 ${FRONTEND_URL}"
echo -e "     → 健康检查返回 ${GREEN}{\"status\":\"ok\"}${NC}"
echo ""
echo -e "  ${BOLD}2. 双后端可见${NC}"
echo -e "     → GET /api/backends 同时包含 mujoco 与 ros2_gazebo"
echo -e "     → 页面数据源下拉可见这两个后端"
echo ""
echo -e "  ${BOLD}3. 实时切换数据源${NC}"
echo -e "     → 在页面切换 mujoco ↔ ros2_gazebo"
echo -e "     → 无需刷新页面，连接不中断，场景 backend 字段同步变化"
echo ""
echo -e "  ${BOLD}4. 后端特有能力暴露${NC}"
echo -e "     → GET /api/backends/ros2_gazebo/capabilities 含 backend_specific_commands"
echo -e "     → POST /api/backends/ros2_gazebo/commands/publish_topic 返回 unavailable"
echo ""
echo -e "  ${BOLD}5. 快速 API 验证 (新终端)${NC}"
echo -e "     curl http://localhost:8000/health"
echo -e "     curl http://localhost:8000/api/backends | python3 -m json.tool"
echo -e "     curl -X POST http://localhost:8000/api/backends/select \\"
echo -e "       -H 'Content-Type: application/json' \\"
echo -e "       -d '{\"backend_id\":\"ros2_gazebo\"}'"
echo -e "     curl http://localhost:8000/api/view/scene | python3 -m json.tool"
echo -e "     curl http://localhost:8000/api/backends/ros2_gazebo/capabilities | python3 -m json.tool"
echo -e "     curl -X POST http://localhost:8000/api/backends/ros2_gazebo/commands/publish_topic \\"
echo -e "       -H 'Content-Type: application/json' \\"
echo -e "       -d '{\"params\":{\"topic\":\"/joint_states\"}}'"
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  按 ${BOLD}Ctrl+C${NC} 停止所有服务"
echo ""

# ── 保持进程运行，实时输出后端日志 ─────────────────────────────────────────────
if [[ ${#PIDS[@]} -gt 0 ]]; then
    echo -e "${CYAN}→ 后端日志 (实时):${NC}"
    echo -e "  (前端日志: tail -f $FRONTEND_LOG)"
    echo ""
    tail -f "$BACKEND_LOG" &
    PIDS+=($!)
    wait "${PIDS[0]}" 2>/dev/null || true
fi
