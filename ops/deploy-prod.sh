#!/usr/bin/env bash
# =============================================================================
# Cortex Production Deployment Script
# =============================================================================
# Complete production deployment for Strix Halo with PostgreSQL.
#
# Usage:
#   ./ops/deploy-prod.sh [--skip-models] [--skip-build] [--dry-run]
#
# Prerequisites:
#   - Copy ../.env.example to ../.env and configure all required values
#   - Ensure Docker and Docker Compose are installed
#   - For model download: Set HF_TOKEN in environment
#
# This script will:
#   1. Validate environment configuration
#   2. Download models (if not skipped)
#   3. Build Docker images
#   4. Start all services
#   5. Run database migrations
#   6. Verify deployment health
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

# Default options
SKIP_MODELS=false
SKIP_BUILD=false
DRY_RUN=false
COMPOSE_FILE="docker-compose.prod.yml"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-models)
            SKIP_MODELS=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--skip-models] [--skip-build] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --skip-models  Skip model download"
            echo "  --skip-build   Skip Docker image build"
            echo "  --dry-run      Show what would be done without executing"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Header
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Cortex Production Deployment (Strix Halo)            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_ROOT"

# =============================================================================
# STEP 1: Validate Environment
# =============================================================================
log "Step 1: Validating environment configuration..."

# Check for .env file
if [ ! -f ".env" ]; then
    log_error ".env file not found!"
    echo "  Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    exit 1
fi

# Source .env file
set -a
source .env
set +a

# Validate required variables
REQUIRED_VARS=(
    "CORTEX_AUTH_SECRET"
    "POSTGRES_PASSWORD"
    "CORTEX_DOMAIN"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

log_success "Environment configuration valid"

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker."
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker daemon not running or insufficient permissions."
    exit 1
fi

log_success "Docker is available"

# Determine docker compose command
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

log_success "Using: $DOCKER_COMPOSE"
echo ""

# =============================================================================
# STEP 2: Download Models (if not skipped)
# =============================================================================
if [ "$SKIP_MODELS" = false ]; then
    log "Step 2: Checking/downloading models..."
    
    MODELS_DIR="${MODELS_PATH:-/data/cortex-models}"
    
    if [ ! -d "$MODELS_DIR" ]; then
        log_warning "Models directory not found: $MODELS_DIR"
        echo "  Creating directory..."
        
        if [ "$DRY_RUN" = false ]; then
            sudo mkdir -p "$MODELS_DIR"
            sudo chown -R "$(id -u):$(id -g)" "$MODELS_DIR"
        else
            echo "  [DRY RUN] Would create: $MODELS_DIR"
        fi
    fi
    
    # Check if models exist
    VLLM_MODELS="$MODELS_DIR/vllm"
    GGUF_MODELS="$MODELS_DIR/gguf"
    
    if [ -d "$VLLM_MODELS" ] && [ -d "$GGUF_MODELS" ]; then
        log_success "Models directory exists with content"
    else
        log_warning "Models not found. Running download script..."
        
        if [ -z "${HF_TOKEN:-}" ]; then
            log_warning "HF_TOKEN not set. Some models may fail to download."
        fi
        
        if [ "$DRY_RUN" = false ]; then
            export MODELS_DIR
            bash "$SCRIPT_DIR/download_all_models.sh" || {
                log_warning "Model download had issues. Check output above."
            }
        else
            echo "  [DRY RUN] Would run: download_all_models.sh"
        fi
    fi
    
    log_success "Model check complete"
else
    log "Step 2: Skipping model download (--skip-models)"
fi
echo ""

# =============================================================================
# STEP 3: Build Docker Images (if not skipped)
# =============================================================================
if [ "$SKIP_BUILD" = false ]; then
    log "Step 3: Building Docker images..."
    
    cd "$SCRIPT_DIR"
    
    if [ "$DRY_RUN" = false ]; then
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" build --parallel backend frontend-builder
    else
        echo "  [DRY RUN] Would build: backend, frontend-builder"
    fi
    
    log_success "Docker images built"
else
    log "Step 3: Skipping Docker build (--skip-build)"
fi
echo ""

# =============================================================================
# STEP 4: Start Services
# =============================================================================
log "Step 4: Starting services..."

cd "$SCRIPT_DIR"

if [ "$DRY_RUN" = false ]; then
    # Start infrastructure services first
    log "  Starting PostgreSQL and Qdrant..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d postgres qdrant
    
    # Wait for PostgreSQL
    log "  Waiting for PostgreSQL to be ready..."
    for i in {1..60}; do
        if $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T postgres pg_isready -U cortex -d cortex &> /dev/null; then
            break
        fi
        sleep 2
    done
    
    # Run migrations
    log "  Running database migrations..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up migrations
    
    # Start remaining services
    log "  Starting remaining services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
else
    echo "  [DRY RUN] Would start all services"
fi

log_success "Services started"
echo ""

# =============================================================================
# STEP 5: Verify Deployment
# =============================================================================
log "Step 5: Verifying deployment health..."

if [ "$DRY_RUN" = false ]; then
    # Give services time to start
    sleep 10
    
    # Check each service
    SERVICES_OK=true
    
    # PostgreSQL
    if $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T postgres pg_isready -U cortex -d cortex &> /dev/null; then
        log_success "PostgreSQL is healthy"
    else
        log_error "PostgreSQL is not healthy"
        SERVICES_OK=false
    fi
    
    # Qdrant
    if curl -sf http://localhost:6333/health &> /dev/null; then
        log_success "Qdrant is healthy"
    else
        log_error "Qdrant is not healthy"
        SERVICES_OK=false
    fi
    
    # Backend
    if curl -sf http://localhost:8000/api/system/health &> /dev/null; then
        log_success "Backend is healthy"
    else
        log_warning "Backend not responding yet (may still be starting)"
    fi
    
    # Caddy
    if curl -sf http://localhost/health &> /dev/null; then
        log_success "Caddy is healthy"
    else
        log_warning "Caddy not responding yet (may still be starting)"
    fi
    
    if [ "$SERVICES_OK" = false ]; then
        log_error "Some services failed health checks"
        echo ""
        echo "Check logs with:"
        echo "  $DOCKER_COMPOSE -f $COMPOSE_FILE logs"
        exit 1
    fi
else
    echo "  [DRY RUN] Would verify service health"
fi
echo ""

# =============================================================================
# Deployment Complete
# =============================================================================
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Deployment Complete!                            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Service URLs:${NC}"
echo "  Frontend:     https://${CORTEX_DOMAIN}"
echo "  Backend API:  https://${CORTEX_DOMAIN}/api"
echo "  API Docs:     https://${CORTEX_DOMAIN}/api/docs"
echo "  n8n:          https://${CORTEX_DOMAIN}/n8n"
echo ""
echo -e "${GREEN}Management Commands:${NC}"
echo "  View logs:    $DOCKER_COMPOSE -f ops/$COMPOSE_FILE logs -f"
echo "  Stop:         $DOCKER_COMPOSE -f ops/$COMPOSE_FILE down"
echo "  Restart:      $DOCKER_COMPOSE -f ops/$COMPOSE_FILE restart"
echo "  Status:       $DOCKER_COMPOSE -f ops/$COMPOSE_FILE ps"
echo ""
echo -e "${GREEN}Database:${NC}"
echo "  Connect:      docker exec -it cortex-postgres psql -U cortex -d cortex"
echo "  Backup:       docker exec cortex-postgres pg_dump -U cortex cortex > backup.sql"
echo ""
