#!/bin/bash
# Direct server start - bypass all testing

echo "=== Direct Llama Server Start ==="
echo "Bypassing all tests to avoid hangs..."
echo ""

PROJECT_ROOT="/home/nexus/Argos_Chatgpt"
LLAMA_BIN="$HOME/rocm/py311-tor290/bin/llama-server"
MODEL_SUPER="$PROJECT_ROOT/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
MODEL_GOV="$PROJECT_ROOT/models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# Set minimal environment - DISABLE GPU COMPLETELY
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES=""  # Empty string disables GPU
export HSA_ENABLE_SDMA="0"
export ROCR_VISIBLE_DEVICES=""  # Empty string disables GPU

echo "Starting SUPER_READER on port 8080..."
nohup "$LLAMA_BIN" \
    --model "$MODEL_SUPER" \
    --host 0.0.0.0 \
    --port 8080 \
    --ctx-size 4096 \
    --n-gpu-layers 0 \
    --threads 1 \
    --parallel 1 \
    --log-disable \
    > "$LOG_DIR/super_reader.log" 2>&1 &

SUPER_PID=$!
echo $SUPER_PID > "$PID_DIR/super_reader.pid"
echo "SUPER_READER started with PID $SUPER_PID"

sleep 2

echo "Starting GOVERNANCE on port 8081..."
nohup "$LLAMA_BIN" \
    --model "$MODEL_GOV" \
    --host 0.0.0.0 \
    --port 8081 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 1 \
    --parallel 1 \
    --log-disable \
    > "$LOG_DIR/governance.log" 2>&1 &

GOV_PID=$!
echo $GOV_PID > "$PID_DIR/governance.pid"
echo "GOVERNANCE started with PID $GOV_PID"

echo ""
echo "Servers starting... Check status with:"
echo "./scripts/start_llama_servers.sh --status"
echo ""
echo "Check logs:"
echo "tail -f logs/super_reader.log"
echo "tail -f logs/governance.log"