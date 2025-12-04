#!/bin/bash
# Test model loading without server

echo "=== Model Loading Test ==="

MODEL="/home/nexus/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
LLAMA_BIN="$HOME/rocm/py311-tor290/bin/llama-server"

if [ ! -f "$MODEL" ]; then
    echo "❌ Model not found"
    exit 1
fi

echo "Testing model loading (no server, 10 second timeout)..."

# Try to load model without starting server
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES=""

timeout 10s "$LLAMA_BIN" \
    --model "$MODEL" \
    --ctx-size 512 \
    --n-gpu-layers 0 \
    --threads 1 \
    --parallel 1 \
    --log-format text \
    --verbose \
    2>&1 | head -20

EXIT_CODE=$?
echo ""
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 124 ]; then
    echo "✅ Model loaded successfully (timed out as expected)"
elif [ $EXIT_CODE -eq 0 ]; then
    echo "⚠️ Model loaded but exited (unexpected)"
else
    echo "❌ Model loading failed"
fi