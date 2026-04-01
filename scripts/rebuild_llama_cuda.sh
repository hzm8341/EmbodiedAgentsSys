#!/usr/bin/env bash
# Build llama.cpp with CUDA for RTX 30xx (sm_86). Requires conda env llama-cuda:
#   conda create -y -n llama-cuda -c nvidia cuda-toolkit=12.4 cmake ninja

set -euo pipefail
ROOT="${LLAMA_CPP_ROOT:-/media/hzm/data_disk/llama.cpp}"
ENV_NAME="${LLAMA_CUDA_ENV:-llama-cuda}"
cd "$ROOT"

pkill -f "${ROOT}/build-cuda/bin/llama-server" 2>/dev/null || true
sleep 1

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

cmake -B build-cuda \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DCUDAToolkit_ROOT="$CONDA_PREFIX"

cmake --build build-cuda --config Release -j"$(nproc)"

test -x build-cuda/bin/llama-server
echo "OK GPU: ${ROOT}/build-cuda/bin/llama-server"
