#!/usr/bin/env bash
# Rebuild llama.cpp (CPU/OpenMP only). Use when build/ is corrupted or llama-server is missing.
# Never run: rm build/bin  (use full rm -rf build). If rm fails, stop llama-server first: pkill -f llama-server

set -euo pipefail
ROOT="${LLAMA_CPP_ROOT:-/media/hzm/data_disk/llama.cpp}"
cd "$ROOT"
pkill -f "${ROOT}/build/bin/llama-server" 2>/dev/null || true
sleep 1
chmod -R u+w build 2>/dev/null || true
rm -rf build
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j"$(nproc)"
test -x build/bin/llama-server
echo "OK: ${ROOT}/build/bin/llama-server"
