#!/bin/bash
# Manual execution script for ROCm reingestion
# Run this step by step if the automated script fails

set -e

echo "=========================================="
echo "Manual Cortex ROCm Reingestion"
echo "=========================================="
echo ""

cd /home/nexus/Argos_Chatgpt

echo "Step 1: Check if vLLM image exists..."
if [ -f "/home/nexus/rocm/py311-tor290/images/vllm_rocm_image.tar" ]; then
    echo "✓ Image file found"
    ls -lh /home/nexus/rocm/py311-tor290/images/vllm_rocm_image.tar
else
    echo "❌ Image file not found at /home/nexus/rocm/py311-tor290/images/vllm_rocm_image.tar"
    exit 1
fi

echo ""
echo "Step 2: Load vLLM image into Docker..."
docker load -i /home/nexus/rocm/py311-tor290/images/vllm_rocm_image.tar

echo ""
echo "Step 3: Verify image was loaded..."
docker images | grep vllm

echo ""
echo "Step 4: Stop any existing services..."
docker compose -f ops/docker-compose.strix.yml down || true
./scripts/start_llama_servers.sh stop || true

echo ""
echo "Step 5: Start Docker services..."
docker compose -f ops/docker-compose.strix.yml up -d qdrant postgres n8n

echo ""
echo "Step 6: Start vLLM service..."
docker compose -f ops/docker-compose.strix.yml up -d inference-vllm

echo ""
echo "Step 7: Start llama.cpp servers..."
./scripts/start_llama_servers.sh start

echo ""
echo "Step 8: Check status..."
echo "Docker services:"
docker ps --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "llama.cpp servers:"
./scripts/start_llama_servers.sh status

echo ""
echo "=========================================="
echo "Manual reingestion complete!"
echo "=========================================="