#!/bin/bash
# Comprehensive Nix daemon fix script
# Run with: sudo ./fix-nix-daemon.sh

set -e

if [ "$EUID" -ne 0 ]; then 
   echo "This script must be run as root (use sudo)"
   exit 1
fi

echo "=== Fixing Nix Daemon ==="
echo ""

# 1. Fix socket directory permissions
echo "1. Fixing socket directory permissions..."
mkdir -p /nix/var/nix/daemon-socket
chmod 1777 /nix/var/nix/daemon-socket
chown root:nixbld /nix/var/nix/daemon-socket

# 2. Stop daemon
echo "2. Stopping Nix daemon..."
systemctl stop nix-daemon 2>/dev/null || pkill -9 nix-daemon 2>/dev/null || echo "Daemon not running"

# 3. Remove old socket
echo "3. Removing old socket..."
rm -f /nix/var/nix/daemon-socket/socket

# 4. Fix store permissions
echo "4. Fixing store permissions..."
chmod 1775 /nix/store 2>/dev/null || true
chown root:nixbld /nix/store 2>/dev/null || true

# 5. Start daemon
echo "5. Starting Nix daemon..."
systemctl start nix-daemon || service nix-daemon start || echo "Warning: Could not start daemon service"

# Wait a moment for socket to be created
sleep 2

# 6. Fix socket permissions
if [ -S /nix/var/nix/daemon-socket/socket ]; then
    echo "6. Fixing socket permissions..."
    chmod 666 /nix/var/nix/daemon-socket/socket
    chown root:root /nix/var/nix/daemon-socket/socket
    echo "✓ Socket created and permissions fixed"
else
    echo "⚠ Socket not created yet - daemon may need manual start"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Now run: newgrp nixbld"
echo "Then test: nix --version"





