#!/bin/bash
# Quick test script for llama servers

echo "=== Quick Llama Server Test ==="
echo ""

# Check if binary exists
LLAMA_BIN="$HOME/rocm/py311-tor290/bin/llama-server"
if [ ! -f "$LLAMA_BIN" ]; then
    echo "❌ Binary not found: $LLAMA_BIN"
    exit 1
fi
echo "✅ Binary exists"

# Check model
MODEL="$HOME/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
if [ ! -f "$MODEL" ]; then
    echo "❌ Model not found: $MODEL"
    exit 1
fi
echo "✅ Model exists"

# Set environment
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"
export HSA_ENABLE_SDMA="0"
export ROCR_VISIBLE_DEVICES="0"
export HIP_FORCE_DEV_KERNARG="1"
export AMD_LOG_LEVEL="0"

echo "Environment set"
echo ""

# Test binary
echo "Testing binary..."
if timeout 3s "$LLAMA_BIN" --version >/dev/null 2>&1; then
    echo "✅ Binary test passed"
else
    echo "❌ Binary test failed"
    exit 1
fi

# Test CPU startup
echo "Testing CPU startup..."
timeout 5s "$LLAMA_BIN" \
    --model "$MODEL" \
    --host 127.0.0.1 \
    --port 9999 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 2 \
    --parallel 1 \
    --log-disable \
    >/dev/null 2>&1

if [ $? -eq 124 ]; then
    echo "✅ CPU mode works (timed out as expected)"
else
    echo "❌ CPU mode failed"
    exit 1
fi

echo ""
echo "=== Ready to start servers ==="
echo "Run: ./scripts/start_llama_servers.sh start"