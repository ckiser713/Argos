#!/bin/bash
# Download FP8 models in background for memory-efficient deployment

set -e

echo "=== Downloading FP8 Models in Background ==="
echo "This will download ~30GB total of FP8 quantized models"
echo "Models will use ~25% of the memory of BF16 versions"
echo ""

# Create directories
mkdir -p models/vllm/orchestrator/fp8
mkdir -p models/vllm/coder/fp8

# Function to download with retry
download_model() {
    local repo=$1
    local dest=$2
    local name=$3

    echo "Downloading $name to $dest..."

    # Check if already has safetensors files
    if ls "$dest"/*.safetensors 2>/dev/null; then
        echo "✅ $name already downloaded"
        return 0
    fi

    # Download with huggingface-cli (more reliable for large files)
    if command -v huggingface-cli &> /dev/null; then
        echo "Using huggingface-cli for $name..."
        huggingface-cli download "$repo" --local-dir "$dest" --local-dir-use-symlinks False
    else
        echo "Using Python API for $name..."
        python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='$repo',
    local_dir='$dest',
    local_dir_use_symlinks=False,
    max_workers=4
)
"
    fi

    # Verify download
    if ls "$dest"/*.safetensors 2>/dev/null; then
        local size
        size=$(du -sh "$dest" | cut -f1)
        echo "✅ $name downloaded successfully ($size)"
    else
        echo "❌ $name download failed - no safetensors files found"
        return 1
    fi
}

# Download models sequentially
echo "1. Downloading ORCHESTRATOR FP8..."
download_model "neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic" "models/vllm/orchestrator/fp8" "ORCHESTRATOR FP8"

echo ""
echo "2. Downloading CODER FP8..."
download_model "BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic" "models/vllm/coder/fp8" "CODER FP8"

echo ""
echo "=== Download Complete ==="
echo "FP8 models provide ~75% memory savings vs BF16"
echo "Total VRAM usage will be ~72GB with 96GB available"