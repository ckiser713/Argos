# Nix Environment Setup - Quick Reference

This project now has a complete Nix environment setup for reproducible development and builds.

## Files Created

- `flake.nix` - Root flake with development shell and build outputs
- `backend/flake.nix` - Backend Python sub-flake (poetry2nix)
- `frontend/flake.nix` - Frontend Node.js sub-flake
- `shell.nix` - Traditional Nix shell (for non-flake users)
- `.envrc` - direnv configuration for auto-activation
- `nix/overlays.nix` - Custom package overlays
- `nix/docker-services.nix` - Docker services integration
- `nix/README.md` - Detailed documentation

## Quick Start

```bash
# Enter development shell
nix develop

# Or with direnv (auto-activates)
direnv allow

# Build packages
nix build .#backend
nix build .#frontend
nix build  # Builds both

# Start Docker services
cortex-docker up -d
```

## What's Included

- Python 3.11 with Poetry
- Node.js 20 with pnpm
- Playwright with all browser dependencies
- Docker and docker-compose
- All system libraries for Playwright browsers
- Development tools (git, curl, jq, etc.)

## Next Steps

1. **Enable flakes** (if not already enabled):
   ```bash
   # Add to /etc/nix/nix.conf or ~/.config/nix/nix.conf
   experimental-features = nix-command flakes
   ```

2. **Enter the shell**:
   ```bash
   nix develop
   ```

3. **Install dependencies**:
   ```bash
   # Backend
   cd backend && poetry install
   
   # Frontend
   cd frontend && pnpm install
   ```

4. **Start services**:
   ```bash
   cortex-docker up -d
   ```

5. **Run the application**:
   ```bash
   # Backend (in one terminal)
   cd backend && poetry run uvicorn app.main:app --reload
   
   # Frontend (in another terminal)
   cd frontend && pnpm dev
   ```

## Notes

- Playwright browsers are automatically installed to `$HOME/.cache/ms-playwright`
- Environment variables are automatically set in the shell
- The `cortex-docker` wrapper script finds the project root automatically
- See `nix/README.md` for detailed documentation and troubleshooting

