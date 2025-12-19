#!/bin/bash
# Download models using HF_TOKEN from /etc/llama/llama.env
# This script should be run as user llama or with sudo -u llama

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

# Load HF_TOKEN from /etc/llama/llama.env
if [ -f /etc/llama/llama.env ]; then
    # Source the file to get environment variables
    set -a
    source /etc/llama/llama.env
    set +a
    echo "Loaded HF_TOKEN from /etc/llama/llama.env"
else
    echo "Warning: /etc/llama/llama.env not found"
fi

# Set models directory
export MODELS_DIR=/models

# Run the download script
cd "$BACKEND_DIR"
poetry run python scripts/download_models.py
