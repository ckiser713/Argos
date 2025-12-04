#!/bin/bash
# Verification script to check if ROCm reingestion was successful

echo "=========================================="
echo "Cortex ROCm Reingestion Verification"
echo "=========================================="
echo ""

echo "1. Checking Docker images..."
docker images | grep vllm || echo "❌ No vLLM images found"

echo ""
echo "2. Checking Docker containers..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(vllm|qdrant|postgres|n8n)" || echo "❌ Some containers not running"

echo ""
echo "3. Checking llama.cpp servers..."
for port in 8080 8081; do
    if curl -s "http://localhost:$port/health" | grep -q "ok"; then
        echo "✅ Port $port: HEALTHY"
    else
        echo "❌ Port $port: UNHEALTHY"
    fi
done

echo ""
echo "4. Checking vLLM service..."
if curl -s "http://localhost:8000/health" | grep -q "ok"; then
    echo "✅ vLLM: HEALTHY"
else
    echo "❌ vLLM: UNHEALTHY"
fi

echo ""
echo "5. Checking GPU acceleration..."
# Check if ROCm binaries are being used
if pgrep -f "llama-server" > /dev/null; then
    echo "✅ llama.cpp servers are running"
    ps aux | grep llama-server | grep -v grep | head -2
else
    echo "❌ No llama.cpp servers running"
fi

echo ""
echo "=========================================="
echo "Verification complete"
echo "=========================================="