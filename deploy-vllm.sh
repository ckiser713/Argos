#!/usr/bin/env bash

##############################################################################
# vLLM Nix Deployment Script
# 
# This script deploys vLLM using Nix in one of three ways:
#   1. Development shell (nix develop)
#   2. Systemd service (production)
#   3. OCI container (docker)
#
# Artifacts: /home/nexus/amd-ai/artifacts/
##############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ARTIFACTS_DIR="/home/nexus/amd-ai/artifacts"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_MODE="${1:-shell}"
MODEL_PATH="${MODEL_PATH:-}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.48}"

# Print functions
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Banner
print_banner() {
  cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                      vLLM Nix Deployment Tool                            ║
║                                                                           ║
║  Deploys vLLM with Nix for fast, reproducible AMD ROCm GPU inference    ║
╚═══════════════════════════════════════════════════════════════════════════╝
EOF
}

# Check artifacts exist
check_artifacts() {
  info "Checking artifacts directory: $ARTIFACTS_DIR"
  
  if [ ! -d "$ARTIFACTS_DIR" ]; then
    error "Artifacts directory not found: $ARTIFACTS_DIR"
    exit 1
  fi
  
  # Check for wheels
  if [ -f "$ARTIFACTS_DIR/vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl" ]; then
    success "Found vLLM wheel at $ARTIFACTS_DIR/vllm_docker_rocm/"
  elif [ -f "$ARTIFACTS_DIR/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl" ]; then
    success "Found vLLM wheel at $ARTIFACTS_DIR/"
  else
    error "vLLM wheel not found in artifacts"
    exit 1
  fi
  
  if [ -f "$ARTIFACTS_DIR/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl" ]; then
    success "Found PyTorch wheel"
  else
    warn "PyTorch wheel not found - may be auto-installed from PyPI"
  fi
  
  if [ -f "$ARTIFACTS_DIR/llama_cpp_rocm.tar.gz" ]; then
    success "Found llama.cpp archive (for future use)"
  fi
}

# Mode 1: Development Shell
deploy_shell() {
  info "Deploying vLLM in development shell mode..."
  
  if [ -z "$MODEL_PATH" ]; then
    warn "MODEL_PATH not set. Using default: /models/orchestrator/bf16"
    MODEL_PATH="/models/orchestrator/bf16"
  fi
  
  if [ ! -d "$MODEL_PATH" ]; then
    error "Model path does not exist: $MODEL_PATH"
    error "Please ensure model files are available or adjust MODEL_PATH"
    exit 1
  fi
  
  success "Using model: $MODEL_PATH"
  success "GPU memory utilization: $GPU_MEM_UTIL"
  
  echo ""
  echo "╔═══════════════════════════════════════════════════════════════════════════╗"
  echo "║                  Starting vLLM Development Shell                          ║"
  echo "╠═══════════════════════════════════════════════════════════════════════════╣"
  echo "║ Mode:           Shell (Development)"
  echo "║ Model Path:     $MODEL_PATH"
  echo "║ GPU Mem:        $GPU_MEM_UTIL"
  echo "║ Artifacts:      $ARTIFACTS_DIR"
  echo "╠═══════════════════════════════════════════════════════════════════════════╣"
  echo "║ Once in the shell, start vLLM with:"
  echo "║   vllm-server"
  echo "║"
  echo "║ Or with custom GPU memory:"
  echo "║   GPU_MEM_UTIL=0.50 vllm-server"
  echo "║"
  echo "║ Test with:"
  echo "║   curl http://localhost:8000/health"
  echo "║"
  echo "║ Exit shell with: exit"
  echo "╚═══════════════════════════════════════════════════════════════════════════╝"
  echo ""
  
  cd "$PROJECT_ROOT"
  nix develop -f flake.nix '.#vllm' --command bash
}

# Mode 2: Systemd Service
deploy_systemd() {
  info "Deploying vLLM as systemd service..."
  
  if [ "$EUID" -ne 0 ]; then 
    error "Systemd deployment requires root privileges"
    exit 1
  fi
  
  if [ -z "$MODEL_PATH" ]; then
    error "MODEL_PATH must be set for systemd deployment"
    error "Usage: MODEL_PATH=/path/to/model ./deploy-vllm.sh systemd"
    exit 1
  fi
  
  if [ ! -d "$MODEL_PATH" ]; then
    error "Model path does not exist: $MODEL_PATH"
    exit 1
  fi
  
  # Create systemd service file
  SERVICE_FILE="/etc/systemd/system/vllm.service"
  
  cat > "$SERVICE_FILE" << SYSTEMD_CONFIG
[Unit]
Description=vLLM Inference Server (ROCm)
Documentation=https://docs.vllm.ai/
After=network.target dev-kfd.device dev-dri.device
Wants=dev-kfd.device dev-dri.device

[Service]
Type=simple
Restart=always
RestartSec=10s
User=nexus
Group=nexus
WorkingDirectory=/var/lib/vllm

DeviceAllow=/dev/kfd rw
DeviceAllow=/dev/dri rw
DeviceAllow=/dev/shm rw
DevicePolicy=closed
SupplementaryGroups=video render

Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONDONTWRITEBYTECODE=1"
Environment="HIP_VISIBLE_DEVICES=0"
Environment="HSA_OVERRIDE_GFX_VERSION=11.0.0"
Environment="VLLM_TARGET_DEVICE=rocm"
Environment="VLLM_ROCM_USE_AITER=1"
Environment="VLLM_ROCM_USE_SKINNY_GEMM=1"
Environment="MODEL_PATH=$MODEL_PATH"
Environment="GPU_MEM_UTIL=$GPU_MEM_UTIL"
Environment="VLLM_HOST=0.0.0.0"
Environment="VLLM_PORT=8000"

ExecStart=${PROJECT_ROOT}/result/bin/vllm-server

MemoryLimit=64G
CPUQuota=80%
TasksMax=4096

StandardOutput=journal
StandardError=journal
SyslogIdentifier=vllm

[Install]
WantedBy=multi-user.target
SYSTEMD_CONFIG
  
  success "Created systemd service: $SERVICE_FILE"
  
  # Enable and start service
  systemctl daemon-reload
  systemctl enable vllm.service
  systemctl start vllm.service
  
  success "vLLM service enabled and started"
  
  echo ""
  echo "╔═══════════════════════════════════════════════════════════════════════════╗"
  echo "║                    vLLM Service Started                                   ║"
  echo "╠═══════════════════════════════════════════════════════════════════════════╣"
  echo "║ Check status:    systemctl status vllm"
  echo "║ View logs:       journalctl -u vllm -f"
  echo "║ Stop service:    systemctl stop vllm"
  echo "║ Restart:         systemctl restart vllm"
  echo "║"
  echo "║ Test API:        curl http://localhost:8000/health"
  echo "║ Chat completion: curl -X POST http://localhost:8000/v1/chat/completions \\"
  echo "║                    -H 'Content-Type: application/json' \\"
  echo "║                    -d '{\"model\": \"...\", \"messages\": [{\"role\": \"user\", \"content\": \"Hi\"}]}'"
  echo "╚═══════════════════════════════════════════════════════════════════════════╝"
  echo ""
}

# Mode 3: OCI Container
deploy_container() {
  info "Building vLLM OCI container..."
  
  cd "$PROJECT_ROOT"
  
  info "Building container image..."
  nix build '.#vllm-container' --out-link result-container
  
  success "Container image built"
  
  if command -v docker &> /dev/null; then
    info "Loading image into Docker..."
    docker load -i result-container
    success "Image loaded into Docker"
    
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║                  OCI Container Built Successfully                        ║"
    echo "╠═══════════════════════════════════════════════════════════════════════════╣"
    echo "║ Run with docker:"
    echo "║   docker run -it --rm \\\"
    echo "║     --device /dev/kfd \\\"
    echo "║     --device /dev/dri \\\"
    echo "║     -p 8000:8000 \\\"
    echo "║     -e MODEL_PATH=/models/orchestrator/bf16 \\\"
    echo "║     -v /path/to/models:/models:ro \\\"
    echo "║     vllm-rocm-nix:latest"
    echo "║"
    echo "║ Or add to docker-compose.yml:"
    echo "║   services:"
    echo "║     vllm:"
    echo "║       image: vllm-rocm-nix:latest"
    echo "║       devices:"
    echo "║         - /dev/kfd:/dev/kfd"
    echo "║         - /dev/dri:/dev/dri"
    echo "║       ports:"
    echo "║         - 8000:8000"
    echo "║       environment:"
    echo "║         MODEL_PATH: /models/orchestrator/bf16"
    echo "║       volumes:"
    echo "║         - /path/to/models:/models:ro"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo ""
  else
    warn "Docker not found - image built but not loaded"
    info "Load manually with: docker load -i result-container"
  fi
}

# Show usage
show_usage() {
  cat << USAGE
Usage: $0 [MODE] [OPTIONS]

Modes:
  shell      Deploy in development shell (default)
             - Fastest for testing
             - Interactive terminal
             - GPU: Direct access
             
  systemd    Deploy as systemd service (requires root)
             - Persistent running service
             - Auto-restart on failure
             - GPU: Device access via systemd
             
  container  Build OCI container image
             - Docker-compatible
             - Portable deployment
             - GPU: Passed via --device

Options:
  MODEL_PATH=/path/to/model   Path to model directory
  GPU_MEM_UTIL=0.48          GPU memory utilization (0.0-1.0)

Examples:
  # Development shell with default model
  $0 shell
  
  # Development shell with custom model
  MODEL_PATH=/models/custom $0 shell
  
  # Production systemd service
  MODEL_PATH=/models/orchestrator/bf16 $0 systemd
  
  # Build OCI container
  $0 container

Environment:
  ARTIFACTS_DIR   Artifacts location (default: /home/nexus/amd-ai/artifacts)
  PROJECT_ROOT    Project root (auto-detected)

USAGE
}

# Main
main() {
  print_banner
  echo ""
  
  # Show usage if requested
  if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    show_usage
    exit 0
  fi
  
  # Verify nix is available
  if ! command -v nix &> /dev/null; then
    error "Nix not found. Please install Nix: https://nixos.org/download.html"
    exit 1
  fi
  
  info "Nix version: $(nix --version)"
  
  # Check artifacts
  check_artifacts
  echo ""
  
  # Deploy based on mode
  case "$DEPLOYMENT_MODE" in
    shell)
      deploy_shell
      ;;
    systemd)
      deploy_systemd
      ;;
    container)
      deploy_container
      ;;
    *)
      error "Unknown deployment mode: $DEPLOYMENT_MODE"
      echo ""
      show_usage
      exit 1
      ;;
  esac
}

# Run main
main "$@"
