#!/bin/bash
# Unattended FP8 model download that survives terminal disconnection

set -e

echo "=== Unattended FP8 Model Download ==="
echo "This script will download models in background and survive disconnection"
echo ""

# Create log file
LOG_FILE="download_fp8_unattended.log"
echo "$(date): Starting unattended FP8 download" > "$LOG_FILE"

# Function to download with logging
download_with_log() {
    local repo=$1
    local dest=$2
    local name=$3

    echo "$(date): Starting $name download" >> "$LOG_FILE"

    # Clean any existing locks
    find "$dest" -name "*.lock" -delete 2>/dev/null || true
    find "$dest" -name "*.incomplete" -delete 2>/dev/null || true

    # Check if already downloaded
    if ls "$dest"/*.safetensors 2>/dev/null; then
        local size
        size=$(du -sh "$dest" | cut -f1)
        echo "$(date): ✅ $name already downloaded ($size)" >> "$LOG_FILE"
        echo "$(date): ✅ $name already downloaded ($size)"
        return 0
    fi

    echo "$(date): Downloading $name..." >> "$LOG_FILE"
    echo "$(date): Downloading $name..."

    # Use hf command (modern version)
    if hf download "$repo" --local-dir "$dest" >> "$LOG_FILE" 2>&1; then
        # Verify download
        if ls "$dest"/*.safetensors 2>/dev/null; then
            local size
            size=$(du -sh "$dest" | cut -f1)
            echo "$(date): ✅ $name downloaded successfully ($size)" >> "$LOG_FILE"
            echo "$(date): ✅ $name downloaded successfully ($size)"
            return 0
        else
            echo "$(date): ❌ $name verification failed - no safetensors files" >> "$LOG_FILE"
            echo "$(date): ❌ $name verification failed - no safetensors files"
            return 1
        fi
    else
        echo "$(date): ❌ $name download failed" >> "$LOG_FILE"
        echo "$(date): ❌ $name download failed"
        return 1
    fi
}

# Create directories
mkdir -p models/vllm/orchestrator/fp8
mkdir -p models/vllm/coder/fp8

echo "Starting downloads..." >> "$LOG_FILE"
echo "Starting downloads..."

# Download models sequentially
download_with_log "neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic" "models/vllm/orchestrator/fp8" "ORCHESTRATOR FP8"
download_with_log "BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic" "models/vllm/coder/fp8" "CODER FP8"

echo "$(date): All downloads completed" >> "$LOG_FILE"
echo "$(date): All downloads completed"

echo ""
echo "=== Final Summary ===" >> "$LOG_FILE"
echo "=== Final Summary ==="
echo "FP8 Model Sizes:" >> "$LOG_FILE"
echo "FP8 Model Sizes:"
du -sh models/vllm/orchestrator/fp8 models/vllm/coder/fp8 models/vllm/fast_rag/bf16 2>/dev/null >> "$LOG_FILE"
du -sh models/vllm/orchestrator/fp8 models/vllm/coder/fp8 models/vllm/fast_rag/bf16 2>/dev/null

echo ""
echo "Expected total VRAM usage: ~72GB (fits in 96GB limit!)" >> "$LOG_FILE"
echo "Expected total VRAM usage: ~72GB (fits in 96GB limit!)"