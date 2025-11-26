#!/usr/bin/env bash
set -euo pipefail

# Script to run all tests inside the Nix dev shell
# Usage: ./run-tests-in-nix.sh
# 
# Prerequisites:
# 1. Fix Nix daemon: sudo ./fix-nix-daemon.sh && newgrp nixbld
# 2. Enter Nix shell: nix develop (or nix-shell for ROCm)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Running Tests in Nix Dev Shell"
echo "=========================================="
echo ""

# Check if we're in Nix shell
if [[ "${IN_NIX_SHELL:-}" != "impure" && "${IN_NIX_SHELL:-}" != "pure" ]]; then
    echo "ERROR: This script must be run inside the Nix dev shell!"
    echo ""
    echo "Please run:"
    echo "  nix develop"
    echo "  # or for ROCm:"
    echo "  nix-shell nix/rocm-shell.nix"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✓ Confirmed: Running inside Nix dev shell"
echo ""

# Backend tests
echo "=========================================="
echo "Running Backend Tests"
echo "=========================================="
cd backend

echo "Installing backend dependencies..."
"$SCRIPT_DIR/tools/require-nix.sh" poetry install

echo ""
echo "Running backend tests..."
"$SCRIPT_DIR/tools/require-nix.sh" poetry run python -m pytest

echo ""
echo "✓ Backend tests completed"
echo ""

# Frontend/E2E tests
echo "=========================================="
echo "Running Frontend/E2E Tests"
echo "=========================================="
cd ../frontend

echo "Installing frontend dependencies..."
"$SCRIPT_DIR/tools/require-nix.sh" pnpm install

echo ""
echo "Installing Playwright browsers..."
"$SCRIPT_DIR/tools/require-nix.sh" pnpm exec playwright install --with-deps

echo ""
echo "Running E2E tests..."
cd ..
"$SCRIPT_DIR/tools/require-nix.sh" pnpm e2e

echo ""
echo "=========================================="
echo "✓ All tests completed successfully!"
echo "=========================================="

