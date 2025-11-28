#!/bin/bash
#
# Download all models required for Cortex Model Lanes
# Models are downloaded outside containers to a shared directory
# that can be mounted into containers.
#
# Usage:
#   ./ops/download_all_models.sh [--models-dir /path/to/models]
#
# Environment Variables:
#   MODELS_DIR - Base directory for models (default: ./models)
#   HF_TOKEN - Hugging Face token (optional, for gated models)
#   SKIP_VLLM - Skip vLLM models (default: false)
#   SKIP_GGUF - Skip GGUF models (default: false)
#   SKIP_EMBEDDINGS - Skip embedding models (default: false)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default models directory (relative to script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${MODELS_DIR:-${SCRIPT_DIR}/models}"

# Parse arguments
SKIP_VLLM="${SKIP_VLLM:-false}"
SKIP_GGUF="${SKIP_GGUF:-false}"
SKIP_EMBEDDINGS="${SKIP_EMBEDDINGS:-false}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --models-dir)
      MODELS_DIR="$2"
      shift 2
      ;;
    --skip-vllm)
      SKIP_VLLM="true"
      shift
      ;;
    --skip-gguf)
      SKIP_GGUF="true"
      shift
      ;;
    --skip-embeddings)
      SKIP_EMBEDDINGS="true"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--models-dir PATH] [--skip-vllm] [--skip-gguf] [--skip-embeddings]"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cortex Model Lanes - Model Downloader${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Models directory: ${GREEN}${MODELS_DIR}${NC}"
echo ""

# Create models directory structure
mkdir -p "${MODELS_DIR}"/{vllm,gguf,embeddings}

# Function to download with huggingface-cli
download_hf_model() {
  local repo_id=$1
  local local_dir=$2
  local description=$3
  
  echo -e "${YELLOW}Downloading: ${description}${NC}"
  echo -e "  Repository: ${repo_id}"
  echo -e "  Destination: ${local_dir}"
  
  if [ -d "${local_dir}" ] && [ "$(ls -A ${local_dir} 2>/dev/null)" ]; then
    echo -e "  ${GREEN}✓ Already exists, skipping${NC}"
    return 0
  fi
  
  mkdir -p "${local_dir}"
  
  # Use huggingface-cli if available, otherwise use Python
  if command -v huggingface-cli &> /dev/null; then
    echo "  Using huggingface-cli..."
    huggingface-cli download "${repo_id}" \
      --local-dir "${local_dir}" \
      --local-dir-use-symlinks False \
      ${HF_TOKEN:+--token "${HF_TOKEN}"} || {
      echo -e "  ${RED}✗ Failed to download${NC}"
      return 1
    }
  else
    echo "  Using Python huggingface_hub..."
    python3 -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id='${repo_id}',
    local_dir='${local_dir}',
    local_dir_use_symlinks=False,
    token=os.getenv('HF_TOKEN')
)
" || {
      echo -e "  ${RED}✗ Failed to download${NC}"
      return 1
    }
  fi
  
  echo -e "  ${GREEN}✓ Successfully downloaded${NC}"
}

# Function to download GGUF model (specific file)
download_gguf_file() {
  local repo_id=$1
  local filename=$2
  local local_dir=$3
  local description=$4
  
  echo -e "${YELLOW}Downloading GGUF: ${description}${NC}"
  echo -e "  Repository: ${repo_id}"
  echo -e "  File: ${filename}"
  echo -e "  Destination: ${local_dir}"
  
  local file_path="${local_dir}/${filename}"
  
  if [ -f "${file_path}" ]; then
    echo -e "  ${GREEN}✓ Already exists, skipping${NC}"
    return 0
  fi
  
  mkdir -p "${local_dir}"
  
  # Use huggingface-cli to download specific file
  if command -v huggingface-cli &> /dev/null; then
    huggingface-cli download "${repo_id}" "${filename}" \
      --local-dir "${local_dir}" \
      ${HF_TOKEN:+--token "${HF_TOKEN}"} || {
      echo -e "  ${RED}✗ Failed to download${NC}"
      return 1
    }
  else
    python3 -c "
from huggingface_hub import hf_hub_download
import os
hf_hub_download(
    repo_id='${repo_id}',
    filename='${filename}',
    local_dir='${local_dir}',
    token=os.getenv('HF_TOKEN')
)
" || {
      echo -e "  ${RED}✗ Failed to download${NC}"
      return 1
    }
  fi
  
  echo -e "  ${GREEN}✓ Successfully downloaded${NC}"
}

# Download vLLM models (for ORCHESTRATOR, CODER, FAST_RAG lanes)
if [ "${SKIP_VLLM}" != "true" ]; then
  echo -e "${BLUE}=== Downloading vLLM Models ===${NC}"
  
  # ORCHESTRATOR: Qwen3-30B-Thinking-256k
  # Note: Actual model name may vary - adjust based on availability
  download_hf_model \
    "Qwen/Qwen2.5-32B-Instruct" \
    "${MODELS_DIR}/vllm/qwen-orchestrator" \
    "ORCHESTRATOR Lane - Qwen Thinking Model"
  
  # CODER: Qwen3-Coder-30B-1M
  download_hf_model \
    "Qwen/Qwen2.5-Coder-32B-Instruct" \
    "${MODELS_DIR}/vllm/qwen-coder" \
    "CODER Lane - Qwen Coder Model"
  
  # FAST_RAG: MegaBeam-Mistral-7B-512k
  # Note: May need to adjust model name based on actual availability
  download_hf_model \
    "mistralai/Mistral-7B-Instruct-v0.2" \
    "${MODELS_DIR}/vllm/mistral-fastrag" \
    "FAST_RAG Lane - Mistral Model"
  
  echo ""
else
  echo -e "${YELLOW}Skipping vLLM models${NC}"
  echo ""
fi

# Download GGUF models (for SUPER_READER, GOVERNANCE lanes)
if [ "${SKIP_GGUF}" != "true" ]; then
  echo -e "${BLUE}=== Downloading GGUF Models ===${NC}"
  
  # SUPER_READER: Nemotron-8B-UltraLong-4M
  # Download GGUF file (adjust filename based on actual model)
  download_gguf_file \
    "nvidia/Nemotron-8B-Instruct" \
    "nemotron-8b-instruct.Q4_K_M.gguf" \
    "${MODELS_DIR}/gguf" \
    "SUPER_READER Lane - Nemotron UltraLong"
  
  # Alternative: If model uses different naming, try common variants
  if [ ! -f "${MODELS_DIR}/gguf/nemotron-8b-instruct.Q4_K_M.gguf" ]; then
    echo "  Trying alternative GGUF filenames..."
    for variant in "nemotron-8b-instruct-q4_k_m.gguf" "nemotron-8b.Q4_K_M.gguf"; do
      download_gguf_file \
        "nvidia/Nemotron-8B-Instruct" \
        "${variant}" \
        "${MODELS_DIR}/gguf" \
        "SUPER_READER Lane - Nemotron (${variant})" && break
    done
  fi
  
  # GOVERNANCE: Granite 4.x Long-Context
  download_gguf_file \
    "ibm-granite/granite-8b-instruct" \
    "granite-8b-instruct.Q4_K_M.gguf" \
    "${MODELS_DIR}/gguf" \
    "GOVERNANCE Lane - Granite Long Context"
  
  echo ""
else
  echo -e "${YELLOW}Skipping GGUF models${NC}"
  echo ""
fi

# Download embedding models
if [ "${SKIP_EMBEDDINGS}" != "true" ]; then
  echo -e "${BLUE}=== Downloading Embedding Models ===${NC}"
  
  # Use Python script for embeddings (sentence-transformers)
  echo "Downloading embedding models using Python..."
  cd "${SCRIPT_DIR}/.." || exit 1
  
  python3 backend/scripts/download_models.py || {
    echo -e "${YELLOW}Warning: Embedding model download failed, continuing...${NC}"
  }
  
  echo ""
else
  echo -e "${YELLOW}Skipping embedding models${NC}"
  echo ""
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Model Download Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Models are stored in: ${MODELS_DIR}"
echo ""
echo "Directory structure:"
echo "  ${MODELS_DIR}/vllm/     - vLLM models (ORCHESTRATOR, CODER, FAST_RAG)"
echo "  ${MODELS_DIR}/gguf/     - GGUF models (SUPER_READER, GOVERNANCE)"
echo "  ${MODELS_DIR}/embeddings/ - Embedding models (RAG)"
echo ""
echo "Next steps:"
echo "1. Update docker-compose.strix.yml volumes to mount ${MODELS_DIR}"
echo "2. Set environment variables pointing to model paths"
echo "3. Start services with: docker-compose -f ops/docker-compose.strix.yml up"
echo ""

