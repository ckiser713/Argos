#!/bin/bash
# Fix Nix daemon socket permissions
# Run this script with sudo: sudo ./fix-nix-socket.sh

set -e

if [ "$EUID" -ne 0 ]; then 
   echo "This script must be run as root (use sudo)"
   exit 1
fi

echo "Fixing Nix daemon socket permissions..."

# Ensure socket directory exists and has correct permissions
mkdir -p /nix/var/nix/daemon-socket
chmod 1777 /nix/var/nix/daemon-socket

# Check if socket exists and fix permissions
if [ -S /nix/var/nix/daemon-socket/socket ]; then
    chmod 666 /nix/var/nix/daemon-socket/socket
    echo "✓ Socket permissions fixed"
else
    echo "Socket doesn't exist yet - it will be created when daemon starts"
fi

# Restart daemon to recreate socket if needed
systemctl restart nix-daemon || service nix-daemon restart || echo "Note: Could not restart daemon"

echo ""
echo "✓ Nix socket permissions fixed!"
echo ""
echo "Now run: newgrp nixbld"
echo "Then: nix develop"





