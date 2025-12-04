#!/bin/bash
# Debug script for llama-server startup issues

echo "=== Llama Server Debug ==="
echo ""

# Check if binary exists and is executable
LLAMA_BIN="/home/nexus/rocm/py311-tor290/bin/llama-server"
if [ ! -x "$LLAMA_BIN" ]; then
    echo "❌ Binary not found or not executable: $LLAMA_BIN"
    ls -la "$LLAMA_BIN"
    exit 1
else
    echo "✓ Binary exists and is executable: $LLAMA_BIN"
fi

# Check model file
MODEL_FILE="/home/nexus/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ Model file not found: $MODEL_FILE"
    exit 1
else
    echo "✓ Model file exists: $MODEL_FILE"
    ls -lh "$MODEL_FILE"
fi

# Check directories
echo ""
echo "Directories:"
echo "LOGS: /home/nexus/Argos_Chatgpt/logs/"
echo "PIDS: /home/nexus/Argos_Chatgpt/.pids/"
mkdir -p /home/nexus/Argos_Chatgpt/logs/
mkdir -p /home/nexus/Argos_Chatgpt/.pids/

# Try to run llama-server with minimal options to see if it starts
echo ""
echo "Testing llama-server startup..."
export LD_LIBRARY_PATH="/home/nexus/rocm/py311-tor290/bin:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

# Try with CPU only first
echo "Testing with CPU only (n-gpu-layers=0)..."
timeout 10s "$LLAMA_BIN" \
    --model "$MODEL_FILE" \
    --host 0.0.0.0 \
    --port 8080 \
    --ctx-size 4096 \
    --n-gpu-layers 0 \
    --threads 4 \
    --parallel 1 \
    --log-disable || echo "Process exited or timed out"

echo ""
echo "Debug complete."