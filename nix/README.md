# Nix Environment Setup

This directory contains Nix configuration files for the Cortex project, providing a reproducible development and build environment.

## Files

- `../flake.nix` - Root flake definition with development shell and build outputs
- `../backend/flake.nix` - Backend Python sub-flake using poetry2nix
- `../frontend/flake.nix` - Frontend Node.js sub-flake
- `overlays.nix` - Custom Nix overlays for package overrides
- `docker-services.nix` - Docker services integration (placeholder for NixOS containers)

## Quick Start

### Using Nix Flakes (Recommended)

1. **Enter the development shell:**
   ```bash
   nix develop
   ```

2. **Or use direnv (auto-activates on directory entry):**
   ```bash
   # Install direnv if not already installed
   nix-env -iA nixpkgs.direnv
   
   # Add to your shell config (~/.bashrc, ~/.zshrc, etc.)
   eval "$(direnv hook bash)"  # or zsh/fish
   
   # Allow direnv in the project directory
   direnv allow
   ```

3. **Build packages:**
   ```bash
   # Build backend
   nix build .#backend
   
   # Build frontend
   nix build .#frontend
   
   # Build both
   nix build
   ```

### Using Traditional Nix (shell.nix)

If you don't have flakes enabled:

```bash
nix-shell
```

## What's Included

The development shell provides:

- **Python 3.11** with Poetry
- **Node.js 20** with pnpm
- **Playwright** with browser dependencies
- **Docker** and docker-compose
- **System libraries** for Playwright browsers
- **Development tools** (git, curl, jq, etc.)

## Docker Services

Use the wrapper script to manage Docker services:

```bash
# Start services
cortex-docker up -d

# Stop services
cortex-docker down

# View logs
cortex-docker logs -f
```

Or use docker-compose directly:

```bash
docker-compose -f ops/docker-compose.yml up -d
```

## Environment Variables

The shell automatically sets:

- `CORTEX_ENV=dev`
- `CORTEX_QDRANT_URL=http://localhost:6333`
- `CORTEX_DB_URL=postgresql+psycopg://cortex:cortex@localhost:5432/cortex`
- `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright`

## Playwright Browsers

Playwright browsers are automatically installed to `$HOME/.cache/ms-playwright` on first shell entry. All required system dependencies are included in the Nix environment.

## Troubleshooting

### Flakes not enabled

Enable flakes in your Nix configuration:

```bash
# Add to /etc/nix/nix.conf or ~/.config/nix/nix.conf
experimental-features = nix-command flakes
```

### Frontend build hash error

If you get a hash mismatch error when building the frontend:

1. Build with `--impure` flag to calculate the correct hash:
   ```bash
   nix build .#frontend --impure 2>&1 | grep got:
   ```

2. Update the `npmDepsHash` in `frontend/flake.nix` with the correct hash.

### Poetry dependencies not resolving

If poetry2nix has issues with certain Python packages, add overrides in `backend/flake.nix` or use `nix/overlays.nix`.

### Docker socket permission denied

Ensure your user is in the `docker` group:

```bash
sudo usermod -aG docker $USER
```

Then log out and back in.

## Customization

### Adding Python packages

Edit `backend/pyproject.toml` and run `poetry lock` to update the lock file.

### Adding Node.js packages

Edit `frontend/package.json` and run `pnpm install` to update the lock file.

### ROCm Support (AMD GPU)

Uncomment and configure the ROCm overlay in `nix/overlays.nix` if building on AMD hardware.

## Further Reading

- [Nix Flakes Documentation](https://nixos.wiki/wiki/Flakes)
- [poetry2nix Documentation](https://github.com/nix-community/poetry2nix)
- [direnv Documentation](https://direnv.net/)

