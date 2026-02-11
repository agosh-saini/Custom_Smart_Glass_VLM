#!/usr/bin/env bash
#
# Clone and build llama.cpp with Metal support (Apple Silicon).
# Run from the project root or pass LLAMA_CPP_DIR.
# After building, start the vision server with: scripts/start_llama_server.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$PROJECT_ROOT/llama.cpp}"

echo "Project root: $PROJECT_ROOT"
echo "llama.cpp will be at: $LLAMA_CPP_DIR"

if [[ ! -d "$LLAMA_CPP_DIR" ]]; then
  echo "Cloning llama.cpp..."
  git clone https://github.com/ggml-org/llama.cpp "$LLAMA_CPP_DIR"
  cd "$LLAMA_CPP_DIR"
else
  echo "Using existing clone at $LLAMA_CPP_DIR"
  cd "$LLAMA_CPP_DIR"
  git pull --rebase || true
fi

echo "Configuring with Metal..."
cmake -B build -DGGML_METAL=ON

echo "Building (Release, -j8)..."
cmake --build build --config Release -j 8

echo "Done. Binary: $LLAMA_CPP_DIR/build/bin/llama-server"
echo "Start the vision server with: scripts/start_llama_server.sh"

