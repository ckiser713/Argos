#!/bin/bash
# Complete reingestion script for vLLM and llama.cpp from ROCm artifacts
# This script loads the vLLM image and starts all services

set -e

echo "=========================================="
echo "Cortex ROCm Reingestion Script"
echo "=========================================="
echo ""

# Configuration
VLLM_IMAGE_PATH="/home/nexus/rocm/py311-tor290/images/vllm_rocm_image.tar"
VLLM_IMAGE_NAME="vllm-rocm-gfx1151:complete"
PROJECT_ROOT="/home/nexus/Argos_Chatgpt"

cd "$PROJECT_ROOT"

echo "Step 1: Loading vLLM ROCm image..."
if [ -f "$VLLM_IMAGE_PATH" ]; then
    echo "Found image at: $VLLM_IMAGE_PATH"
    echo "Loading image into Docker..."
    docker load -i "$VLLM_IMAGE_PATH"
    echo "✓ Image loaded successfully"
else
    echo "⚠ Image not found at $VLLM_IMAGE_PATH"
    echo "Continuing without loading image..."
fi

echo ""
echo "Step 2: Checking Docker images..."
docker images | grep vllm || echo "No vLLM images found"

echo ""
echo "Step 3: Starting Docker services..."
cd "$PROJECT_ROOT"
docker compose -f ops/docker-compose.strix.yml down || true
docker compose -f ops/docker-compose.strix.yml up -d qdrant postgres n8n

echo ""
echo "Step 4: Starting vLLM service..."
docker compose -f ops/docker-compose.strix.yml up -d inference-vllm

echo ""
echo "Step 5: Starting llama.cpp servers..."
./scripts/start_llama_servers.sh stop || true
sleep 2
./scripts/start_llama_servers.sh start

echo ""
echo "Step 6: Checking service status..."
echo "Docker services:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "llama.cpp servers:"
./scripts/start_llama_servers.sh status

echo ""
echo "=========================================="
echo "Reingestion complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check that all services are healthy"
echo "2. Test the API endpoints"
echo "3. Verify GPU acceleration is working"
echo ""