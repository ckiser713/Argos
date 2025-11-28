#!/bin/bash
#
# Orchestrates a sequential, two-phase ingestion process using a dedicated
# inference engine for high-fidelity data processing.

set -euo pipefail

# --- Configuration ---
COMPOSE_FILE="ops/docker-compose.ingest.yml"
BACKEND_IMAGE="cortex-backend:latest"
BACKEND_DOCKERFILE="Dockerfile.backend"
NETWORK_NAME="cortex-network"

# Phase 1: Document Processing (Deep Context)
PHASE1_MODEL="nvidia/Nemotron-8B-Instruct"
PHASE1_SCRIPT="backend/scripts/process_documents.py"
PHASE1_CONTAINER_NAME="cortex-ingest-phase1"

# Phase 2: Database Organization (Reasoning)
PHASE2_MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
PHASE2_SCRIPT="backend/scripts/organize_database.py"
PHASE2_CONTAINER_NAME="cortex-ingest-phase2"

# --- Colors for Output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Helper Functions ---

# Ensure the backend Docker image exists, building it if necessary.
default ensure_backend_image() {
  echo -e "${BLUE}Checking for backend image: ${YELLOW}${BACKEND_IMAGE}${NC}"
  if ! docker image inspect "${BACKEND_IMAGE}" &> /dev/null; then
    echo -e "${YELLOW}Backend image not found. Building from ${BACKEND_DOCKERFILE}...${NC}"
    docker build -f "${BACKEND_DOCKERFILE}" -t "${BACKEND_IMAGE}" .
    echo -e "${GREEN}✓ Backend image built successfully.${NC}"
  else
    echo -e "${GREEN}✓ Backend image found.${NC}"
  fi
}

# Wait for the inference engine to become healthy.
wait_for_service() {
  local container_name=$1
  echo -e "Waiting for ${container_name} to become healthy..."
  
  # Give the container a moment to start up
  sleep 15

  for i in {1..30}; do # Timeout after 5 minutes (30 * 10s)
    if curl -sf "http://localhost:8000/health" > /dev/null; then
      echo -e "${GREEN}✓ Service is healthy!${NC}"
      return 0
    fi
    echo -n "."
    sleep 10
  done

  echo -e "\n${RED}✗ Service health check timed out!${NC}"
  # Grab logs for debugging
  docker logs "${container_name}"
  return 1
}

# Clean up function to stop and remove a container
cleanup() {
  local container_name=$1
  echo -e "Cleaning up container: ${container_name}"
  docker stop "${container_name}" >/dev/null && docker rm "${container_name}" >/dev/null || echo -e "${YELLOW}Warning: Could not stop/remove container ${container_name}. It may have already been removed.${NC}"
}

# --- Main Execution ---

# Ensure project root is current directory
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Build backend image if needed
ensure_backend_image

# Trap to ensure cleanup happens on exit or error
trap 'cleanup "${PHASE1_CONTAINER_NAME}"; cleanup "${PHASE2_CONTAINER_NAME}";' EXIT

# --- Phase 1: Process Documents ---
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Starting Phase 1: Document Processing ${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Starting inference engine with model: ${PHASE1_MODEL}"
# Start the vLLM server with the specified model
docker compose -f "${COMPOSE_FILE}" run -d --name "${PHASE1_CONTAINER_NAME}" --service-ports inference-engine \
  python -m vllm.entrypoints.openai.api_server \
  --model "${PHASE1_MODEL}" \
  --dtype bfloat16 \
  --max-model-len 131072

# Wait for the service to be ready
wait_for_service "${PHASE1_CONTAINER_NAME}"

echo "Running document processing script: ${PHASE1_SCRIPT}"
# Run the processing script in a backend container
docker run --rm --network="${NETWORK_NAME}" -v "$(pwd):/app" -w /app "${BACKEND_IMAGE}" \
  python "${PHASE1_SCRIPT}"

echo -e "${GREEN}✓ Phase 1 completed.${NC}"
cleanup "${PHASE1_CONTAINER_NAME}"


# --- Phase 2: Organize Database ---
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Starting Phase 2: Database Organization${NC}"
echo -e "${BLUE}========================================${NC}"

echo "Starting inference engine with model: ${PHASE2_MODEL}"
docker compose -f "${COMPOSE_FILE}" run -d --name "${PHASE2_CONTAINER_NAME}" --service-ports inference-engine \
  python -m vllm.entrypoints.openai.api_server \
  --model "${PHASE2_MODEL}" \
  --dtype bfloat16

# Wait for the service to be ready
wait_for_service "${PHASE2_CONTAINER_NAME}"

echo "Running database organization script: ${PHASE2_SCRIPT}"
docker run --rm --network="${NETWORK_NAME}" -v "$(pwd):/app" -w /app "${BACKEND_IMAGE}" \
  python "${PHASE2_SCRIPT}"

echo -e "${GREEN}✓ Phase 2 completed.${NC}"
cleanup "${PHASE2_CONTAINER_NAME}"

# --- Completion ---
trap - EXIT # Clear the trap
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Sequential Ingest Process Complete!   ${NC}"
echo -e "${GREEN}========================================${NC}
