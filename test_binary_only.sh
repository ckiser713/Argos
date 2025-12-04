#!/bin/bash
# Test just the binary startup without model

echo "=== Binary Startup Test ==="

# Set environment
export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

echo "Testing binary startup (no model, 2 second timeout)..."

# Try to start without model - should fail quickly but show it can start
timeout 2s ~/rocm/py311-tor290/bin/llama-server \
    --host 127.0.0.1 \
    --port 9999 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 2 \
    --parallel 1 \
    --log-disable \
    2>&1 | head -5

EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 124 ]; then
    echo "⚠️ Binary started but didn't exit cleanly (expected with no model)"
    echo "✅ Binary can start - model loading might be the issue"
elif [ $EXIT_CODE -eq 0 ]; then
    echo "❌ Binary exited cleanly (unexpected without model)"
else
    echo "❌ Binary failed to start with exit code $EXIT_CODE"
fi

echo ""
echo "Next: Try with model but shorter timeout..."