# Deployment Modes Comparison

This guide helps you choose the best deployment mode for your Argos installation.

## Overview

Argos supports three primary deployment modes:

1. **Docker Compose** - Container-based orchestration
2. **Systemd** - Native Linux service management
3. **Nix** - Reproducible development environment

## Quick Comparison Table

| Feature | Docker Compose | Systemd | Nix |
|---------|---------------|---------|-----|
| **Ease of Setup** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ Moderate | ⭐⭐ Advanced |
| **Portability** | ⭐⭐⭐⭐⭐ High | ⭐⭐ Low | ⭐⭐⭐⭐ High |
| **Resource Overhead** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Minimal | ⭐⭐⭐⭐ Low |
| **Service Dependencies** | ⭐⭐⭐⭐⭐ Automatic | ⭐⭐ Manual | ⭐⭐⭐⭐ Automatic |
| **Production Ready** | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐ Yes | ⭐⭐⭐ Dev/CI |
| **Requires Docker** | Yes | No | Optional |
| **Requires Root** | No* | Yes | No |
| **Health Checks** | Built-in | Manual | Manual |
| **TLS/SSL** | Caddy (auto) | Manual | Manual |
| **Scaling** | Easy | Complex | N/A |

*Requires Docker group membership

## Detailed Breakdown

### Docker Compose

**Best for:**
- Production deployments
- Quick prototyping
- Teams familiar with containers
- Multi-service orchestration
- Automated dependency management

**Pros:**
- One-command deployment
- Built-in health checks and restart policies
- Automatic service discovery
- Easy to replicate across environments
- Caddy handles TLS automatically
- Clear service boundaries

**Cons:**
- Requires Docker installed
- Additional resource overhead (~10-15%)
- Container image management needed
- Docker daemon dependency

**When to use:**
- ✅ First production deployment
- ✅ Development teams
- ✅ Cloud VMs (AWS, GCP, Azure)
- ✅ Need automatic TLS
- ❌ Bare metal with no Docker
- ❌ Extremely resource-constrained

**Quick Start:**
```bash
# Copy environment template
cp ops/.env.example.prod ops/.env
# Edit ops/.env with your secrets

# Start production stack
docker-compose -f ops/docker-compose.prod.yml up -d

# Check status
docker-compose -f ops/docker-compose.prod.yml ps
```

**Files:**
- `ops/docker-compose.yml` - Local development
- `ops/docker-compose.prod.yml` - Production
- `ops/Dockerfile.backend` - Backend image
- `ops/Dockerfile.frontend` - Frontend image
- `ops/Caddyfile` - Reverse proxy config

---

### Systemd

**Best for:**
- Bare metal servers
- No Docker requirement
- Traditional Linux deployments
- Fine-grained resource control
- Integration with existing infrastructure

**Pros:**
- Native Linux integration
- No Docker overhead
- Direct hardware access
- Standard Linux tooling (journalctl, systemctl)
- Low memory footprint

**Cons:**
- Manual dependency management
- No automatic health checks
- Requires root for installation
- More complex setup
- Manual TLS configuration
- Environment-specific tuning needed

**When to use:**
- ✅ Existing Linux infrastructure
- ✅ No Docker available
- ✅ Maximum performance needed
- ✅ Integration with monitoring systems
- ❌ First-time deployment
- ❌ Need quick setup
- ❌ Multi-host deployment

**Quick Start:**
```bash
# Run interactive installer
sudo bash ops/install.sh
# Select option 2 (Systemd)

# Manage services
sudo systemctl status argos-backend
sudo systemctl restart argos-backend
sudo journalctl -u argos-backend -f
```

**Files:**
- `ops/systemd/argos-backend.service.template`
- `ops/systemd/argos-frontend.service.template`
- `ops/systemd/argos-worker.service.template`
- `/etc/argos/argos.env` - Environment configuration

---

### Nix

**Best for:**
- Development environments
- Reproducible builds
- CI/CD pipelines
- Experimentation
- NixOS systems

**Pros:**
- Reproducible across machines
- Isolated dependencies
- No system pollution
- Fast iteration
- Works on any Linux

**Cons:**
- Steep learning curve
- Not ideal for production
- Limited runtime configuration
- Requires Nix installation
- Less common in ops teams

**When to use:**
- ✅ Local development
- ✅ CI/CD builds
- ✅ Reproducible testing
- ✅ NixOS deployments
- ❌ Production (use Compose or Systemd)
- ❌ Team unfamiliar with Nix

**Quick Start:**
```bash
# Enter development shell
nix develop

# Start services
nix run .#backend &
nix run .#frontend &

# Or use helper script
./nix-deploy.sh start
```

**Files:**
- `flake.nix` - Nix configuration
- `nix/vllm.nix` - vLLM module
- `nix/services.nix` - Service definitions

---

## Decision Matrix

### I want to...

**Deploy to production quickly**
→ Use **Docker Compose** with `ops/docker-compose.prod.yml`

**Run on bare metal without Docker**
→ Use **Systemd** with `ops/install.sh`

**Develop locally**
→ Use **Docker Compose** (`ops/docker-compose.yml`) or **Nix** (`nix develop`)

**Integrate with existing systemd services**
→ Use **Systemd** mode

**Ensure reproducible builds**
→ Use **Docker Compose** (images) or **Nix** (derivations)

**Minimize resource usage**
→ Use **Systemd** (no container overhead)

**Get automatic TLS/SSL**
→ Use **Docker Compose** (Caddy handles it)

**Run in Kubernetes**
→ Use Docker images from Compose build, create K8s manifests

---

## Environment Variables

### Common to All Modes

```bash
# Core
ARGOS_ENV=strix|production|local
ARGOS_AUTH_SECRET=<32+ character random string>
ARGOS_DATABASE_URL=postgresql://user:pass@host:5432/db

# Services
ARGOS_QDRANT_URL=http://qdrant:6333
ARGOS_REDIS_URL=redis://redis:6379/0

# Lane URLs
ARGOS_LANE_ORCHESTRATOR_URL=http://inference-vllm:8000/v1
# ... (other lanes)
```

### Compose-Specific

```bash
# Set in compose files or ops/.env
RUNNING_IN_DOCKER=1
ARGOS_DOMAIN=your-domain.com
POSTGRES_PASSWORD=<secret>
MINIO_ROOT_PASSWORD=<secret>
```

### Systemd-Specific

```bash
# Set in /etc/argos/argos.env
CORTEX_ALLOW_NON_NIX=1
POSTGRES_HOST=localhost
# ... (all vars from common)
```

### Nix-Specific

```bash
# Set in shell or nix shell config
IN_NIX_SHELL=1
ARGOS_ENV=local
# ... (local development vars)
```

---

## Runtime Guards

Argos backend includes validation to ensure it runs in appropriate environments:

| Environment | Guard Required | How to Set |
|-------------|----------------|------------|
| local | None | `ARGOS_ENV=local` |
| strix/prod + Docker | `RUNNING_IN_DOCKER=1` | Set in compose or Dockerfile |
| strix/prod + Systemd | `CORTEX_ALLOW_NON_NIX=1` | Set in service file |
| strix/prod + Nix | `IN_NIX_SHELL=1` | Auto-set by `nix develop` |
| strix/prod + PID1 | Auto-detected | Running as init process |

### Bypass Examples

```bash
# Docker Compose (automatic)
environment:
  RUNNING_IN_DOCKER: "1"

# Systemd (in service file)
Environment="CORTEX_ALLOW_NON_NIX=1"

# Manual override (emergency)
ARGOS_ALLOW_NON_NIX=1 poetry run uvicorn app.main:app
```

---

## Migration Between Modes

### Compose → Systemd

1. Export data:
   ```bash
   docker-compose -f ops/docker-compose.prod.yml exec postgres pg_dump -U cortex cortex > backup.sql
   ```

2. Install systemd:
   ```bash
   sudo ops/install.sh  # Select systemd
   ```

3. Restore data:
   ```bash
   psql -U cortex -d cortex < backup.sql
   ```

### Systemd → Compose

1. Backup data:
   ```bash
   sudo -u postgres pg_dump cortex > backup.sql
   ```

2. Stop systemd services:
   ```bash
   sudo systemctl stop argos-{backend,frontend,worker}
   ```

3. Start compose:
   ```bash
   docker-compose -f ops/docker-compose.prod.yml up -d
   docker-compose exec -T postgres psql -U cortex cortex < backup.sql
   ```

---

## Troubleshooting

### "RuntimeError: must run within a Nix shell"

**Cause:** Non-local environment without runtime guard
**Fix:** Set appropriate guard (see Runtime Guards table above)

### "Database connection refused"

**Compose:** Check `docker-compose ps` - wait for postgres healthy
**Systemd:** Check `systemctl status postgresql` and connection string
**Nix:** Ensure Docker services started with `nix run .#docker-up`

### "Lanes unavailable at startup"

**Graceful:** Set `ARGOS_STRICT_LANE_STARTUP=false`
**Timeout:** Increase `ARGOS_LANE_WARMUP_TIMEOUT=60`
**Check services:** Verify vLLM/llama.cpp services are accessible

### Frontend can't reach backend

**Compose:** Check `VITE_CORTEX_API_BASE_URL` build arg
**Systemd:** Ensure backend listening on 0.0.0.0:8000
**Proxy:** Verify Caddy/nginx reverse proxy configuration

---

## Recommended Setups

### Small Deployment (1-10 users)
- **Mode:** Docker Compose
- **Resources:** 2 vCPU, 4GB RAM
- **Storage:** 20GB SSD
- **Stack:** Backend, Frontend, Postgres, Qdrant, Redis, Caddy

### Medium Deployment (10-100 users)
- **Mode:** Docker Compose or Systemd
- **Resources:** 4 vCPU, 8GB RAM, GPU for inference
- **Storage:** 100GB SSD
- **Stack:** + Worker, MinIO, vLLM lanes

### Large Deployment (100+ users)
- **Mode:** Kubernetes (using Compose images)
- **Resources:** Autoscaling, dedicated inference nodes
- **Storage:** Distributed (S3, managed Postgres)
- **Stack:** + Load balancer, monitoring, backups

---

## Next Steps

- Follow [DEPLOY.md](./DEPLOY.md) for step-by-step instructions
- See [E2E_TESTING_SETUP.md](./E2E_TESTING_SETUP.md) for test environment
- Check [backup-restore.md](./backup-restore.md) for data safety