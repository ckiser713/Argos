#!/bin/bash
# Download FP8 models using huggingface-cli for better reliability

set -e

echo "=== FP8 Model Download (CLI) ==="

# Create directories
mkdir -p models/vllm/orchestrator/fp8
mkdir -p models/vllm/coder/fp8

# Function to download with retry
download_model() {
    local repo=$1
    local dest=$2
    local name=$3
    local max_retries=3
    local retry=0

    echo "Downloading $name to $dest..."

    # Check if already downloaded
    if ls "$dest"/*.safetensors 2>/dev/null; then
        local size
        size=$(du -sh "$dest" | cut -f1)
        echo "✅ $name already downloaded ($size)"
        return 0
    fi

    while [ $retry -lt $max_retries ]; do
        echo "Attempt $((retry+1))/$max_retries for $name..."

        if huggingface-cli download "$repo" --local-dir "$dest" --local-dir-use-symlinks False; then
            # Verify download
            if ls "$dest"/*.safetensors 2>/dev/null; then
                local size
                size=$(du -sh "$dest" | cut -f1)
                echo "✅ $name downloaded successfully ($size)"
                return 0
            else
                echo "❌ Verification failed - no safetensors files found"
            fi
        else
            echo "❌ Download attempt $((retry+1)) failed"
        fi

        retry=$((retry+1))
        if [ $retry -lt $max_retries ]; then
            echo "Retrying in 10 seconds..."
            sleep 10
        fi
    done

    echo "❌ $name download failed after $max_retries attempts"
    return 1
}

# Download models
echo "Starting downloads..."
download_model "neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic" "models/vllm/orchestrator/fp8" "ORCHESTRATOR FP8"
download_model "BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic" "models/vllm/coder/fp8" "CODER FP8"

echo ""
echo "=== Summary ==="
echo "Checking final sizes..."
du -sh models/vllm/orchestrator/fp8 models/vllm/coder/fp8 2>/dev/null || echo "Some directories not found"

echo ""
echo "With FAST_RAG BF16 (40GB), expected total VRAM: ~72GB"
echo "This fits comfortably within 96GB VRAM limit!"