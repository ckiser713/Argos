#!/bin/bash
# Robust model download script using huggingface-cli
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
# Default to ops/models relative to the script location to avoid permission issues
DEFAULT_MODELS_DIR="$SCRIPT_DIR/../ops/models"
MODELS_DIR="${MODELS_DIR:-$DEFAULT_MODELS_DIR}"

# Load HF_TOKEN from .env
if [ -f "$SCRIPT_DIR/../.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/../.env" | grep HF_TOKEN | xargs)
fi

if [ -z "$HF_TOKEN" ]; then
    echo "ERROR: HF_TOKEN not set. Please set it in .env file or environment."
    exit 1
fi

# Enable HF Transfer for faster, more robust downloads (if hf_transfer is installed)
export HF_HUB_ENABLE_HF_TRANSFER=1

echo "=========================================="
echo "Model Download Script (Robust)"
echo "=========================================="
echo "Models directory: $MODELS_DIR"
echo "HF Transfer: Enabled"
echo ""

cd "$BACKEND_DIR"

# Download models one at a time with progress and retries
download_model() {
    local repo=$1
    local target_dir=$2
    local name=$3
    local filename=$4
    
    echo "----------------------------------------"
    echo "Downloading: $name"
    echo "Repository: $repo"
    echo "Target: $target_dir"
    [ -n "$filename" ] && echo "File: $filename"
    echo "----------------------------------------"
    
    # Check if already complete (simple check)
    if [ -d "$target_dir" ]; then
        # If specific filename requested, check it
        if [ -n "$filename" ]; then
            if [ -f "$target_dir/$filename" ]; then
                echo "✓ Model file $filename already exists, skipping."
                return 0
            fi
        # Otherwise check for any model files
        elif find "$target_dir" -name "*.safetensors" -o -name "*.bin" -o -name "*.gguf" | grep -q .; then
            echo "✓ Model files detected in $target_dir, assuming complete (run with --force to re-download)."
            return 0
        fi
    fi
    
    mkdir -p "$target_dir"
    
    # Retry loop
    local max_retries=5
    local retry_count=0
    local success=0
    
    while [ $retry_count -lt $max_retries ]; do
        if [ $retry_count -gt 0 ]; then
            echo "⚠ Retry $((retry_count+1))/$max_retries in 5 seconds..."
            sleep 5
        fi

        set +e # temporarily disable exit on error
        if [ -n "$filename" ]; then
             HF_TOKEN="$HF_TOKEN" poetry run hf download \
                "$repo" \
                "$filename" \
                --local-dir "$target_dir"
        else
             HF_TOKEN="$HF_TOKEN" poetry run hf download \
                "$repo" \
                --local-dir "$target_dir"
        fi
        
        if [ $? -eq 0 ]; then
            success=1
            set -e
            break
        else
            echo "✗ Download attempt failed."
            set -e
        fi
        
        retry_count=$((retry_count+1))
    done

    if [ $success -eq 0 ]; then
        echo "❌ Failed to download $name after $max_retries attempts."
        return 1
    fi
    
    echo "✓ Successfully downloaded $name"
    echo ""
}

# vLLM Models
echo "=== vLLM Models ==="
download_model "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B" \
    "$MODELS_DIR/vllm/orchestrator/bf16" \
    "Orchestrator (DeepSeek-R1)"

download_model "Qwen/Qwen2.5-Coder-32B-Instruct" \
    "$MODELS_DIR/vllm/coder/bf16" \
    "Coder (Qwen2.5)"

download_model "meta-llama/Llama-3.2-11B-Vision-Instruct" \
    "$MODELS_DIR/vllm/fast_rag/bf16" \
    "Fast RAG (Llama 3.2 Vision)"

# GGUF Models
echo "=== GGUF Models ==="
mkdir -p "$MODELS_DIR/gguf"

# Super Reader (Specific GGUF)
download_model "Mungert/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-GGUF" \
    "$MODELS_DIR/gguf" \
    "Super Reader (Nemotron)" \
    "Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf"

# Governance (Specific GGUF)
download_model "bartowski/granite-3.0-8b-instruct-GGUF" \
    "$MODELS_DIR/gguf" \
    "Governance (Granite)" \
    "granite-3.0-8b-instruct-Q4_K_M.gguf"

echo "=========================================="
echo "Download process completed!"
echo "=========================================="