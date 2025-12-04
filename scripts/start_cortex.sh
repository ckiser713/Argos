#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Cortex AI Platform - Startup Script for Strix (AMD Ryzen AI Max+ / ROCm 7.1.1)
# ═══════════════════════════════════════════════════════════════════════════════
# This script starts all Cortex services in the correct order:
#   1. Docker services (vLLM, llama-servers, Qdrant)
#   2. Backend (FastAPI)
#   3. Frontend (Vite dev server)
#
# Usage:
#   ./scripts/start_cortex.sh [--dev|--staging|--docker-only]
#
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from .env file
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

set -euo pipefail

# Detect docker-compose command (v2 plugin or v1 standalone)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ───────────────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ───────────────────────────────────────────────────────────────────────────────

check_prerequisites() {
    log_info "Running pre-flight checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check docker compose (already detected at script start)
    if [ -z "$DOCKER_COMPOSE" ]; then
        log_error "Neither 'docker compose' nor 'docker-compose' is available."
        exit 1
    fi
    log_success "Using: $DOCKER_COMPOSE"
    
    # Check ROCm (optional but recommended)
    if [ -d "/opt/rocm" ]; then
        ROCM_VERSION=$(cat /opt/rocm/.info/version 2>/dev/null || echo "unknown")
        log_success "ROCm detected: version $ROCM_VERSION"
    else
        log_warn "ROCm not found at /opt/rocm - GPU acceleration may not work"
    fi
    
    # Check HSA environment
    if [ -z "${HSA_OVERRIDE_GFX_VERSION:-}" ]; then
        log_info "HSA_OVERRIDE_GFX_VERSION not set. Using native GPU detection for recompiled binaries."
        # Removed HSA_OVERRIDE_GFX_VERSION setting to allow recompiled binaries to work with native GPU detection
    fi
    
    # Verify model files exist
    check_models
    
    log_success "Pre-flight checks passed"
}

check_models() {
    log_info "Checking model files..."
    
    local MODELS_DIR="$PROJECT_ROOT/models"
    local missing=0
    
    # Check GGUF models for llama-server
    local GGUF_MODELS=(
        "gguf/qwen2.5-coder-14b-instruct-q4_k_m.gguf"
        "gguf/phi-4-q4_k_m.gguf"
    )
    
    for model in "${GGUF_MODELS[@]}"; do
        if [ ! -f "$MODELS_DIR/$model" ]; then
            log_warn "Missing GGUF model: $model"
            ((missing++)) || true
        else
            log_success "Found: $model"
        fi
    done
    
    # Check vLLM model directories
    local VLLM_MODELS=(
        "vllm/Qwen2.5-Coder-14B-Instruct"
    )
    
    for model in "${VLLM_MODELS[@]}"; do
        if [ ! -d "$MODELS_DIR/$model" ]; then
            log_warn "Missing vLLM model: $model"
            ((missing++)) || true
        else
            log_success "Found: $model"
        fi
    done
    
    if [ $missing -gt 0 ]; then
        log_warn "$missing model(s) missing. Run 'python3 download_remaining_models.py' to download."
    fi
}

# ───────────────────────────────────────────────────────────────────────────────
# Docker Services
# ───────────────────────────────────────────────────────────────────────────────

start_docker_services() {
    log_info "Starting Docker services (vLLM, Qdrant, PostgreSQL, n8n)..."
    
    cd "$PROJECT_ROOT"
    
    # Use the Strix-specific docker-compose
    local COMPOSE_FILE="ops/docker-compose.strix.yml"
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Pull latest images if needed
    log_info "Pulling latest images..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" pull --ignore-pull-failures || true
    
    # Start services
    log_info "Starting containers..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
    
    # Start native llama.cpp servers
    log_info "Starting native llama.cpp servers..."
    ./scripts/start_llama_servers.sh start
    
    # Wait for services to be healthy
    wait_for_services
    
    log_success "Docker services and llama servers started"
}

wait_for_services() {
    log_info "Waiting for services to become healthy..."
    
    local MAX_WAIT=180  # 3 minutes
    local INTERVAL=5
    local elapsed=0
    
    # Services to check
    local SERVICES=(
        "localhost:6333:Qdrant"
        "localhost:8080:llama-super-reader"
        "localhost:8081:llama-governance"
        "localhost:8000:vLLM"
    )
    
    for service in "${SERVICES[@]}"; do
        IFS=':' read -r host port name <<< "$service"
        log_info "Waiting for $name on port $port..."
        
        while ! nc -z "$host" "$port" 2>/dev/null; do
            sleep "$INTERVAL"
            ((elapsed+=INTERVAL))
            if [ $elapsed -ge $MAX_WAIT ]; then
                log_warn "$name did not become healthy within ${MAX_WAIT}s"
                break
            fi
        done
        
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "$name is ready"
        fi
    done
}

stop_docker_services() {
    log_info "Stopping Docker services..."
    cd "$PROJECT_ROOT"
    $DOCKER_COMPOSE -f "ops/docker-compose.strix.yml" down
    
    log_info "Stopping native llama.cpp servers..."
    ./scripts/start_llama_servers.sh --stop
    
    log_success "Docker services and llama servers stopped"
}

# ───────────────────────────────────────────────────────────────────────────────
# Backend Service
# ───────────────────────────────────────────────────────────────────────────────

start_backend() {
    log_info "Starting FastAPI backend..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Activate virtual environment if it exists
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    
    # Set environment variables
    export CORTEX_ENV="${CORTEX_ENV:-development}"
    export DATABASE_URL="${DATABASE_URL:-sqlite:///./cortex.db}"
    export QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
    export LANE_ORCHESTRATOR_URL="${LANE_ORCHESTRATOR_URL:-http://localhost:8000/v1}"
    export LANE_CODER_URL="${LANE_CODER_URL:-http://localhost:8000/v1}"
    export LANE_FAST_RAG_URL="${LANE_FAST_RAG_URL:-http://localhost:8000/v1}"
    export LANE_SUPER_READER_URL="${LANE_SUPER_READER_URL:-http://localhost:8080/v1}"
    export LANE_GOVERNANCE_URL="${LANE_GOVERNANCE_URL:-http://localhost:8081/v1}"
    
    # Run database migrations
    log_info "Running database migrations..."
    python3 -m alembic upgrade head || log_warn "Migration failed or already up to date"
    
    # Start uvicorn in background
    log_info "Starting uvicorn server on port 8088..."
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload &
    BACKEND_PID=$!
    
    # Save PID for cleanup
    echo $BACKEND_PID > "$PROJECT_ROOT/.backend.pid"
    
    # Wait for backend to start
    sleep 3
    if kill -0 $BACKEND_PID 2>/dev/null; then
        log_success "Backend started (PID: $BACKEND_PID)"
    else
        log_error "Backend failed to start"
        exit 1
    fi
}

stop_backend() {
    log_info "Stopping backend..."
    if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
        kill $(cat "$PROJECT_ROOT/.backend.pid") 2>/dev/null || true
        rm "$PROJECT_ROOT/.backend.pid"
    fi
    log_success "Backend stopped"
}

# ───────────────────────────────────────────────────────────────────────────────
# Frontend Service
# ───────────────────────────────────────────────────────────────────────────────

start_frontend() {
    log_info "Starting Vite frontend..."
    
    cd "$PROJECT_ROOT/frontend"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        pnpm install
    fi
    
    # Start Vite dev server in background
    log_info "Starting Vite on port 5173..."
    pnpm dev &
    FRONTEND_PID=$!
    
    # Save PID for cleanup
    echo $FRONTEND_PID > "$PROJECT_ROOT/.frontend.pid"
    
    sleep 3
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        log_success "Frontend started (PID: $FRONTEND_PID)"
    else
        log_error "Frontend failed to start"
        exit 1
    fi
}

stop_frontend() {
    log_info "Stopping frontend..."
    if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
        kill $(cat "$PROJECT_ROOT/.frontend.pid") 2>/dev/null || true
        rm "$PROJECT_ROOT/.frontend.pid"
    fi
    log_success "Frontend stopped"
}

# ───────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ───────────────────────────────────────────────────────────────────────────────

print_banner() {
    echo -e "${CYAN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "   ██████╗ ██████╗ ██████╗ ████████╗███████╗██╗  ██╗"
    echo "  ██╔════╝██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝"
    echo "  ██║     ██║   ██║██████╔╝   ██║   █████╗   ╚███╔╝ "
    echo "  ██║     ██║   ██║██╔══██╗   ██║   ██╔══╝   ██╔██╗ "
    echo "  ╚██████╗╚██████╔╝██║  ██║   ██║   ███████╗██╔╝ ██╗"
    echo "   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo "   AI-Integrated Knowledge & Execution Engine"
    echo "   ROCm 7.1.1 | gfx1151 (Strix Point)"
    echo ""
}

print_status() {
    echo ""
    log_info "Service Status:"
    echo "  • Qdrant:           http://localhost:6333"
    echo "  • vLLM:             http://localhost:8000"
    echo "  • llama-super-reader: http://localhost:8080"
    echo "  • llama-governance: http://localhost:8081"
    echo "  • Backend API:      http://localhost:8088"
    echo "  • Frontend:         http://localhost:5173"
    echo ""
    log_success "Cortex is ready!"
    echo ""
    echo "To stop all services: $0 --stop"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev         Start all services in development mode (default)"
    echo "  --staging     Start all services in staging mode"
    echo "  --docker-only Start only Docker services (no backend/frontend)"
    echo "  --stop        Stop all services"
    echo "  --status      Show status of all services"
    echo "  --help        Show this help message"
}

main() {
    local MODE="${1:-dev}"
    
    case "$MODE" in
        --dev|dev)
            print_banner
            check_prerequisites
            start_docker_services
            start_backend
            start_frontend
            print_status
            ;;
        --staging|staging)
            export CORTEX_ENV="staging"
            print_banner
            check_prerequisites
            start_docker_services
            start_backend
            print_status
            ;;
        --docker-only)
            print_banner
            check_prerequisites
            start_docker_services
            log_success "Docker services running. Backend/frontend not started."
            ;;
        --stop)
            stop_frontend
            stop_backend
            stop_docker_services
            log_success "All services stopped"
            ;;
        --status)
            echo "Docker services:"
            $DOCKER_COMPOSE -f "$PROJECT_ROOT/ops/docker-compose.strix.yml" ps
            echo ""
            echo "Backend PID:"
            cat "$PROJECT_ROOT/.backend.pid" 2>/dev/null || echo "Not running"
            echo ""
            echo "Frontend PID:"
            cat "$PROJECT_ROOT/.frontend.pid" 2>/dev/null || echo "Not running"
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $MODE"
            usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo ""; log_warn "Interrupted. Run \"$0 --stop\" to stop services."; exit 130' INT

main "$@"
