#!/usr/bin/env bash
# =============================================================================
# EmbodiedAgentsSys 手动测试启动脚本
#
# 用法:
#   bash scripts/start_dev.sh              # 启动后端(含MuJoCo viewer) + 前端
#   bash scripts/start_dev.sh --headless   # 启动后端(无viewer,仅终端) + 前端
#   bash scripts/start_dev.sh --backend    # 仅启动后端
#   bash scripts/start_dev.sh --frontend   # 仅启动前端
#
# 退出: Ctrl+C 同时关闭所有进程
# =============================================================================
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="$PROJECT_ROOT/.backend.log"
FRONTEND_LOG="$PROJECT_ROOT/.frontend.log"

HEADLESS=0
ONLY_BACKEND=0
ONLY_FRONTEND=0

for arg in "$@"; do
    case "$arg" in
        --headless)  HEADLESS=1 ;;
        --backend)   ONLY_BACKEND=1 ;;
        --frontend)  ONLY_FRONTEND=1 ;;
    esac
done

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
    if [[ ! -d "$PROJECT_ROOT/frontend/node_modules" ]]; then
        echo -e "${CYAN}→ 安装前端依赖 (npm install)...${NC}"
        (cd "$PROJECT_ROOT/frontend" && npm install --silent 2>&1 | tail -3)
    fi

    echo -e "${CYAN}→ 启动前端开发服务器...${NC}"
    (cd "$PROJECT_ROOT/frontend" && npm run dev) > "$FRONTEND_LOG" 2>&1 &
    PIDS+=($!)
    echo -e "  前端 PID: ${PIDS[-1]}"
    echo -e "  日志文件: $FRONTEND_LOG"

    # 等待 Vite 就绪
    echo -ne "  等待前端启动"
    for i in $(seq 1 15); do
        if curl -sf --max-time 1 "http://127.0.0.1:5173" &>/dev/null; then
            echo ""
            echo -e "  ${GREEN}✓ 前端已就绪 (${i}s)${NC}"
            break
        fi
        echo -n "."
        sleep 1
        if [[ $i -eq 15 ]]; then
            echo ""
            echo -e "  ${YELLOW}⚠ 前端启动超时，请查看日志: tail -f $FRONTEND_LOG${NC}"
        fi
    done
}

# ── 执行启动 ──────────────────────────────────────────────────────────────────
[[ $ONLY_FRONTEND -eq 0 ]] && start_backend
[[ $ONLY_BACKEND  -eq 0 ]] && start_frontend

# ── 打印访问地址 ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${BLUE}━━━ 服务地址 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  后端 API    : ${GREEN}http://localhost:8000${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  API 文档    : ${GREEN}http://localhost:8000/docs${NC}"
[[ $ONLY_FRONTEND -eq 0 ]] && echo -e "  健康检查    : ${GREEN}http://localhost:8000/health${NC}"
[[ $ONLY_BACKEND  -eq 0 ]] && echo -e "  前端调试器  : ${GREEN}http://localhost:5173${NC}"
echo ""
echo -e "${BOLD}${BLUE}━━━ 手动测试清单 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}1. 基础连接${NC}"
echo -e "     → 打开 http://localhost:5173"
echo -e "     → 页面右上角应显示 ${GREEN}Connected${NC}"
echo -e "     → 顶部有三个 Tab: 🤖 Agent调试器 / 💬 聊天控制 / 📷 相机"
echo ""
echo -e "  ${BOLD}2. Tab: Agent 调试器${NC}"
echo -e "     → 场景列表显示 5 个预设场景:"
echo -e "       spatial_detection / single_grasp / grasp_and_move"
echo -e "       error_recovery / dynamic_environment"
echo -e "     → 点击场景后点击 Execute，MuJoCo 窗口中观察机器人运动"
echo -e "     → 点击 ${YELLOW}Home${NC} 按钮复位机器人"
echo -e "     → Execution Monitor 实时显示事件流"
echo ""
echo -e "  ${BOLD}3. Tab: 聊天控制${NC}"
echo -e "     → 填入 DeepSeek API Key (sk-...)"
echo -e "     → 输入自然语言指令，例如:"
echo -e "       「将左臂移动到 x=0.3 y=0 z=0.5」"
echo -e "       「抓取前方物体」"
echo -e "     → 观察机器人响应和工具调用详情"
echo ""
echo -e "  ${BOLD}4. Tab: 相机${NC}"
echo -e "     → 点击「开始」按钮接入摄像头画面"
echo -e "     → 点击「截图」保存当前帧"
echo ""
echo -e "  ${BOLD}5. 快速 API 验证 (新终端)${NC}"
echo -e "     curl http://localhost:8000/health"
echo -e "     curl http://localhost:8000/api/agent/scenarios | python3 -m json.tool"
echo -e "     curl -X POST http://localhost:8000/api/chat \\"
echo -e "       -H 'Content-Type: application/json' \\"
echo -e "       -d '{\"message\":\"将左臂移动到x=0.3\",\"history\":[]}'"
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
