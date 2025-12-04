#!/bin/bash
# Ultra-minimal server start - avoid GPU issues

echo "=== Ultra-Minimal Llama Server Start ==="
echo "Completely disabling GPU to avoid D-state hangs..."
echo ""

PROJECT_ROOT="/home/nexus/Argos_Chatgpt"
LLAMA_BIN="$HOME/rocm/py311-tor290/bin/llama-server"
MODEL_SUPER="$PROJECT_ROOT/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
MODEL_GOV="$PROJECT_ROOT/models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# Completely disable GPU to avoid ROCm issues
export HIP_VISIBLE_DEVICES=""
export HSA_ENABLE_SDMA="0"
export ROCR_VISIBLE_DEVICES=""
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"

echo "GPU completely disabled (HIP_VISIBLE_DEVICES='')"
echo "Starting with minimal settings..."
echo ""

echo "Starting SUPER_READER (minimal config)..."
"$LLAMA_BIN" \
    --model "$MODEL_SUPER" \
    --host 0.0.0.0 \
    --port 8080 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 1 \
    --parallel 1 \
    --log-format text \
    > "$LOG_DIR/super_reader.log" 2>&1 &

SUPER_PID=$!
echo $SUPER_PID > "$PID_DIR/super_reader.pid"
echo "SUPER_READER started with PID $SUPER_PID"

sleep 3

echo "Starting GOVERNANCE (minimal config)..."
"$LLAMA_BIN" \
    --model "$MODEL_GOV" \
    --host 0.0.0.0 \
    --port 8081 \
    --ctx-size 1024 \
    --n-gpu-layers 0 \
    --threads 1 \
    --parallel 1 \
    --log-format text \
    > "$LOG_DIR/governance.log" 2>&1 &

GOV_PID=$!
echo $GOV_PID > "$PID_DIR/governance.pid"
echo "GOVERNANCE started with PID $GOV_PID"

echo ""
echo "Waiting 5 seconds for startup..."
sleep 5

echo "Checking process status..."
ps aux | grep llama-server | grep -v grep

echo ""
echo "Testing health endpoints..."
curl -s --max-time 2 http://localhost:8080/health || echo "SUPER_READER: No response"
curl -s --max-time 2 http://localhost:8081/health || echo "GOVERNANCE: No response"

echo ""
echo "Check logs:"
echo "tail -f logs/super_reader.log"
echo "tail -f logs/governance.log"