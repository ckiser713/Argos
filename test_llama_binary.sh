#!/bin/bash
# Simple test to check llama-server binary

echo "=== Llama Server Binary Test ==="
echo ""

# Check if binary exists
LLAMA_BIN="$HOME/rocm/py311-tor290/bin/llama-server"
if [ ! -f "$LLAMA_BIN" ]; then
    echo "❌ Binary not found: $LLAMA_BIN"
    exit 1
fi

echo "✅ Binary exists: $LLAMA_BIN"
echo "Size: $(ls -lh "$LLAMA_BIN" | awk '{print $5}')"
echo "Permissions: $(ls -l "$LLAMA_BIN" | awk '{print $1}')"
echo ""

# Check if executable
if [ ! -x "$LLAMA_BIN" ]; then
    echo "❌ Binary not executable"
    exit 1
fi

echo "✅ Binary is executable"
echo ""

# Set environment
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

echo "Environment:"
echo "  LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "  HIP_VISIBLE_DEVICES=$HIP_VISIBLE_DEVICES"
echo ""

# Test basic help
echo "Testing --help (should show usage):"
timeout 5s "$LLAMA_BIN" --help 2>&1 || echo "❌ Help command failed or timed out"
echo ""

# Test with minimal model loading (CPU only)
MODEL_PATH="/home/nexus/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found: $MODEL_PATH"
    exit 1
fi

echo "✅ Model exists: $MODEL_PATH"
echo ""

echo "Testing minimal startup (CPU only, 10 second timeout):"
timeout 10s "$LLAMA_BIN" \
    --model "$MODEL_PATH" \
    --host 127.0.0.1 \
    --port 9090 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 2 \
    --parallel 1 \
    --log-disable \
    2>&1

EXIT_CODE=$?
echo ""
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Server started successfully"
elif [ $EXIT_CODE -eq 124 ]; then
    echo "⚠️ Server started but was killed by timeout (this is expected)"
else
    echo "❌ Server failed to start"
fi