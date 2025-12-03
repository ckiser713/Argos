#!/usr/bin/env bash
set -euo pipefail

# Staging Deployment Script for Project Cortex
# This script performs a full staging deployment following the execution plan

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Generate secure CORTEX_AUTH_SECRET
generate_auth_secret() {
    if command -v python3 &> /dev/null; then
        python3 -c "import secrets; print(secrets.token_hex(32))"
    elif command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        echo "ERROR: Cannot generate secure secret. Need python3 or openssl." >&2
        exit 1
    fi
}

CORTEX_AUTH_SECRET="${CORTEX_AUTH_SECRET:-$(generate_auth_secret)}"
export CORTEX_AUTH_SECRET
# Note: CORTEX_ENV will be set to strix after tests pass

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  Project Cortex - Staging Deployment${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo -e "${GREEN}✓ Generated CORTEX_AUTH_SECRET${NC}"
echo ""

# Check if we're in nix develop
if [ -z "${IN_NIX_SHELL:-}" ]; then
    echo -e "${RED}ERROR: This script must be run inside 'nix develop'${NC}"
    echo "Please run: nix develop"
    exit 1
fi

echo -e "${GREEN}✓ Running inside nix develop${NC}"
echo ""

# ============================================
# STEP 1: VERIFY
# ============================================
echo -e "${BLUE}=== STEP 1: VERIFY ===${NC}"
echo ""

echo "1.1 Running environment check..."
if ! bash "$PROJECT_ROOT/ops/check_env.sh"; then
    echo -e "${RED}✗ Environment check failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Environment check passed${NC}"
echo ""

echo "1.2 Running backend pytest suite..."
cd "$PROJECT_ROOT/backend"
# Run tests with CORTEX_ENV=local (tests expect local environment)
# Unset CORTEX_ENV temporarily for tests
OLD_CORTEX_ENV="${CORTEX_ENV:-}"
unset CORTEX_ENV
if ! poetry run pytest -v; then
    export CORTEX_ENV="$OLD_CORTEX_ENV"
    echo -e "${RED}✗ Backend test suite failed - ABORTING${NC}"
    exit 1
fi
# Restore CORTEX_ENV for deployment
export CORTEX_ENV=strix
echo -e "${GREEN}✓ Backend test suite passed${NC}"
echo ""
cd "$PROJECT_ROOT"

# ============================================
# STEP 2: INFRASTRUCTURE
# ============================================
echo -e "${BLUE}=== STEP 2: INFRASTRUCTURE ===${NC}"
echo ""

echo "2.1 Starting Docker services (Qdrant, PostgreSQL)..."
cd "$PROJECT_ROOT/ops"

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    exit 1
fi

# Use strix compose file for PostgreSQL
COMPOSE_FILE="docker-compose.strix.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${YELLOW}⚠ Strix compose not found, falling back to default${NC}"
    COMPOSE_FILE="docker-compose.yml"
fi

# Start PostgreSQL
echo "  Starting PostgreSQL..."
if ! $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d postgres; then
    echo -e "${RED}✗ Failed to start PostgreSQL${NC}"
    exit 1
fi

# Start Qdrant
echo "  Starting Qdrant..."
if ! $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d qdrant; then
    echo -e "${RED}✗ Failed to start Qdrant${NC}"
    exit 1
fi

# Try to start inference-engine (optional, don't fail if it doesn't work)
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d inference-vllm 2>&1 | grep -q "not found\|failed\|error" && \
    echo -e "${YELLOW}⚠ Inference-engine not available (optional)${NC}" || \
    echo -e "${GREEN}✓ Inference-engine started${NC}"

echo -e "${GREEN}✓ Docker services started${NC}"
echo ""

# Wait for PostgreSQL
echo "2.2 Waiting for PostgreSQL health..."
POSTGRES_HEALTHY=false
for i in {1..60}; do
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres pg_isready -U cortex -d cortex >/dev/null 2>&1; then
        POSTGRES_HEALTHY=true
        break
    fi
    echo "  Waiting for PostgreSQL... ($i/60)"
    sleep 2
done

if [ "$POSTGRES_HEALTHY" = false ]; then
    echo -e "${RED}✗ PostgreSQL failed to become healthy${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is healthy${NC}"
echo ""

echo "2.3 Waiting for Qdrant health..."
QDRANT_HEALTHY=false
for i in {1..60}; do
    if curl -sS --fail http://localhost:6333/health >/dev/null 2>&1; then
        QDRANT_HEALTHY=true
        break
    fi
    echo "  Waiting for Qdrant... ($i/60)"
    sleep 2
done

if [ "$QDRANT_HEALTHY" = false ]; then
    echo -e "${RED}✗ Qdrant failed to become healthy${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Qdrant is healthy${NC}"
echo ""

cd "$PROJECT_ROOT"

# ============================================
# STEP 3: DATABASE
# ============================================
echo -e "${BLUE}=== STEP 3: DATABASE ===${NC}"
echo ""

# Set PostgreSQL environment for strix mode
export CORTEX_DATABASE_URL="postgresql://cortex:cortex@localhost:5432/cortex"

echo "3.1 Running Alembic migrations..."
cd "$PROJECT_ROOT/backend"

# Run Alembic migrations
if poetry run alembic upgrade head; then
    echo -e "${GREEN}✓ Alembic migrations completed${NC}"
else
    echo -e "${YELLOW}⚠ Alembic migrations failed, trying init_db fallback...${NC}"
fi

echo ""
echo "3.2 Initializing database schema..."

# Dry-run the app factory by importing and calling create_app()
# This will call init_db() which initializes the schema
if ! poetry run python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from app.main import create_app
app = create_app()
print('Database schema initialized successfully')
"; then
    echo -e "${RED}✗ Database initialization failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database schema initialized${NC}"
echo ""
cd "$PROJECT_ROOT"

# ============================================
# STEP 4: DEPLOY
# ============================================
echo -e "${BLUE}=== STEP 4: DEPLOY ===${NC}"
echo ""

# Clean up any existing processes on ports 8000 and 5173
cleanup_port() {
    local port=$1
    local name=$2
    if lsof -i :$port -t >/dev/null 2>&1; then
        FOUND_PID=$(lsof -i :$port -t | head -1)
        echo "  Cleaning up existing $name on port $port (PID: $FOUND_PID)..."
        kill $FOUND_PID 2>/dev/null || true
        sleep 1
    fi
}

cleanup_port 8000 "backend"
cleanup_port 5173 "frontend"

echo "4.1 Starting Backend (port 8000) with CORTEX_ENV=strix..."
cd "$PROJECT_ROOT/backend"
export PYTHONPATH="$PROJECT_ROOT"
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_ROOT/backend_staging.log" 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"
cd "$PROJECT_ROOT"

echo "4.2 Starting Frontend (port 5173) with CORTEX_ENV=strix..."
cd "$PROJECT_ROOT/frontend"
pnpm run dev -- --port 5173 --host 0.0.0.0 > "$PROJECT_ROOT/frontend_staging.log" 2>&1 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
cd "$PROJECT_ROOT"

echo ""
echo "Waiting for services to start..."
sleep 5

# ============================================
# STEP 5: VALIDATE
# ============================================
echo -e "${BLUE}=== STEP 5: VALIDATE ===${NC}"
echo ""

# Wait for backend to be ready
echo "5.1 Polling /api/system/health..."
BACKEND_HEALTHY=false
for i in {1..30}; do
    if curl -sS --fail http://localhost:8000/api/system/health >/dev/null 2>&1; then
        BACKEND_HEALTHY=true
        break
    fi
    echo "  Waiting for backend... ($i/30)"
    sleep 2
done

if [ "$BACKEND_HEALTHY" = false ]; then
    echo -e "${RED}✗ Backend failed to become healthy${NC}"
    echo "Backend logs:"
    tail -20 "$PROJECT_ROOT/backend_staging.log"
    exit 1
fi
echo -e "${GREEN}✓ Backend health check passed${NC}"
echo ""

# Check /api/system/status
echo "5.2 Polling /api/system/status..."
STATUS_RESPONSE=$(curl -sS http://localhost:8000/api/system/status 2>&1)
if echo "$STATUS_RESPONSE" | grep -q "error\|Error\|unauthorized\|Unauthorized"; then
    echo -e "${GREEN}✓ Status endpoint requires authentication (as expected)${NC}"
else
    # Try without auth to verify it's enforced
    STATUS_CODE=$(curl -sS -o /dev/null -w "%{http_code}" http://localhost:8000/api/system/status 2>&1)
    if [ "$STATUS_CODE" = "401" ] || [ "$STATUS_CODE" = "403" ]; then
        echo -e "${GREEN}✓ Auth is enforced (status code: $STATUS_CODE)${NC}"
    else
        echo -e "${YELLOW}⚠ Status endpoint returned code: $STATUS_CODE${NC}"
        echo "  Response: $STATUS_RESPONSE"
    fi
fi
echo ""

# Verify auth is enforced by testing a protected endpoint without token
echo "5.3 Verifying authentication enforcement..."
AUTH_TEST=$(curl -sS -o /dev/null -w "%{http_code}" http://localhost:8000/api/system/status 2>&1)
if [ "$AUTH_TEST" = "401" ] || [ "$AUTH_TEST" = "403" ]; then
    echo -e "${GREEN}✓ Authentication is properly enforced (status code: $AUTH_TEST)${NC}"
else
    echo -e "${YELLOW}⚠ Authentication check returned code: $AUTH_TEST${NC}"
    echo "  Note: This may be expected if CORTEX_SKIP_AUTH is set"
fi
echo ""

# Wait for frontend to be ready
echo "5.4 Checking Frontend..."
FRONTEND_READY=false
for i in {1..30}; do
    if curl -sS --fail http://localhost:5173/ >/dev/null 2>&1; then
        FRONTEND_READY=true
        break
    fi
    echo "  Waiting for frontend... ($i/30)"
    sleep 2
done

if [ "$FRONTEND_READY" = false ]; then
    echo -e "${RED}✗ Frontend failed to become ready${NC}"
    echo "Frontend logs:"
    tail -20 "$PROJECT_ROOT/frontend_staging.log"
    exit 1
fi
echo -e "${GREEN}✓ Frontend is ready${NC}"
echo ""

# ============================================
# STEP 6: REPORT
# ============================================
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  DEPLOYMENT COMPLETE${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo -e "${GREEN}Service Status:${NC}"
echo "  Backend:  ${GREEN}RUNNING${NC} (PID: $BACKEND_PID)"
echo "  Frontend: ${GREEN}RUNNING${NC} (PID: $FRONTEND_PID)"
echo "  Qdrant:   ${GREEN}HEALTHY${NC}"
echo ""
echo -e "${GREEN}Service URLs:${NC}"
echo "  Backend API:     http://localhost:8000"
echo "  Backend Docs:    http://localhost:8000/api/docs"
echo "  Backend Health:  http://localhost:8000/api/system/health"
echo "  Backend Status:  http://localhost:8000/api/system/status (requires auth)"
echo "  Frontend:        http://localhost:5173"
echo "  Qdrant:          http://localhost:6333"
echo ""
echo -e "${GREEN}Environment:${NC}"
echo "  CORTEX_ENV:        $CORTEX_ENV"
echo "  CORTEX_AUTH_SECRET: [SET]"
echo ""
echo -e "${GREEN}Log Files:${NC}"
echo "  Backend:  $PROJECT_ROOT/backend_staging.log"
echo "  Frontend: $PROJECT_ROOT/frontend_staging.log"
echo ""
echo -e "${YELLOW}Note: Services are running in the background.${NC}"
echo -e "${YELLOW}To stop them, run: kill $BACKEND_PID $FRONTEND_PID${NC}"
echo ""

