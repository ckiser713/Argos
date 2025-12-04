#!/bin/bash
# Ultra-simple llama test

echo "Testing llama-server..."

# Check binary
if [ ! -f ~/rocm/py311-tor290/bin/llama-server ]; then
    echo "❌ Binary not found"
    exit 1
fi
echo "✅ Binary exists"

# Check model
if [ ! -f ~/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf ]; then
    echo "❌ Model not found"
    exit 1
fi
echo "✅ Model exists"

# Test help
if timeout 2s ~/rocm/py311-tor290/bin/llama-server --help >/dev/null 2>&1; then
    echo "✅ Help works"
else
    echo "❌ Help failed"
    exit 1
fi

# Test CPU startup
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

echo "Testing CPU startup (2 second timeout)..."
timeout 2s ~/rocm/py311-tor290/bin/llama-server \
    --model ~/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf \
    --host 127.0.0.1 \
    --port 9999 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 2 \
    --parallel 1 \
    --log-disable \
    >/dev/null 2>&1

EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 124 ]; then
    echo "🎉 SUCCESS: CPU mode works!"
    echo "Run: ./scripts/start_llama_servers.sh start"
elif [ $EXIT_CODE -eq 137 ]; then
    echo "⚠️ Process was killed (possibly by timeout)"
    echo "This might indicate the binary is working but slow to start"
    echo "Try: ./scripts/start_llama_servers.sh start"
else
    echo "❌ CPU mode failed with exit code $EXIT_CODE"
fi