#!/bin/bash
# Comprehensive debug script for llama-server startup

echo "=========================================="
echo "Llama Server Startup Debug"
echo "=========================================="
echo ""

cd /home/nexus/Argos_Chatgpt

echo "1. Checking binary..."
LLAMA_BIN="/home/nexus/rocm/py311-tor290/bin/llama-server"
if [ -f "$LLAMA_BIN" ]; then
    echo "✓ Binary file exists"
    if [ -x "$LLAMA_BIN" ]; then
        echo "✓ Binary is executable"
    else
        echo "❌ Binary is not executable"
        ls -la "$LLAMA_BIN"
    fi
else
    echo "❌ Binary file not found: $LLAMA_BIN"
fi

echo ""
echo "2. Checking model file..."
MODEL_FILE="models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
if [ -f "$MODEL_FILE" ]; then
    echo "✓ Model file exists"
    ls -lh "$MODEL_FILE"
else
    echo "❌ Model file not found: $MODEL_FILE"
fi

echo ""
echo "3. Checking directories..."
echo "LOGS: $(pwd)/logs/"
echo "PIDS: $(pwd)/.pids/"
mkdir -p logs .pids

echo ""
echo "4. Cleaning up..."
rm -f .pids/super_reader.pid .pids/governance.pid
echo "✓ PID files cleaned"

echo ""
echo "5. Testing binary execution..."
if [ -x "$LLAMA_BIN" ]; then
    echo "Testing with --help..."
    timeout 5s "$LLAMA_BIN" --help > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ Binary can execute --help"
    else
        echo "❌ Binary failed to execute --help"
    fi
else
    echo "❌ Cannot test - binary not executable"
fi

echo ""
echo "6. Testing with minimal CPU-only command..."
if [ -x "$LLAMA_BIN" ] && [ -f "$MODEL_FILE" ]; then
    echo "Starting server with CPU only for 5 seconds..."
    export LD_LIBRARY_PATH="/home/nexus/rocm/py311-tor290/bin:$LD_LIBRARY_PATH"
    export HIP_VISIBLE_DEVICES="0"

    timeout 5s "$LLAMA_BIN" \
        --model "$MODEL_FILE" \
        --host 0.0.0.0 \
        --port 8080 \
        --ctx-size 4096 \
        --n-gpu-layers 0 \
        --threads 4 \
        --parallel 1 \
        --log-disable \
        > logs/super_reader_test.log 2>&1 &

    PID=$!
    echo "Process started with PID: $PID"

    sleep 2

    if kill -0 $PID 2>/dev/null; then
        echo "✓ Process is running"
        kill $PID
        echo "✓ Process terminated successfully"
    else
        echo "❌ Process failed to start"
        echo "Log output:"
        cat logs/super_reader_test.log
    fi
else
    echo "❌ Cannot test - missing binary or model"
fi

echo ""
echo "=========================================="
echo "Debug complete"
echo "=========================================="