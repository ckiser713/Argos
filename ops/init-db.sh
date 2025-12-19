#!/usr/bin/env bash
# =============================================================================
# Cortex Database Initialization Script
# =============================================================================
# This script initializes the PostgreSQL database and runs Alembic migrations.
# It's designed to be run before starting the backend service.
#
# Usage:
#   ./ops/init-db.sh [--wait] [--migrate-only]
#
# Options:
#   --wait         Wait for PostgreSQL to be ready before proceeding
#   --migrate-only Only run migrations, skip other initialization
#
# Environment Variables:
#   ARGOS_DATABASE_URL  - PostgreSQL connection URL
#   POSTGRES_HOST        - PostgreSQL host (default: localhost)
#   POSTGRES_PORT        - PostgreSQL port (default: 5432)
#   POSTGRES_USER        - PostgreSQL user (default: cortex)
#   POSTGRES_DB          - PostgreSQL database (default: cortex)
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

# Default values
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-argos}"
POSTGRES_DB="${POSTGRES_DB:-argos}"
WAIT_FOR_DB=false
MIGRATE_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --wait)
            WAIT_FOR_DB=true
            shift
            ;;
        --migrate-only)
            MIGRATE_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--wait] [--migrate-only]"
            echo ""
            echo "Options:"
            echo "  --wait         Wait for PostgreSQL to be ready"
            echo "  --migrate-only Only run migrations"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  Cortex Database Initialization${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# Function to check if PostgreSQL is ready
check_postgres() {
    if command -v pg_isready &> /dev/null; then
        pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q
    elif command -v psql &> /dev/null; then
        PGPASSWORD="${POSTGRES_PASSWORD:-}" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" &> /dev/null
    else
        # Fallback: try Python
        python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('$POSTGRES_HOST', $POSTGRES_PORT))
    s.close()
    exit(0)
except:
    exit(1)
"
    fi
}

# Wait for PostgreSQL if requested
if [ "$WAIT_FOR_DB" = true ]; then
    echo -e "${BLUE}Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}...${NC}"
    MAX_ATTEMPTS=60
    ATTEMPT=0
    
    while ! check_postgres; do
        ATTEMPT=$((ATTEMPT + 1))
        if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
            echo -e "${RED}✗ PostgreSQL did not become ready after ${MAX_ATTEMPTS} attempts${NC}"
            exit 1
        fi
        echo "  Waiting... ($ATTEMPT/$MAX_ATTEMPTS)"
        sleep 2
    done
    
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
    echo ""
fi

# Change to backend directory
cd "$PROJECT_ROOT/backend"

# Check if we're in a virtual environment or can use poetry
if [ -n "${VIRTUAL_ENV:-}" ]; then
    PYTHON_CMD="python"
    ALEMBIC_CMD="alembic"
elif command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
    PYTHON_CMD="poetry run python"
    ALEMBIC_CMD="poetry run alembic"
else
    PYTHON_CMD="python3"
    ALEMBIC_CMD="python3 -m alembic"
fi

# Verify Alembic is available
if ! $ALEMBIC_CMD --version &> /dev/null 2>&1; then
    echo -e "${RED}✗ Alembic not found. Please install dependencies.${NC}"
    echo "  Run: poetry install"
    exit 1
fi

echo -e "${BLUE}Using Alembic: $($ALEMBIC_CMD --version)${NC}"
echo ""

# Check current migration status
echo -e "${BLUE}Checking current migration status...${NC}"
CURRENT_REV=$($ALEMBIC_CMD current 2>/dev/null || echo "none")
echo "  Current revision: ${CURRENT_REV:-none}"

# Get pending migrations
echo ""
echo -e "${BLUE}Checking for pending migrations...${NC}"
PENDING=$($ALEMBIC_CMD history -r current:head 2>/dev/null | grep -v "^$" | wc -l || echo "0")
if [ "$PENDING" -gt 0 ]; then
    echo -e "${YELLOW}  Found $PENDING pending migration(s)${NC}"
    $ALEMBIC_CMD history -r current:head 2>/dev/null | head -10 || true
else
    echo -e "${GREEN}  No pending migrations${NC}"
fi

# Run migrations
echo ""
echo -e "${BLUE}Running Alembic migrations...${NC}"
if $ALEMBIC_CMD upgrade head; then
    echo -e "${GREEN}✓ Migrations completed successfully${NC}"
else
    echo -e "${RED}✗ Migration failed${NC}"
    exit 1
fi

# Verify final state
echo ""
echo -e "${BLUE}Verifying database state...${NC}"
FINAL_REV=$($ALEMBIC_CMD current 2>/dev/null || echo "unknown")
echo "  Final revision: $FINAL_REV"

# Skip additional initialization if migrate-only
if [ "$MIGRATE_ONLY" = true ]; then
    echo ""
    echo -e "${GREEN}✓ Migration-only mode complete${NC}"
    exit 0
fi

# Run additional initialization via Python
echo ""
echo -e "${BLUE}Running additional database initialization...${NC}"
$PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from app.db import init_db, get_schema_version

# Initialize database (creates any missing tables, records schema version)
init_db()

# Verify schema version
version = get_schema_version()
print(f'  Schema version: {version}')
print('  ✓ Database initialization complete')
"

echo ""
echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}  Database Initialization Complete!${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo "Database: postgresql://${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo ""
echo "Next steps:"
echo "  1. Start the backend: ./start-services.sh"
echo "  2. Or use Docker: docker compose -f ops/docker-compose.prod.yml up"
echo ""
