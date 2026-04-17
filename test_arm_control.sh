#!/bin/bash
# MuJoCo Arm Control 完整测试脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
    echo "清理进程..."
    pkill -f mujoco_arm_control_server 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "node.*web-dashboard" 2>/dev/null || true
    sleep 1
}

cleanup

echo "=========================================="
echo "1. 启动前端开发服务器 (http://localhost:5173)"
echo "=========================================="
cd /media/hzm/Data/EmbodiedAgentsSys/web-dashboard
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo "等待前端启动..."
for i in {1..10}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "前端就绪 (PID: $FRONTEND_PID)"
        break
    fi
    sleep 0.5
done

echo ""
echo "=========================================="
echo "2. 启动 MuJoCo 服务器 (http://localhost:8000)"
echo "=========================================="
python3 /media/hzm/Data/EmbodiedAgentsSys/examples/mujoco_arm_control_server.py > /tmp/mujoco_server.log 2>&1 &
SERVER_PID=$!

echo "等待 MuJoCo 服务器启动..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health | grep -q "ok"; then
        echo "MuJoCo 服务器就绪 (PID: $SERVER_PID)"
        break
    fi
    sleep 0.5
done

echo ""
echo "=========================================="
echo "测试 1: 左臂移动到 (0.1, 0, 0.2)"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/execute \
    -H "Content-Type: application/json" \
    -d '{"action":"move_arm_to","params":{"arm":"left","x":0.1,"y":0,"z":0.2}}'
echo

echo ""
echo "=========================================="
echo "测试 2: 右臂移动到 (0.1, 0, 0.2)"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/execute \
    -H "Content-Type: application/json" \
    -d '{"action":"move_arm_to","params":{"arm":"right","x":0.1,"y":0,"z":0.2}}'
echo

echo ""
echo "=========================================="
echo "测试 3: 左臂移动到 (0.5, 0.2, 0.4)"
echo "=========================================="
curl -s -X POST http://localhost:8000/api/execute \
    -H "Content-Type: application/json" \
    -d '{"action":"move_arm_to","params":{"arm":"left","x":0.5,"y":0.2,"z":0.4}}'
echo

echo ""
echo "=========================================="
echo "测试 4: 获取场景状态"
echo "=========================================="
curl -s http://localhost:8000/api/scene
echo

echo ""
echo "=========================================="
echo "所有服务已启动!"
echo "=========================================="
echo "前端界面: http://localhost:5173"
echo "MuJoCo Viewer: http://localhost:8000 (API)"
echo ""
echo "前端测试: 在聊天框输入 '将机器人左臂移动到 x=0.1 y=0 z=0.2'"
echo ""
echo "停止所有服务: pkill -f mujoco_arm_control; pkill -f vite"
echo "前端日志: tail -f /tmp/frontend.log"
echo "后端日志: tail -f /tmp/mujoco_server.log"