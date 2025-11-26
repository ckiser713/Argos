# Fix Nix Daemon Socket Permissions

The Nix daemon socket has restrictive permissions. Run this command to fix it:

```bash
sudo ./fix-nix-socket.sh
```

Or manually:

```bash
sudo chmod 1777 /nix/var/nix/daemon-socket
sudo chmod 666 /nix/var/nix/daemon-socket/socket
sudo systemctl restart nix-daemon
```

Then start a new shell session with the nixbld group:

```bash
newgrp nixbld
```

Now you should be able to run:

```bash
cd /home/nexus/Argos_Chatgpt
nix develop
```

## Alternative: Use nix-shell (traditional, no flakes)

If flakes continue to have issues, you can use the traditional shell.nix:

```bash
nix-shell shell.nix
```

This doesn't require flakes and should work immediately.





