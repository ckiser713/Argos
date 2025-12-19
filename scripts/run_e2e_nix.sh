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

nix develop --command bash -lc "./tools/run_e2e_local.sh $@" 2>&1 | tee e2e_setup.log
