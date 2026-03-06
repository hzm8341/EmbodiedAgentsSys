#!/bin/bash
# Fara-7B vLLM服务器启动脚本
# 版本: v1.0
# 日期: 2026-03-03
# 说明: 启动Fara-7B模型的vLLM服务器，提供OpenAI兼容API

set -e  # 遇到错误退出

# ============================================================
# 配置参数
# ============================================================

# 模型配置
MODEL="microsoft/Fara-7B"
PORT=5000
DTYPE="auto"
GPU_UTIL="0.9"

# 路径配置
FARA_DIR="/media/hzm/data_disk/fara"
LOG_DIR="${FARA_DIR}/logs"
LOG_FILE="${LOG_DIR}/vllm_server_$(date +%Y%m%d_%H%M%S).log"

# vLLM参数
TENSOR_PARALLEL_SIZE=1
MAX_MODEL_LEN=4096
ENFORCE_EAGER=true  # 启用兼容模式

# ============================================================
# 初始化环境
# ============================================================

echo "=" * 60
echo "Fara-7B vLLM服务器启动脚本"
echo "=" * 60

# 检查fara目录
if [ ! -d "$FARA_DIR" ]; then
    echo "✗ 错误: fara目录不存在: $FARA_DIR"
    exit 1
fi

# 创建日志目录
mkdir -p "$LOG_DIR"
echo "✓ 日志目录: $LOG_DIR"

# 检查虚拟环境
VENV_PYTHON="${FARA_DIR}/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "✗ 错误: 虚拟环境不存在: $VENV_PYTHON"
    echo "请确保已在fara目录中设置好虚拟环境"
    exit 1
fi

echo "✓ 虚拟环境: $VENV_PYTHON"

# ============================================================
# 检查端口占用
# ============================================================

echo "检查端口 $PORT 占用情况..."

if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用，尝试关闭现有进程..."

    # 获取占用端口的进程
    PID=$(lsof -ti:$PORT)
    echo "占用进程PID: $PID"

    # 询问是否关闭
    read -p "是否关闭进程 $PID? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -9 $PID 2>/dev/null
        sleep 2
        echo "✓ 已关闭进程 $PID"
    else
        echo "✗ 用户取消操作"
        exit 1
    fi
else
    echo "✓ 端口 $PORT 可用"
fi

# ============================================================
# 检查GPU状态
# ============================================================

echo "检查GPU状态..."

if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits)
    echo "GPU信息:"
    echo "$GPU_INFO" | while IFS=',' read -r name total free; do
        echo "  - $name: 总内存 ${total}MB, 可用内存 ${free}MB"
    done
else
    echo "⚠️  未找到nvidia-smi，确保GPU驱动已安装"
fi

# ============================================================
# 启动vLLM服务器
# ============================================================

echo "=" * 60
echo "启动 Fara-7B vLLM服务器..."
echo "=" * 60
echo "模型: $MODEL"
echo "端口: $PORT"
echo "数据类型: $DTYPE"
echo "GPU利用率: $GPU_UTIL"
echo "日志文件: $LOG_FILE"
echo "=" * 60

# 激活虚拟环境并启动vLLM
cd "$FARA_DIR"

echo "激活虚拟环境并启动vLLM服务器..."
echo "详细日志请查看: $LOG_FILE"
echo

# 启动命令
source .venv/bin/activate

# 构建vLLM命令
VLLM_CMD="vllm serve \"$MODEL\" \
  --port $PORT \
  --dtype $DTYPE \
  --tensor-parallel-size $TENSOR_PARALLEL_SIZE \
  --gpu-memory-utilization $GPU_UTIL \
  --max-model-len $MAX_MODEL_LEN"

# 添加可选参数
if [ "$ENFORCE_EAGER" = "true" ]; then
    VLLM_CMD="$VLLM_CMD --enforce-eager"
fi

echo "执行命令: $VLLM_CMD"
echo

# 执行命令，输出到日志文件和终端
eval $VLLM_CMD 2>&1 | tee "$LOG_FILE"

# ============================================================
# 启动后检查
# ============================================================

echo
echo "=" * 60
echo "启动完成"
echo "=" * 60

# 检查进程
sleep 3
if pgrep -f "vllm serve" > /dev/null; then
    echo "✓ vLLM服务器正在运行"
    echo "进程ID: $(pgrep -f "vllm serve")"
else
    echo "✗ vLLM服务器可能启动失败，请检查日志: $LOG_FILE"
    exit 1
fi

# 检查API端点
sleep 2
echo "检查API端点..."
if curl -s "http://127.0.0.1:$PORT/v1/models" > /dev/null 2>&1; then
    echo "✓ API端点响应正常"
    echo "服务地址: http://127.0.0.1:$PORT"
    echo "模型列表: http://127.0.0.1:$PORT/v1/models"
else
    echo "⚠️  API端点暂时无响应，可能还在加载中"
    echo "请等待1-2分钟后检查: curl http://127.0.0.1:$PORT/v1/models"
fi

echo
echo "=" * 60
echo "使用说明"
echo "=" * 60
echo "1. 停止服务: pkill -f \"vllm serve\""
echo "2. 查看日志: tail -f \"$LOG_FILE\""
echo "3. 测试API: curl http://127.0.0.1:$PORT/v1/models"
echo "4. EmbodiedAgentsSys配置: 使用host=127.0.0.1, port=$PORT"
echo "=" * 60

# 保持脚本运行，直到用户中断
echo "按 Ctrl+C 停止服务器和日志显示..."
echo "日志输出:"

# 持续显示日志尾部
tail -f "$LOG_FILE"