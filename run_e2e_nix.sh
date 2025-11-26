#!/bin/bash
# E2E Testing Script for Nix Environment
set -e

echo "=========================================="
echo "Cortex E2E Testing Setup"
echo "=========================================="
echo ""

# Source Nix profile
if [ -f ~/.nix-profile/etc/profile.d/nix.sh ]; then
    source ~/.nix-profile/etc/profile.d/nix.sh
    echo "✓ Nix profile sourced"
else
    echo "⚠ Warning: Nix profile not found, trying to continue..."
fi

# Enter Nix shell and run setup
echo ""
echo "Entering Nix development shell..."
echo "This may take a while on first run as Nix builds packages..."
echo ""

nix develop --command bash << 'E2E_SETUP' 2>&1 | tee e2e_setup.log
set -e

echo "=========================================="
echo "Step 1: Installing Backend Dependencies"
echo "=========================================="
cd backend
if [ ! -d ".venv" ] || [ ! -f "poetry.lock" ]; then
    echo "Installing backend dependencies with Poetry..."
    # Regenerate lockfile to fix ABI compatibility issues with Nix Python environment
    echo "Regenerating Poetry lockfile for Nix Python environment..."
    poetry lock --no-cache --regenerate 2>&1 | tail -5 || poetry lock 2>&1 | tail -5 || true
    echo "Installing dependencies..."
    # Try to install, and if tree-sitter-languages fails, install it separately from source
    poetry install --no-root || {
        echo "⚠ Some packages failed, trying to install tree-sitter-languages from source..."
        pip install --no-build-isolation tree-sitter-languages || echo "⚠ tree-sitter-languages installation skipped (optional dependency)"
        poetry install --no-root --no-interaction || echo "⚠ Poetry install completed with warnings"
    }
else
    echo "Backend dependencies appear to be installed, skipping..."
fi
cd ..

echo ""
echo "=========================================="
echo "Step 2: Installing Frontend Dependencies"
echo "=========================================="
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies with pnpm..."
    pnpm install
else
    echo "Frontend dependencies appear to be installed, skipping..."
fi

echo ""
echo "=========================================="
echo "Step 3: Installing Playwright Browsers"
echo "=========================================="
echo "Installing Playwright browsers..."
if ! pnpm exec playwright install; then
    echo "⚠ Playwright browser installation had issues, continuing..."
fi

echo ""
echo "=========================================="
echo "Step 4: Starting Qdrant Service"
echo "=========================================="
cd ops
if docker-compose ps qdrant | grep -q "Up"; then
    echo "✓ Qdrant is already running"
else
    echo "Starting Qdrant..."
    docker-compose up -d qdrant
    echo "Waiting for Qdrant to be ready..."
    sleep 5
fi
cd ..

echo ""
echo "=========================================="
echo "Step 5: Running E2E Tests"
echo "=========================================="
echo "Starting e2e tests..."
echo ""

# Run e2e tests
pnpm e2e

echo ""
echo "=========================================="
echo "E2E Testing Complete!"
echo "=========================================="
E2E_SETUP
