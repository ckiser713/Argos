#!/bin/bash
# This script attempts to fix common Nix permission issues.
# Run with: sudo ./fix-nix-permissions.sh

set -e

if [ "$EUID" -ne 0 ]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

echo "=== Fixing Nix Permissions ==="

# 1. Run the existing daemon fix script
echo "1. Running fix-nix-daemon.sh..."
./fix-nix-daemon.sh

# 2. Reset /nix/var/nix/profiles/per-user and /nix/var/nix/gcroots/per-user to standard multi-user Nix permissions
echo "2. Resetting /nix/var/nix/profiles/per-user and /nix/var/nix/gcroots/per-user permissions..."
chown root:root /nix/var/nix/profiles/per-user
chmod 1777 /nix/var/nix/profiles/per-user

chown root:root /nix/var/nix/gcroots/per-user
chmod 1777 /nix/var/nix/gcroots/per-user

# 3. Ensure /nix/var/nix and its contents (excluding the per-user profiles/gcroots) are owned by root:nixbld and are group-writable
echo "3. Fixing /nix/var/nix directory tree ownership and permissions..."

# Temporarily exclude per-user directories from recursive changes
# This is a bit tricky with chown -R and chmod -R, so we'll do it explicitly
chown root:nixbld /nix/var/nix
chmod g+w /nix/var/nix

# Fix other subdirectories that should be group-writable for nixbld
# Find all directories under /nix/var/nix (excluding per-user ones) and apply changes
find /nix/var/nix -mindepth 1 -maxdepth 1 -type d \
  ! -name "profiles" \
  ! -name "gcroots" \
  -exec chown -R root:nixbld {} + \
  -exec chmod -R g+w {} +

# Specifically target /nix/var/nix/db
chown root:nixbld /nix/var/nix/db
chmod g+w /nix/var/nix/db

echo "=== Done ==="
echo ""
echo "Please run 'newgrp nixbld' and then retry your Nix command."
