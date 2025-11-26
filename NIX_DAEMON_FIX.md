# Fix Nix Daemon Connection Issues

The error "Connection reset by peer" indicates the Nix daemon is having connection issues.

## Quick Fix

Run this command:

```bash
sudo ./fix-nix-daemon.sh
```

Then start a new shell:

```bash
newgrp nixbld
```

## Manual Fix Steps

If the script doesn't work, try these steps manually:

```bash
# 1. Stop the daemon
sudo systemctl stop nix-daemon

# 2. Remove old socket
sudo rm -f /nix/var/nix/daemon-socket/socket

# 3. Fix permissions
sudo chmod 1777 /nix/var/nix/daemon-socket
sudo chown root:nixbld /nix/var/nix/daemon-socket

# 4. Start the daemon
sudo systemctl start nix-daemon

# 5. Wait a moment, then fix socket permissions
sleep 2
sudo chmod 666 /nix/var/nix/daemon-socket/socket 2>/dev/null || echo "Socket will be created on next daemon start"

# 6. Start new shell with nixbld group
newgrp nixbld
```

## Alternative: Use Traditional Nix Shell (No Daemon Required)

If the daemon continues to have issues, you can use the traditional approach which may work better:

```bash
# This uses nix-shell which might work even with daemon issues
cd /home/nexus/Argos_Chatgpt
nix-shell shell.nix
```

This provides the same development environment without requiring flakes.

## Verify Daemon is Running

```bash
ps aux | grep nix-daemon | grep -v grep
systemctl status nix-daemon
```

## Check Socket

```bash
ls -la /nix/var/nix/daemon-socket/
```

The socket should exist and be readable by your user.





