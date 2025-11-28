# Nix Deployment Guide

This guide explains how to deploy Cortex services using Nix.

## Quick Start

### 1. Deploy Services

```bash
# Start all services
./nix-deploy.sh start

# Check status
./nix-deploy.sh status

# View logs
./nix-deploy.sh logs

# Stop services
./nix-deploy.sh stop
```

### 2. Run Services Manually (Alternative)

#### Start Docker Services (Qdrant)
```bash
nix run .#docker-up
# Or manually:
docker-compose -f ops/docker-compose.yml up -d
```

#### Start Backend
```bash
nix run .#backend
# Or manually:
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Start Frontend
```bash
nix run .#frontend
# Or manually:
cd frontend
pnpm preview --host 0.0.0.0 --port 5173
```

## NixOS Systemd Deployment

For production deployments on NixOS systems, you can use systemd services.

### Option 1: Add to NixOS Configuration

Add to your `/etc/nixos/configuration.nix`:

```nix
{
  imports = [
    /home/nexus/Argos_Chatgpt/nix/services.nix
  ];
}
```

Then rebuild:
```bash
sudo nixos-rebuild switch
```

### Option 2: Use Flake Module

If using flakes, add to your system flake:

```nix
{
  inputs.cortex.url = "/home/nexus/Argos_Chatgpt";
  
  outputs = { self, nixpkgs, cortex }: {
    nixosConfigurations.your-hostname = nixpkgs.lib.nixosSystem {
      modules = [
        cortex.nixosModules.default
        # ... your other modules
      ];
    };
  };
}
```

### Managing Systemd Services

```bash
# Start services
sudo systemctl start cortex-backend
sudo systemctl start cortex-frontend
sudo systemctl start cortex-docker

# Enable auto-start on boot
sudo systemctl enable cortex-backend
sudo systemctl enable cortex-frontend
sudo systemctl enable cortex-docker

# Check status
sudo systemctl status cortex-backend
sudo systemctl status cortex-frontend
sudo systemctl status cortex-docker

# View logs
sudo journalctl -u cortex-backend -f
sudo journalctl -u cortex-frontend -f
sudo journalctl -u cortex-docker -f
```

## Available Nix Commands

### Build Packages
```bash
# Build backend package
nix build .#backend

# Build frontend package
nix build .#frontend

# Build all packages
nix build
```

### Run Apps
```bash
# Run backend
nix run .#backend

# Run frontend
nix run .#frontend

# Start Docker services
nix run .#docker-up

# Stop Docker services
nix run .#docker-down
```

### Development Shell
```bash
# Enter development shell
nix develop

# This provides:
# - Python 3.11 with Poetry
# - Node.js 20 with pnpm
# - Docker and docker-compose
# - All required system libraries
```

## Service URLs

Once deployed, services are available at:

- **Qdrant**: http://localhost:6333
- **Backend API**: http://localhost:8000
- **Backend Docs**: http://localhost:8000/api/docs
- **Frontend**: http://localhost:5173

## Environment Variables

The services use the following environment variables (set automatically in systemd services):

- `CORTEX_ENV=production`
- `CORTEX_QDRANT_URL=http://localhost:6333`
- `CORTEX_ATLAS_DB_PATH=/home/nexus/Argos_Chatgpt/backend/atlas.db`
- `NODE_ENV=production`

## Troubleshooting

### Flakes Not Enabled
```bash
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### Docker Permission Issues
```bash
sudo usermod -aG docker $USER
# Then log out and log back in
```

### Services Not Starting
1. Check if dependencies are installed:
   ```bash
   cd backend && poetry install
   cd ../frontend && pnpm install
   ```

2. Check Docker services:
   ```bash
   docker-compose -f ops/docker-compose.yml ps
   ```

3. Check service logs:
   ```bash
   ./nix-deploy.sh logs
   # Or for systemd:
   sudo journalctl -u cortex-backend -f
   ```

### Port Already in Use
If ports 8000 or 5173 are already in use:
- Stop existing services on those ports
- Or modify the port in the service configuration

## Architecture

The deployment consists of:

1. **Docker Services** (via docker-compose):
   - Qdrant vector database (ports 6333, 6334)
   - Optional: vLLM inference engine (port 11434)

2. **Backend Service**:
   - FastAPI application
   - Runs on port 8000
   - Uses Poetry for dependency management

3. **Frontend Service**:
   - React/Vite application
   - Runs on port 5173
   - Uses pnpm for dependency management

## Production Considerations

For production deployments:

1. **Use a reverse proxy** (nginx, Caddy, etc.) in front of services
2. **Set up SSL/TLS** certificates
3. **Configure firewall** rules
4. **Set up log rotation** for systemd services
5. **Configure resource limits** in systemd service files
6. **Use a process manager** like systemd or supervisor
7. **Set up monitoring** and alerting
8. **Backup the database** regularly (`atlas.db`)

## Files

- `flake.nix` - Main Nix flake configuration
- `nix/services.nix` - Systemd service definitions
- `nix-deploy.sh` - Deployment script
- `ops/docker-compose.yml` - Docker services configuration





