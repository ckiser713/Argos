#!/bin/bash
# Cortex Deployment Script
# Run this inside nix-shell after fixing the daemon

set -e

echo "=== Cortex Deployment ==="
echo ""

# Check if we're in nix-shell
if ! command -v nix-shell >/dev/null 2>&1 && ! [ -n "$IN_NIX_SHELL" ]; then
    echo "ERROR: This script must be run inside nix-shell"
    echo "Run: nix-shell shell.nix"
    exit 1
fi

echo "1. Installing backend dependencies..."
cd backend
poetry install --no-root
echo "✓ Backend dependencies installed"
echo ""

echo "2. Installing frontend dependencies..."
cd ..
cd frontend
pnpm install
echo "✓ Frontend dependencies installed"
echo ""

echo "3. Installing root dependencies..."
cd ..
pnpm install
echo "✓ Root dependencies installed"
echo ""

echo "4. Starting Docker services..."
docker-compose -f ops/docker-compose.yml up -d
echo "✓ Docker services started"
echo ""

echo "5. Installing Playwright browsers..."
pnpm exec playwright install --with-deps
echo "✓ Playwright browsers installed"
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Services running:"
echo "  - Qdrant: http://localhost:6333"
echo "  - Backend: http://localhost:8000 (start with: cd backend && poetry run uvicorn app.main:app --reload)"
echo "  - Frontend: http://localhost:5173 (start with: cd frontend && pnpm dev)"
echo ""
echo "Run E2E tests: pnpm e2e"
echo ""
echo "Stop services: docker-compose -f ops/docker-compose.yml down"







