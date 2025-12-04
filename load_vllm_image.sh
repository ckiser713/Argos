#!/bin/bash
# Load the vLLM ROCm image from the artifact folder

set -e

IMAGE_PATH="/home/nexus/rocm/py311-tor290/images/vllm_rocm_image.tar"
IMAGE_NAME="vllm-rocm-gfx1151:complete"

echo "Loading vLLM ROCm image from: $IMAGE_PATH"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: Image file not found at $IMAGE_PATH"
    exit 1
fi

echo "Image file exists. Loading into Docker..."
docker load -i "$IMAGE_PATH"

echo "Image loaded successfully!"
docker images | grep vllm