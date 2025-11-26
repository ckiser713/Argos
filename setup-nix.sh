#!/bin/bash
# Nix Setup Script for Cortex Project
# Run this script to fix Nix permissions and enable flakes

set -e

echo "=== Nix Setup for Cortex Project ==="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please run this script as a regular user, not root"
   exit 1
fi

echo "Step 1: Adding user to nixbld group (requires sudo)..."
sudo usermod -aG nixbld $USER

echo "Step 2: Enabling flakes in Nix configuration..."
mkdir -p ~/.config/nix
if ! grep -q "experimental-features = nix-command flakes" ~/.config/nix/nix.conf 2>/dev/null; then
    echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
    echo "✓ Flakes enabled in ~/.config/nix/nix.conf"
else
    echo "✓ Flakes already enabled"
fi

echo "Step 3: Restarting Nix daemon (requires sudo)..."
sudo systemctl restart nix-daemon || echo "Warning: Could not restart daemon (may not be needed)"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "IMPORTANT: You need to apply the group changes:"
echo "  Option 1: Log out and log back in"
echo "  Option 2: Run: newgrp nixbld"
echo ""
echo "After that, run:"
echo "  cd $(pwd)"
echo "  nix develop"
echo ""






