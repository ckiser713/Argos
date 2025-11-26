#!/usr/bin/env bash
# Nix-based deployment script for Cortex services
# Usage: ./nix-deploy.sh [start|stop|restart|status|logs]

set -e

# Don't exit on errors in some cases - we'll handle them explicitly
set +e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-start}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Source Nix profile if available
if [ -f ~/.nix-profile/etc/profile.d/nix.sh ]; then
    source ~/.nix-profile/etc/profile.d/nix.sh
elif [ -f /nix/var/nix/profiles/default/etc/profile.d/nix.sh ]; then
    source /nix/var/nix/profiles/default/etc/profile.d/nix.sh
fi

# Check if Nix is available
if ! command -v nix &> /dev/null; then
    echo -e "${RED}Error: Nix is not installed or not in PATH${NC}"
    echo "Please install Nix: https://nixos.org/download.html"
    echo "Or source the Nix profile: source ~/.nix-profile/etc/profile.d/nix.sh"
    exit 1
fi

# Check if we're in a Nix shell or have flakes enabled
if ! nix flake show . &> /dev/null; then
    echo -e "${YELLOW}Warning: Flakes might not be enabled${NC}"
    echo "Run: mkdir -p ~/.config/nix && echo 'experimental-features = nix-command flakes' >> ~/.config/nix/nix.conf"
fi

# Detect docker-compose command
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo -e "${RED}Error: docker-compose not found${NC}"
    echo "Please install docker-compose or use Docker with compose plugin"
    exit 1
fi

# Function to cleanup existing Qdrant containers
cleanup_qdrant_containers() {
    echo "   Cleaning up existing Qdrant containers..."
    # Find all Qdrant containers (by name or image)
    local containers=$(docker ps -a --filter "name=qdrant" --format "{{.ID}}" 2>/dev/null)
    containers="$containers $(docker ps -a --filter "ancestor=qdrant/qdrant:latest" --format "{{.ID}}" 2>/dev/null)"
    
    for container in $containers; do
        if [ -n "$container" ]; then
            echo "     Removing container $container..."
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        fi
    done
}

# Function to start only Qdrant (skip inference-engine if it fails)
start_qdrant_only() {
    echo "Starting Qdrant service only..."
    
    # Clean up any existing Qdrant containers first
    cleanup_qdrant_containers
    
    # Try docker-compose first
    if $DOCKER_COMPOSE_CMD -f "$PROJECT_ROOT/ops/docker-compose.yml" up -d qdrant 2>&1 | grep -q "ERROR\|Error\|failed"; then
        echo -e "${YELLOW}⚠ docker-compose failed, trying direct docker run...${NC}"
        # Create storage directory if it doesn't exist
        mkdir -p "$PROJECT_ROOT/ops/qdrant_storage"
        docker run -d --name qdrant \
            -p 6333:6333 \
            -p 6334:6334 \
            -v "$PROJECT_ROOT/ops/qdrant_storage:/qdrant/storage" \
            qdrant/qdrant:latest || {
            echo -e "${RED}✗ Failed to start Qdrant${NC}"
            return 1
        }
    fi
}

case "$ACTION" in
    start)
        echo -e "${GREEN}=== Starting Cortex Services ===${NC}"
        echo ""
        
        echo "1. Starting Docker services..."
        echo "   Starting Qdrant..."
        if start_qdrant_only; then
            echo -e "${GREEN}✓ Qdrant started${NC}"
        else
            echo -e "${RED}✗ Failed to start Qdrant${NC}"
            echo "   Trying to clean up and retry..."
            docker stop qdrant ops-qdrant-1 2>/dev/null || true
            docker rm qdrant ops-qdrant-1 2>/dev/null || true
            sleep 2
            if start_qdrant_only; then
                echo -e "${GREEN}✓ Qdrant started after cleanup${NC}"
            else
                echo -e "${RED}✗ Failed to start Qdrant after retry${NC}"
                echo -e "${YELLOW}You may need to manually clean up containers:${NC}"
                echo "   docker ps -a | grep qdrant"
                echo "   docker rm -f <container-id>"
                exit 1
            fi
        fi
        
        # Try to start inference-engine (optional, don't fail if it doesn't work)
        echo "   Attempting to start inference-engine (optional)..."
        if $DOCKER_COMPOSE_CMD -f "$PROJECT_ROOT/ops/docker-compose.yml" up -d inference-engine 2>&1 | grep -q "not found\|failed"; then
            echo -e "${YELLOW}⚠ Inference-engine not available (ROCm image not found) - skipping${NC}"
            echo "   This is optional and won't affect other services"
        else
            echo -e "${GREEN}✓ Inference-engine started${NC}"
        fi
        echo ""
        
        echo "2. Installing dependencies..."
        echo "   Backend dependencies..."
        cd "$PROJECT_ROOT/backend"
        if command -v poetry &> /dev/null; then
            poetry install --no-dev || echo -e "${YELLOW}⚠ Backend dependencies may need manual installation${NC}"
        else
            echo -e "${YELLOW}⚠ Poetry not found - skipping backend dependency installation${NC}"
        fi
        
        echo "   Frontend dependencies..."
        cd "$PROJECT_ROOT/frontend"
        if command -v pnpm &> /dev/null; then
            pnpm install || echo -e "${YELLOW}⚠ Frontend dependencies may need manual installation${NC}"
        else
            echo -e "${YELLOW}⚠ pnpm not found - skipping frontend dependency installation${NC}"
        fi
        echo ""
        
        echo "3. Starting backend service..."
        echo -e "${YELLOW}   Run in separate terminal:${NC}"
        echo -e "${YELLOW}   cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000${NC}"
        echo ""
        
        echo "4. Starting frontend service..."
        echo -e "${YELLOW}   Run in separate terminal:${NC}"
        echo -e "${YELLOW}   cd frontend && pnpm dev${NC}"
        echo -e "${YELLOW}   (Frontend runs on port 3000 by default)${NC}"
        echo ""
        
        echo -e "${GREEN}=== Services Started ===${NC}"
        echo ""
        echo "Services available at:"
        echo "  - Qdrant: http://localhost:6333"
        echo "  - Backend API: http://localhost:8000"
        echo "  - Backend Docs: http://localhost:8000/api/docs"
        echo "  - Frontend: http://localhost:3000 (start with: cd frontend && pnpm dev)"
        ;;
        
    stop)
        echo -e "${YELLOW}=== Stopping Cortex Services ===${NC}"
        echo ""
        
        echo "Stopping Docker services..."
        $DOCKER_COMPOSE_CMD -f "$PROJECT_ROOT/ops/docker-compose.yml" down 2>/dev/null || {
            # Try stopping individual containers
            docker stop qdrant 2>/dev/null || true
            docker rm qdrant 2>/dev/null || true
        }
        echo -e "${GREEN}✓ Docker services stopped${NC}"
        echo ""
        echo -e "${YELLOW}Note: Backend and frontend services need to be stopped manually${NC}"
        echo "  (Ctrl+C in their respective terminals)"
        ;;
        
    restart)
        echo -e "${YELLOW}=== Restarting Cortex Services ===${NC}"
        "$0" stop
        sleep 2
        "$0" start
        ;;
        
    status)
        echo -e "${GREEN}=== Cortex Services Status ===${NC}"
        echo ""
        
        # Check Docker services
        echo "Docker Services:"
        if $DOCKER_COMPOSE_CMD -f "$PROJECT_ROOT/ops/docker-compose.yml" ps 2>/dev/null | grep -q "Up"; then
            echo -e "  ${GREEN}✓ Running${NC}"
            $DOCKER_COMPOSE_CMD -f "$PROJECT_ROOT/ops/docker-compose.yml" ps
        elif docker ps --filter "name=qdrant" --format "{{.Names}}" | grep -q qdrant; then
            echo -e "  ${GREEN}✓ Qdrant running (standalone)${NC}"
            docker ps --filter "name=qdrant"
        else
            echo -e "  ${RED}✗ Not running${NC}"
        fi
        echo ""
        
        # Check backend
        echo "Backend API:"
        if curl -s http://localhost:8000/api/docs > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Running on http://localhost:8000${NC}"
        else
            echo -e "  ${RED}✗ Not running${NC}"
        fi
        echo ""
        
        # Check frontend (Vite default port is 3000)
        echo "Frontend:"
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Running on http://localhost:3000${NC}"
        elif curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Running on http://localhost:5173${NC}"
        else
            echo -e "  ${RED}✗ Not running${NC}"
            echo -e "  ${YELLOW}Start with: cd frontend && pnpm dev${NC}"
        fi
        ;;
        
    logs)
        echo -e "${GREEN}=== Cortex Services Logs ===${NC}"
        echo ""
        echo "Docker services logs:"
        $DOCKER_COMPOSE_CMD -f "$PROJECT_ROOT/ops/docker-compose.yml" logs -f 2>/dev/null || {
            echo "Showing Qdrant logs:"
            local qdrant_container=$(docker ps --filter "ancestor=qdrant/qdrant:latest" --format "{{.ID}}" | head -1)
            if [ -n "$qdrant_container" ]; then
                docker logs -f "$qdrant_container"
            else
                echo "No Qdrant container found"
            fi
        }
        ;;
        
    cleanup)
        echo -e "${YELLOW}=== Cleaning Up Docker Containers ===${NC}"
        echo ""
        cleanup_qdrant_containers
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
        
    systemd)
        echo -e "${GREEN}=== Installing Systemd Services ===${NC}"
        echo ""
        echo "For NixOS systems, add to your configuration.nix:"
        echo ""
        echo "  imports = ["
        echo "    $(nix flake show .#nixosModules.default)"
        echo "  ];"
        echo ""
        echo "Then rebuild:"
        echo "  sudo nixos-rebuild switch --flake .#your-hostname"
        echo ""
        echo "Or for non-NixOS systems, you can manually create systemd service files"
        echo "based on nix/services.nix"
        ;;
        
    cleanup)
        echo -e "${YELLOW}=== Cleaning Up Docker Containers ===${NC}"
        echo ""
        cleanup_qdrant_containers
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
        
    *)
        echo "Usage: $0 [start|stop|restart|status|logs|cleanup|systemd]"
        echo ""
        echo "Commands:"
        echo "  start    - Start all Cortex services"
        echo "  stop     - Stop all Cortex services"
        echo "  restart  - Restart all Cortex services"
        echo "  status   - Show status of all services"
        echo "  logs     - Show Docker services logs"
        echo "  cleanup  - Clean up existing Docker containers"
        echo "  systemd  - Show instructions for systemd deployment"
        exit 1
        ;;
esac

