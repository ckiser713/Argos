# Fix Nix Daemon - REQUIRED

The Nix daemon connection is failing. You MUST fix this before nix-shell will work.

## Quick Fix Command

Run this command to fix the daemon:

```bash
sudo ./fix-nix-daemon.sh
```

Then start a new shell:

```bash
newgrp nixbld
```

## Manual Fix (if script doesn't work)

```bash
# 1. Stop daemon
sudo systemctl stop nix-daemon

# 2. Remove old socket
sudo rm -f /nix/var/nix/daemon-socket/socket

# 3. Fix directory permissions
sudo chmod 1777 /nix/var/nix/daemon-socket
sudo chown root:nixbld /nix/var/nix/daemon-socket

# 4. Start daemon
sudo systemctl start nix-daemon

# 5. Wait and check socket
sleep 3
ls -la /nix/var/nix/daemon-socket/

# 6. Fix socket permissions if it exists
sudo chmod 666 /nix/var/nix/daemon-socket/socket 2>/dev/null || echo "Socket will be created"

# 7. Start new shell
newgrp nixbld
```

## After Fixing

Once the daemon is fixed, you can use nix-shell:

```bash
cd /home/nexus/Argos_Chatgpt
nix-shell shell.nix
```

This will:
1. Download nixpkgs (first time only, takes a few minutes)
2. Install all dependencies (Python, Node.js, pnpm, Poetry, Playwright, etc.)
3. Provide a complete development environment

## Verify Daemon is Working

```bash
# Check daemon is running
ps aux | grep nix-daemon | grep -v grep

# Check socket exists and is accessible
ls -la /nix/var/nix/daemon-socket/socket

# Test Nix
nix --version
```

If all these work, nix-shell should work!





