#!/bin/bash
#
# Download all models required for Cortex Model Lanes
# This script is a wrapper around the main Python download manager.
#
# Usage:
#   ./ops/download_all_models.sh [--models-dir /path/to/models] [--skip-vllm] [--skip-gguf] [--skip-embeddings]
#
# Environment Variables:
#   MODELS_DIR      - Base directory for models (default: ./models)
#   HF_TOKEN        - Hugging Face token (optional, for gated models)
#   SKIP_VLLM       - Skip vLLM models (default: false)
#   SKIP_GGUF       - Skip GGUF models (default: false)
#   SKIP_EMBEDDINGS - Skip embedding models (default: false)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default models directory (relative to the project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
export MODELS_DIR="${MODELS_DIR:-${PROJECT_ROOT}/models}"

# --- Argument Parsing ---
# Set env vars for the Python script to consume
export SKIP_VLLM="${SKIP_VLLM:-false}"
export SKIP_GGUF="${SKIP_GGUF:-false}"
export SKIP_EMBEDDINGS="${SKIP_EMBEDDINGS:-false}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --models-dir)
      export MODELS_DIR="$2"
      shift 2
      ;;
    --skip-vllm)
      export SKIP_VLLM="true"
      shift
      ;;
    --skip-gguf)
      export SKIP_GGUF="true"
      shift
      ;;
    --skip-embeddings)
      export SKIP_EMBEDDINGS="true"
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
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
echo -e "SKIP_VLLM=${SKIP_VLLM}"
echo -e "SKIP_GGUF=${SKIP_GGUF}"
echo -e "SKIP_EMBEDDINGS=${SKIP_EMBEDDINGS}"
echo ""

# Create models directory if it doesn't exist
mkdir -p "${MODELS_DIR}"

# --- Execute Python Download Manager ---
echo -e "${BLUE}Executing Python download manager...${NC}"
echo ""

# Run the python script from the project root
cd "${PROJECT_ROOT}"
python3 backend/scripts/download_models.py

# --- Summary ---
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Model Download Script Finished!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Models are stored in: ${MODELS_DIR}"
echo "Check the output above for the status of each download."
echo ""
echo "Directory structure:"
echo "  ${MODELS_DIR}/vllm/       - vLLM models (ORCHESTRATOR, CODER, FAST_RAG)"
echo "    ├── orchestrator/"
echo "    │   ├── bf16/          - Full BF16 weights"
echo "    │   └── fp8/           - Quantized FP8 weights (if available)"
echo "    └── ..."
echo "  ${MODELS_DIR}/gguf/       - GGUF models (SUPER_READER, GOVERNANCE)"
echo "  (Embeddings are cached by sentence-transformers library)"
echo ""
echo "Next steps:"
echo "1. Update docker-compose.strix.yml volumes to mount ${MODELS_DIR}"
echo "2. Set environment variables pointing to model paths"
echo "3. Start services with: docker-compose -f ops/docker-compose.strix.yml up"
echo ""