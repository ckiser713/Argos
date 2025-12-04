#!/bin/bash
# Minimal test - just check basics

echo "=== Minimal Llama Test ==="

# Check files exist
echo "Checking files..."
[ -f ~/rocm/py311-tor290/bin/llama-server ] && echo "✅ Binary exists" || echo "❌ Binary missing"
[ -f ~/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf ] && echo "✅ Model exists" || echo "❌ Model missing"

# Test binary directly
echo "Testing binary..."
~/rocm/py311-tor290/bin/llama-server --help >/dev/null 2>&1 &
PID=$!
sleep 1
if kill -0 $PID 2>/dev/null; then
    echo "✅ Binary runs (killed after 1s)"
    kill $PID 2>/dev/null
else
    wait $PID 2>/dev/null
    echo "❌ Binary failed or exited"
fi

echo "Done."