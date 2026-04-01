#!/usr/bin/env bash
# Start Jackrong Qwen3.5-9B Claude Opus reasoning distilled GGUF via llama.cpp llama-server.
# Prefers CUDA build (build-cuda, NGL=99); falls back to CPU (build, NGL=0).

set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/media/hzm/data_disk/EmbodiedAgentsSys/models/qwen3.5-9b-claude-distilled-v2-gguf}"
LLAMA_CPP_ROOT="${LLAMA_CPP_ROOT:-/media/hzm/data_disk/llama.cpp}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"

if [[ -z "${LLAMA_BIN_DIR:-}" ]]; then
  if [[ -x "${LLAMA_CPP_ROOT}/build-cuda/bin/llama-server" ]]; then
    LLAMA_BIN_DIR="${LLAMA_CPP_ROOT}/build-cuda/bin"
    NGL="${NGL:-99}"
  else
    LLAMA_BIN_DIR="${LLAMA_CPP_ROOT}/build/bin"
    NGL="${NGL:-0}"
  fi
else
  NGL="${NGL:-0}"
fi

GGUF="${MODEL_DIR}/Qwen3.5-9B.Q4_K_M.gguf"
MMPROJ="${MODEL_DIR}/mmproj-BF16.gguf"

if [[ ! -f "$GGUF" ]]; then
  echo "Missing: $GGUF"
  echo "Download with: hf download Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF Qwen3.5-9B.Q4_K_M.gguf --local-dir $MODEL_DIR"
  exit 1
fi
if [[ ! -f "$MMPROJ" ]]; then
  echo "Missing: $MMPROJ"
  exit 1
fi

if [[ ! -x "${LLAMA_BIN_DIR}/llama-server" ]]; then
  echo "Missing executable: ${LLAMA_BIN_DIR}/llama-server"
  echo "Rebuild CPU: bash scripts/rebuild_llama_cpu.sh"
  echo "Or GPU: bash scripts/rebuild_llama_cuda.sh"
  exit 1
fi

if [[ "${NGL}" != "0" ]] && [[ ! -f "${LLAMA_BIN_DIR}/libggml-cuda.so" ]]; then
  echo "警告: NGL=${NGL} 但 ${LLAMA_BIN_DIR} 下无 libggml-cuda.so（非 CUDA 构建），请改用 NGL=0 或运行 scripts/rebuild_llama_cuda.sh" >&2
fi

exec "${LLAMA_BIN_DIR}/llama-server" \
  -m "$GGUF" \
  --mmproj "$MMPROJ" \
  --host "$HOST" \
  --port "$PORT" \
  --jinja \
  -ngl "$NGL" \
  -c 8192 \
  --reasoning-format deepseek \
  "$@"
