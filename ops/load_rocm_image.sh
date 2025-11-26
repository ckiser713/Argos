#!/bin/bash
# Load ROCm vLLM Docker image from pre-built tarball
# This script loads the pre-built vLLM image with ROCm support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ROCM_IMAGE_PATH="${ROCM_IMAGE_PATH:-$HOME/rocm/py311-tor290/images/vllm_rocm_image.tar}"
ROCM_IMAGE_DIR="$(dirname "$ROCM_IMAGE_PATH")"
CHECKSUM_FILE="${ROCM_IMAGE_PATH}.sha256"

echo "=========================================="
echo "ROCm vLLM Image Loader"
echo "=========================================="
echo ""

# Check if image file exists
if [ ! -f "$ROCM_IMAGE_PATH" ]; then
    echo "Error: ROCm image not found at: $ROCM_IMAGE_PATH"
    echo ""
    echo "Please ensure the image exists, or set ROCM_IMAGE_PATH environment variable:"
    echo "  export ROCM_IMAGE_PATH=/path/to/vllm_rocm_image.tar"
    exit 1
fi

echo "Image path: $ROCM_IMAGE_PATH"
echo "Image size: $(du -h "$ROCM_IMAGE_PATH" | cut -f1)"
echo ""

# Verify checksum if available
if [ -f "$CHECKSUM_FILE" ]; then
    echo "Verifying image checksum..."
    cd "$ROCM_IMAGE_DIR"
    if sha256sum -c "$(basename "$CHECKSUM_FILE")"; then
        echo "✓ Checksum verified successfully"
    else
        echo "⚠ Warning: Checksum verification failed!"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    echo ""
else
    echo "⚠ Checksum file not found at: $CHECKSUM_FILE"
    echo "  Skipping verification..."
    echo ""
fi

# Check if image already loaded
IMAGE_NAME="vllm-rocm-strix:latest"
if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Image '$IMAGE_NAME' already exists in Docker."
    read -p "Remove existing image and reload? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing image..."
        docker rmi "$IMAGE_NAME" || true
    else
        echo "Keeping existing image. Exiting."
        exit 0
    fi
    echo ""
fi

# Load the image
echo "Loading Docker image (this may take a few minutes)..."
docker load -i "$ROCM_IMAGE_PATH"

echo ""
echo "=========================================="
echo "✓ Image loaded successfully!"
echo "=========================================="
echo ""
echo "Image name: $IMAGE_NAME"
echo ""
echo "To use this image, update ops/docker-compose.yml:"
echo "  inference-engine:"
echo "    image: $IMAGE_NAME"
echo "    # Remove 'build:' section"
echo ""
echo "Or run manually:"
echo "  docker run --rm --device=/dev/kfd --device=/dev/dri \\"
echo "    --group-add video --group-add render \\"
echo "    -p 11434:8000 \\"
echo "    $IMAGE_NAME \\"
echo "    --model /path/to/model --host 0.0.0.0 --port 8000"
echo ""


