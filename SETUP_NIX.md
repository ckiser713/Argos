# Nix Setup Commands

Run these commands to fix Nix permissions and enable flakes:

## 1. Add user to nixbld group
```bash
sudo usermod -aG nixbld $USER
```

## 2. Enable flakes in Nix configuration
```bash
# Create config directory if it doesn't exist
mkdir -p ~/.config/nix

# Add experimental features to nix.conf
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

## 3. Restart Nix daemon (if using multi-user install)
```bash
sudo systemctl restart nix-daemon
```

## 4. Log out and log back in (or run: newgrp nixbld)

After completing these steps, the Nix environment will be ready to use.


