#!/usr/bin/env bash
#
# Start llama-server for vision (Qwen3-VL). Run this in a separate terminal
# before running the Python motion capture driver (capture_frame.py).
#
# Requires: llama.cpp built with Metal (scripts/build_llama_cpp.sh).
#
# Model files: Qwen3VL-2B-Instruct-Q4_K_M.gguf and mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf
# (or set MODEL_PATH / MMPROJ_PATH / LLAMA_CPP_DIR / MODELS_DIR).
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$PROJECT_ROOT/llama.cpp}"
MODELS_DIR="${MODELS_DIR:-$PROJECT_ROOT}"

# Default GGUF paths (under project root or MODELS_DIR)
MODEL_PATH="${MODEL_PATH:-$MODELS_DIR/Qwen3VL-2B-Instruct-Q4_K_M.gguf}"
MMPROJ_PATH="${MMPROJ_PATH:-$MODELS_DIR/mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf}"
PORT="${PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-2048}"
NGL="${NGL:-99}"

SERVER="$LLAMA_CPP_DIR/build/bin/llama-server"
if [[ ! -x "$SERVER" ]]; then
  echo "Error: llama-server not found at $SERVER"
  echo "Build first: scripts/build_llama_cpp.sh"
  exit 1
fi

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "Error: Model not found: $MODEL_PATH"
  echo "Download with: python download_qwen3vl_gguf.py"
  exit 1
fi
if [[ ! -f "$MMPROJ_PATH" ]]; then
  echo "Error: MMProj not found: $MMPROJ_PATH"
  echo "Download with: python download_qwen3vl_gguf.py"
  exit 1
fi

echo "Starting llama-server (Metal, port $PORT)..."
echo "  Model:  $MODEL_PATH"
echo "  MMProj: $MMPROJ_PATH"
echo "  URL:    http://localhost:$PORT/completion (native) or /v1/chat/completions (OAI-compatible)"
echo "Press Ctrl+C to stop."
echo ""

exec "$SERVER" \
  -m "$MODEL_PATH" \
  --mmproj "$MMPROJ_PATH" \
  --port "$PORT" \
  -ngl "$NGL" \
  --jinja \
  --ctx-size "$CTX_SIZE"

