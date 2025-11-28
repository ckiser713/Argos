#!/bin/bash
# Cortex Deployment Script V3
# Enhanced for Strix Halo Environment and Safety Checks

set -e

# --- Configuration ---
STRIX_MODE=false
DOCKER_COMPOSE_FILE="ops/docker-compose.yml"
STRIX_DOCKER_COMPOSE_FILE="ops/docker-compose.strix.yml"
STRIX_IMAGE_NAME="vllm-rocm-strix:latest"
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Token Validation ---
if [ -z "$HF_TOKEN" ]; then
    echo -e "${RED}Error: HF_TOKEN is not set. You cannot download Llama 3.2 without it.${NC}"
    exit 1
fi

# --- Argument Parsing ---
if [[ "$1" == "--strix" ]]; then
    STRIX_MODE=true
    DOCKER_COMPOSE_FILE=$STRIX_DOCKER_COMPOSE_FILE
    echo "🚀 Strix Halo mode enabled. Using $DOCKER_COMPOSE_FILE"
else
    echo "Standard deployment mode. Use --strix for Strix Halo environment."
fi

echo "=== Cortex Deployment ==="
echo ""

# Check if we're in nix-shell
if ! command -v nix-shell >/dev/null 2>&1 && ! [ -n "$IN_NIX_SHELL" ]; then
    echo "ERROR: This script must be run inside a nix-shell"
    echo "Run: nix-shell"
    exit 1
fi

echo "1. Installing backend dependencies..."
echo "   - Installing custom ROCm wheels..."
(cd backend && poetry run pip install ~/rocm/py311-tor290/wheels/common/triton-*.whl)
(cd backend && poetry run pip install ~/rocm/py311-tor290/wheels/common/tokenizers-*.whl)
(cd backend && poetry run pip install ~/rocm/py311-tor290/wheels/torch2.9/torch-*.whl)
(cd backend && poetry run pip install ~/rocm/py311-tor290/wheels/torch2.9/torchvision-*.whl)
(cd backend && poetry run pip install ~/rocm/py311-tor290/wheels/torch2.9/torchaudio-*.whl)
echo "   - Verifying torch installation..."
(cd backend && poetry run python -c "import torch; print(f'torch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')")
(cd backend && poetry install --no-root)
echo "✓ Backend dependencies installed"
echo ""

echo "2. Installing and building frontend..."
(cd frontend && pnpm install && pnpm build)
echo "✓ Frontend dependencies installed and built"
echo ""

echo "3. Installing root dependencies..."
pnpm install
echo "✓ Root dependencies installed"
echo ""

# --- Strix-specific Setup ---
if [ "$STRIX_MODE" = true ]; then
    echo "4. Running Strix Halo specific setup..."

    # Load vLLM ROCm image from local artifact
    echo "   - Loading vLLM ROCm image from ~/rocm/py311-tor290/images/vllm_rocm_image.tar..."
    VLLM_IMAGE_OUTPUT=$(docker load -i ~/rocm/py311-tor290/images/vllm_rocm_image.tar)
    
    # The output of 'docker load' is expected to be in the format 'Loaded image: <image_name>:<tag>' or 'Loaded image ID: sha256:...'
    # We parse this output to get the image identifier.
    if [[ "$VLLM_IMAGE_OUTPUT" == *"Loaded image: "* ]]; then
        # Extract name and tag, e.g., "vllm-rocm-strix:latest"
        export CORTEX_VLLM_IMAGE=$(echo "$VLLM_IMAGE_OUTPUT" | sed -n 's/Loaded image: \(.*\)/\1/p')
    elif [[ "$VLLM_IMAGE_OUTPUT" == *"Loaded image ID: "* ]]; then
        # Extract SHA, e.g., "sha256:abcdef123456"
        export CORTEX_VLLM_IMAGE=$(echo "$VLLM_IMAGE_OUTPUT" | sed -n 's/Loaded image ID: \(.*\)/\1/p')
    else
        echo -e "${RED}Error: Could not determine image identifier from 'docker load' output.${NC}"
        echo "Output was: $VLLM_IMAGE_OUTPUT"
        exit 1
    fi
    
    echo "   - ✓ Image loaded. Exported CORTEX_VLLM_IMAGE=$CORTEX_VLLM_IMAGE"

    # Generate backend helper script
    echo "   - Generating start_backend.sh helper script..."
    cat << 'EOF' > start_backend.sh
#!/bin/bash
# Helper script to start the backend with Strix Halo environment variables

echo "Starting backend with Strix Lane configuration..."
export CORTEX_LANE_ORCHESTRATOR_URL="http://localhost:8000/v1"
export CORTEX_LANE_SUPER_READER_URL="http://localhost:8080/v1"
export CORTEX_ENV="strix"

# Add other lane URLs as needed for Coder, etc.
# export CORTEX_LANE_CODER_URL="http://localhost:8000/v1" 

cd backend
poetry run uvicorn app.main:app --reload --port 8001
EOF
    chmod +x start_backend.sh
    echo "   - ✓ start_backend.sh created. Run with: ./start_backend.sh"
    echo ""
fi

echo "5. Downloading required AI models..."
if [ -f "./ops/download_all_models.sh" ]; then
    ./ops/download_all_models.sh
else
    echo "   - WARNING: ./ops/download_all_models.sh not found. Skipping model download."
fi
echo "✓ Model download process finished."
echo ""

echo "6. Preparing Docker environment..."
echo "   - Creating Qdrant storage directory..."
mkdir -p ops/qdrant_storage
echo "   - Setting permissions for Qdrant storage..."
chmod 777 ops/qdrant_storage
echo "✓ Docker environment prepared."
echo ""


echo "7. Starting Docker services..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
echo "✓ Docker services started"
echo ""

echo "8. Installing Playwright browsers..."
pnpm exec playwright install --with-deps
echo "✓ Playwright browsers installed"
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Services running:"
echo "  - Docker services via: $DOCKER_COMPOSE_FILE"
echo "  - Qdrant: http://localhost:6333"
if [ "$STRIX_MODE" = true ]; then
    echo "  - Strix vLLM (Orchestrator/Coder): http://localhost:8000"
    echo "  - Strix Llama.cpp (Reader): http://localhost:8080"
    echo "  - Backend: http://localhost:8001 (start with: ./start_backend.sh)"
else
    echo "  - Backend: http://localhost:8000 (start with: cd backend && poetry run uvicorn app.main:app --reload)"
fi
echo "  - Frontend: http://localhost:5173 (start with: cd frontend && pnpm dev)"
echo ""
echo "Run E2E tests: pnpm e2e"
echo ""
echo "Stop services: docker-compose -f \"$DOCKER_COMPOSE_FILE\" down"
