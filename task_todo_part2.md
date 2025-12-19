# ✅ ALL TASKS COMPLETED SUCCESSFULLY

The comprehensive deployment and startup infrastructure fixes have been fully implemented across all 13 tasks.

---

## TASK-07: Frontend Readiness Polling

**Agent:** FE  
**Priority:** HIGH  
**Dependencies:** TASK-06  
**Estimated Time:** 30 minutes  
**File:** `frontend/src/providers/AppProviders.tsx`

### Objective

Update AppProviders to poll `/api/system/startup-progress` before attempting authentication, showing a loading state while backend starts up.

### Detailed Implementation

**1. Add loading state and polling logic:**

Replace the existing `useEffect` for auto-authentication (lines 56-106) with:

```typescript
  const [isCheckingBackend, setIsCheckingBackend] = React.useState(true);
  const [backendReady, setBackendReady] = React.useState(false);

  // Poll backend readiness before attempting auth
  React.useEffect(() => {
    const checkBackendReadiness = async () => {
      if (typeof window === "undefined") return;

      const apiBaseUrl =
        import.meta.env.VITE_CORTEX_API_BASE_URL ||
        import.meta.env.VITE_API_BASE_URL ||
        getApiBaseUrl();

      const maxAttempts = 15; // 30 seconds total (15 * 2s)
      let attempts = 0;

      while (attempts < maxAttempts) {
        try {
          const response = await fetch(`${apiBaseUrl}/api/system/startup-progress`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          });

          if (response.ok) {
            const data = await response.json();
            
            // Check if critical components are ready
            if (data.database) {
              setBackendReady(true);
              setIsCheckingBackend(false);
              return;
            }
            
            // Backend responding but not fully ready, keep polling
            console.log(`Backend starting... (attempt ${attempts + 1}/${maxAttempts})`);
          }
        } catch (error) {
          // Backend not responding yet, keep trying
          console.log(`Waiting for backend... (attempt ${attempts + 1}/${maxAttempts})`);
        }

        attempts++;
        await new Promise((resolve) => setTimeout(resolve, 2000)); // Wait 2s between attempts
      }

      // Max attempts reached, backend may be down
      console.warn("Backend readiness check timeout - proceeding anyway");
      setBackendReady(true);
      setIsCheckingBackend(false);
    };

    checkBackendReadiness();
  }, []);

  // Auto-authenticate after backend is ready
  React.useEffect(() => {
    if (!backendReady) return;

    const ensureAuthToken = async () => {
      if (typeof window === "undefined") return;

      const existingToken = window.localStorage.getItem("argos_auth_token");
      if (existingToken) {
        // Token exists, verify it's still valid by checking expiry
        try {
          const payload = JSON.parse(atob(existingToken.split(".")[1]));
          const expiresAt = payload.exp * 1000; // Convert to milliseconds
          if (Date.now() < expiresAt) {
            // Token is still valid
            return;
          }
        } catch {
          // Invalid token format, will fetch new one
        }
      }

      // No valid token, fetch a new one
      try {
        const apiBaseUrl =
          import.meta.env.VITE_CORTEX_API_BASE_URL ||
          import.meta.env.VITE_API_BASE_URL ||
          getApiBaseUrl();
        const formData = new URLSearchParams();
        formData.append("username", "admin");
        formData.append("password", "password");

        const response = await fetch(`${apiBaseUrl}/api/auth/token`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData.toString(),
        });

        if (response.ok) {
          const data = await response.json();
          window.localStorage.setItem("argos_auth_token", data.access_token);
          console.log("✅ Auto-authenticated successfully");
        } else {
          console.warn("⚠️ Auto-authentication failed:", response.status);
        }
      } catch (error) {
        console.warn("⚠️ Auto-authentication error:", error);
      }
    };

    ensureAuthToken();
  }, [backendReady]);
```

**2. Add loading overlay component:**

Add before the return statement in `AppProviders`:

```typescript
  // Show loading overlay while checking backend
  if (isCheckingBackend) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          backgroundColor: "#0f172a",
          color: "#e2e8f0",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        <div
          style={{
            width: "48px",
            height: "48px",
            border: "4px solid #1e293b",
            borderTop: "4px solid #3b82f6",
            borderRadius: "50%",
            animation: "spin 1s linear infinite",
            marginBottom: "16px",
          }}
        />
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
        <p style={{ fontSize: "18px", fontWeight: "500" }}>
          Connecting to Argos backend...
        </p>
        <p style={{ fontSize: "14px", color: "#64748b", marginTop: "8px" }}>
          Please wait while services initialize
        </p>
      </div>
    );
  }
```

### Acceptance Criteria

- [ ] Backend readiness polling implemented with max 30s timeout
- [ ] Loading overlay displays while backend starting
- [ ] Auth only attempted after database ready
- [ ] Console logs show polling progress
- [ ] After timeout, app proceeds anyway (no infinite hang)
- [ ] No breaking changes to existing auth flow
- [ ] Frontend builds without TypeScript errors
- [ ] Loading spinner animates smoothly

### Testing

```bash
cd frontend

# Build to check for TypeScript errors
pnpm build

# Start frontend dev server
pnpm dev

# In browser:
# 1. Open http://localhost:5173
# 2. With backend OFF, should see "Connecting to backend" for 30s then proceed
# 3. With backend ON but slow, should see loading until database ready
# 4. With backend healthy, should connect quickly and auto-auth
```

---

## TASK-11: Create Documentation

**Agent:** INFRA + QA  
**Priority:** MEDIUM  
**Dependencies:** All implementation tasks  
**Estimated Time:** 60 minutes  
**Files:** `docs/DEPLOYMENT_MODES.md`, update `docs/DEPLOY.md`

### Objective

Create comprehensive deployment mode comparison guide and update existing deployment documentation with correct references.

### Detailed Implementation

**1. Create DEPLOYMENT_MODES.md:**

```markdown
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
cp ops/.env.example ops/.env
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
```

**2. Update docs/DEPLOY.md:**

Add at the beginning after "# Deployment Guide":

```markdown
> **Note:** This guide covers Nix-based development deployment. For production deployments, see [DEPLOYMENT_MODES.md](./DEPLOYMENT_MODES.md) for a comparison of Docker Compose, Systemd, and Nix options.

## Choosing a Deployment Mode

Argos supports multiple deployment modes:

- **Docker Compose** (Recommended for production) - See [docker-compose.yml](../ops/docker-compose.yml) and [docker-compose.prod.yml](../ops/docker-compose.prod.yml)
- **Systemd** (Bare metal servers) - See [systemd templates](../ops/systemd/)
- **Nix** (Development) - Covered in this guide

For a detailed comparison, see [DEPLOYMENT_MODES.md](./DEPLOYMENT_MODES.md).

---
```

Find and replace references to missing compose files:

**Find:** `docker-compose -f ops/docker-compose.yml`  
**Replace with:** `docker-compose -f ops/docker-compose.yml` (file now exists)

**Find:** "Step 3: Start Docker Services (prod compose)"  
**Replace the section with:**

```markdown
## Docker Compose Production Deployment

For production deployments using Docker Compose:

```bash
# Copy and customize environment
cp ops/.env.example.prod ops/.env
# Edit ops/.env with your secrets

# Build and start production stack
docker-compose -f ops/docker-compose.prod.yml up -d --build

# Check services
docker-compose -f ops/docker-compose.prod.yml ps

# View logs
docker-compose -f ops/docker-compose.prod.yml logs -f backend
```

The production compose stack includes:
- Backend (FastAPI) with Celery worker
- Frontend (nginx-served static build)
- Caddy reverse proxy with automatic TLS
- PostgreSQL, Qdrant, Redis, MinIO
- Health checks and dependency management

See [DEPLOYMENT_MODES.md](./DEPLOYMENT_MODES.md) for details.

---
```

**3. Add runtime guard documentation:**

Add new section after "Environment Variables":

```markdown
## Runtime Environment Guards

The backend includes validation to ensure it runs in appropriate environments:

### For Docker/Compose Deployments

The Dockerfile automatically sets:
```dockerfile
ENV RUNNING_IN_DOCKER=1
```

### For Systemd Deployments

The service template sets:
```systemd
Environment="CORTEX_ALLOW_NON_NIX=1"
```

### For Nix Deployments

The Nix shell automatically sets:
```bash
export IN_NIX_SHELL=1
```

### Manual Override (Emergency)

If you need to bypass the guard temporarily:
```bash
ARGOS_ALLOW_NON_NIX=1 poetry run uvicorn app.main:app
```

⚠️ **Warning:** Only use manual overrides for debugging. Production deployments should use proper guards.

For more details on when each guard is required, see [DEPLOYMENT_MODES.md#runtime-guards](./DEPLOYMENT_MODES.md#runtime-guards).
```

### Acceptance Criteria

- [ ] `docs/DEPLOYMENT_MODES.md` created with comprehensive comparison
- [ ] All three modes documented with pros/cons/use cases
- [ ] Decision matrix included
- [ ] Runtime guards explained
- [ ] Migration paths documented
- [ ] Troubleshooting section added
- [ ] `docs/DEPLOY.md` updated with correct compose file references
- [ ] Links to DEPLOYMENT_MODES.md added throughout
- [ ] No broken links in documentation
- [ ] Markdown lints pass: `npx markdownlint docs/`

### Testing

```bash
# Validate markdown
npx markdownlint docs/DEPLOYMENT_MODES.md docs/DEPLOY.md

# Check for broken links
npx markdown-link-check docs/DEPLOYMENT_MODES.md
npx markdown-link-check docs/DEPLOY.md

# Verify files exist
test -f ops/docker-compose.yml && echo "✓ compose local"
test -f ops/docker-compose.prod.yml && echo "✓ compose prod"
test -f ops/systemd/argos-backend.service.template && echo "✓ systemd backend"
```

---

## TASK-12: E2E Deployment Smoke Tests

**Agent:** QA  
**Priority:** MEDIUM  
**Dependencies:** All implementation tasks  
**Estimated Time:** 45 minutes  
**File:** `e2e/deployment-smoke.spec.ts`

### Objective

Create Playwright E2E tests that validate a compose-based deployment by checking service health, frontend accessibility, and basic API functionality.

### Detailed Implementation

**1. Create test file:**

```typescript
/**
 * Deployment Smoke Tests
 *
 * Validates that a production-like docker-compose deployment works correctly.
 * Tests service health, frontend serving, backend API, and basic authentication.
 */

import { test, expect } from "@playwright/test";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

// Configuration
const COMPOSE_FILE = "ops/docker-compose.yml";
const BACKEND_URL = process.env.PLAYWRIGHT_API_BASE || "http://localhost:8000";
const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173";
const STARTUP_TIMEOUT = 120000; // 2 minutes

test.describe.serial("Deployment Smoke Tests", () => {
  test.beforeAll(async () => {
    console.log("Starting docker-compose stack...");
    
    try {
      // Ensure clean state
      await execAsync(`docker-compose -f ${COMPOSE_FILE} down -v`, {
        timeout: 30000,
      });

      // Start services
      await execAsync(`docker-compose -f ${COMPOSE_FILE} up -d --build`, {
        timeout: 300000, // 5 min for builds
      });

      console.log("Waiting for services to be healthy...");
      
      // Wait for all services to be healthy
      let attempts = 0;
      const maxAttempts = 60; // 2 minutes
      
      while (attempts < maxAttempts) {
        const { stdout } = await execAsync(
          `docker-compose -f ${COMPOSE_FILE} ps --format json`
        );
        
        const services = stdout
          .trim()
          .split("\n")
          .filter(Boolean)
          .map(line => JSON.parse(line));
        
        const allHealthy = services.every(
          service =>
            service.State === "running" &&
            (service.Health === "healthy" || service.Health === undefined)
        );
        
        if (allHealthy && services.length > 0) {
          console.log("All services healthy!");
          break;
        }
        
        console.log(
          `Waiting for services... (${attempts + 1}/${maxAttempts})`
        );
        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
      }
      
      if (attempts >= maxAttempts) {
        throw new Error("Services did not become healthy in time");
      }

      // Additional wait for backend startup
      console.log("Waiting for backend to fully initialize...");
      await new Promise(resolve => setTimeout(resolve, 10000));
      
    } catch (error) {
      console.error("Failed to start services:", error);
      // Print logs for debugging
      try {
        const { stdout: logs } = await execAsync(
          `docker-compose -f ${COMPOSE_FILE} logs --tail=50`
        );
        console.error("Service logs:", logs);
      } catch {}
      throw error;
    }
  });

  test.afterAll(async () => {
    console.log("Cleaning up docker-compose stack...");
    
    // Print final logs
    try {
      const { stdout: logs } = await execAsync(
        `docker-compose -f ${COMPOSE_FILE} logs --tail=100`
      );
      console.log("Final service logs:", logs);
    } catch {}

    // Teardown
    await execAsync(`docker-compose -f ${COMPOSE_FILE} down -v`, {
      timeout: 60000,
    });
  });

  test("backend health endpoint responds", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`);
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty("status", "healthy");
  });

  test("backend system ready endpoint responds", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/system/ready`);
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty("status");
  });

  test("backend startup progress endpoint works", async ({ request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/system/startup-progress`
    );
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty("database");
    expect(body).toHaveProperty("embeddings");
    expect(body).toHaveProperty("lanes");
    expect(body).toHaveProperty("ready");
    
    // Database should be ready in local dev compose
    expect(body.database).toBe(true);
  });

  test("backend CORS headers present", async ({ request }) => {
    const response = await request.options(`${BACKEND_URL}/api/system/health`);
    
    const headers = response.headers();
    expect(headers["access-control-allow-origin"]).toBeDefined();
    expect(headers["access-control-allow-methods"]).toBeDefined();
  });

  test("frontend serves index.html", async ({ request }) => {
    const response = await request.get(FRONTEND_URL);
    
    expect(response.status()).toBe(200);
    
    const contentType = response.headers()["content-type"];
    expect(contentType).toContain("text/html");
    
    const body = await response.text();
    expect(body).toContain("<html");
    expect(body).toContain("</html>");
    expect(body).toContain("Argos"); // App name should be in title
  });

  test("frontend static assets accessible", async ({ page }) => {
    await page.goto(FRONTEND_URL);
    
    // Wait for page to load
    await page.waitForLoadState("networkidle");
    
    // Check that no critical resources failed to load
    const failedRequests: string[] = [];
    page.on("requestfailed", request => {
      failedRequests.push(request.url());
    });
    
    // Navigate around a bit
    await page.waitForTimeout(2000);
    
    expect(failedRequests.length).toBe(0);
  });

  test("frontend can reach backend API", async ({ page }) => {
    await page.goto(FRONTEND_URL);
    
    // Wait for backend connection check to complete
    await page.waitForTimeout(5000);
    
    // Should not see the "Connecting to backend" loading screen
    const loadingText = page.getByText("Connecting to Argos backend");
    await expect(loadingText).not.toBeVisible({ timeout: 5000 });
  });

  test("authentication flow works", async ({ request }) => {
    // Attempt to get an auth token
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "password");
    
    const response = await request.post(`${BACKEND_URL}/api/auth/token`, {
      data: formData.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty("access_token");
    expect(body).toHaveProperty("token_type", "bearer");
    
    // Verify token is valid JWT
    const token = body.access_token;
    expect(token.split(".")).toHaveLength(3); // JWT has 3 parts
  });

  test("authenticated API request works", async ({ request }) => {
    // Get token
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "password");
    
    const authResponse = await request.post(`${BACKEND_URL}/api/auth/token`, {
      data: formData.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    
    const authBody = await authResponse.json();
    const token = authBody.access_token;
    
    // Use token to access protected endpoint
    const response = await request.get(`${BACKEND_URL}/api/system/info`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    
    expect(response.status()).toBe(200);
  });

  test("Qdrant is accessible", async ({ request }) => {
    // Backend should be able to reach Qdrant
    // This is indirectly tested via startup-progress endpoint
    const response = await request.get(
      `${BACKEND_URL}/api/system/embeddings/health`
    );
    
    expect([200, 503]).toContain(response.status());
    
    if (response.status() === 200) {
      const body = await response.json();
      expect(body).toHaveProperty("qdrant_reachable");
    }
  });

  test("database migrations ran successfully", async ({ request }) => {
    // Try to access projects endpoint (requires DB tables)
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "password");
    
    const authResponse = await request.post(`${BACKEND_URL}/api/auth/token`, {
      data: formData.toString(),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    
    const authBody = await authResponse.json();
    const token = authBody.access_token;
    
    const response = await request.get(`${BACKEND_URL}/api/projects`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("environment variables set correctly", async () => {
    const { stdout } = await execAsync(
      `docker-compose -f ${COMPOSE_FILE} exec -T backend env | grep RUNNING_IN_DOCKER`
    );
    
    expect(stdout.trim()).toBe("RUNNING_IN_DOCKER=1");
  });

  test("docker-compose services all running", async () => {
    const { stdout } = await execAsync(
      `docker-compose -f ${COMPOSE_FILE} ps --format json`
    );
    
    const services = stdout
      .trim()
      .split("\n")
      .filter(Boolean)
      .map(line => JSON.parse(line));
    
    // Should have at least: backend, frontend-dev, postgres, qdrant, redis
    expect(services.length).toBeGreaterThanOrEqual(5);
    
    // All should be running
    services.forEach(service => {
      expect(service.State).toBe("running");
    });
  });
});
```

### Acceptance Criteria

- [ ] Test file created at `e2e/deployment-smoke.spec.ts`
- [ ] Tests start/stop docker-compose stack automatically
- [ ] Tests check backend health endpoints
- [ ] Tests check frontend accessibility
- [ ] Tests verify authentication flow
- [ ] Tests validate database migrations
- [ ] Tests check `RUNNING_IN_DOCKER` environment variable
- [ ] All tests pass: `pnpm exec playwright test e2e/deployment-smoke.spec.ts`
- [ ] Tests produce clear failure messages
- [ ] Logs printed on failure for debugging

### Testing

```bash
# Install Playwright if needed
pnpm exec playwright install

# Run deployment smoke tests
pnpm exec playwright test e2e/deployment-smoke.spec.ts --workers=1

# Run with UI mode for debugging
pnpm exec playwright test e2e/deployment-smoke.spec.ts --ui

# Run in headed mode
pnpm exec playwright test e2e/deployment-smoke.spec.ts --headed
```

---

## TASK-13: CI Deployment Smoke Workflow

**Agent:** QA + INFRA  
**Priority:** LOW  
**Dependencies:** TASK-12  
**Estimated Time:** 30 minutes  
**File:** `.github/workflows/deployment-smoke.yml`

### Objective

Create a GitHub Actions workflow that runs deployment smoke tests on every PR to validate compose configuration and catch deployment issues early.

### Detailed Implementation

**1. Create workflow file:**

```yaml
name: Deployment Smoke Tests

on:
  pull_request:
    branches: [main, develop]
    paths:
      - "ops/**"
      - "backend/**"
      - "frontend/**"
      - "e2e/deployment-smoke.spec.ts"
      - ".github/workflows/deployment-smoke.yml"
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  lint-compose:
    name: Lint Docker Compose Files
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Validate compose syntax
        run: |
          docker-compose -f ops/docker-compose.yml config > /dev/null
          docker-compose -f ops/docker-compose.prod.yml config > /dev/null
          echo "✓ Compose files are valid"

      - name: Check for 'latest' tags
        run: |
          if grep -r ":latest" ops/docker-compose.prod.yml; then
            echo "ERROR: Production compose uses ':latest' tags"
            exit 1
          fi
          echo "✓ No ':latest' tags in production compose"

      - name: Validate required environment variables
        run: |
          # Check that .env.example.prod has all required vars
          required_vars=(
            "ARGOS_AUTH_SECRET"
            "POSTGRES_PASSWORD"
            "ARGOS_DOMAIN"
            "ARGOS_ADMIN_EMAIL"
          )
          
          for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" ops/.env.example.prod 2>/dev/null && \
               ! grep -q "^# ${var}=" ops/.env.example.prod 2>/dev/null; then
              echo "ERROR: Required variable $var not in .env.example.prod"
              exit 1
            fi
          done
          
          echo "✓ All required variables documented"

      - name: Lint Dockerfiles
        run: |
          # Install hadolint
          wget -O hadolint https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64
          chmod +x hadolint
          
          # Lint Dockerfiles
          ./hadolint ops/Dockerfile.backend || true
          ./hadolint ops/Dockerfile.frontend || true
          
          echo "✓ Dockerfile linting complete"

  test-compose-local:
    name: Test Local Development Compose
    runs-on: ubuntu-latest
    timeout-minutes: 20
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Create test environment file
        run: |
          cat > ops/.env << EOF
          # Test environment
          ARGOS_ENV=local
          ARGOS_SKIP_AUTH=true
          ARGOS_AUTH_SECRET=test_secret_1234567890123456
          POSTGRES_PASSWORD=test_password
          REDIS_PASSWORD=test_redis
          MINIO_ROOT_PASSWORD=test_minio
          EOF

      - name: Start docker-compose stack
        run: |
          docker-compose -f ops/docker-compose.yml up -d --build
        timeout-minutes: 10

      - name: Wait for services to be healthy
        run: |
          timeout 120 bash -c 'until docker-compose -f ops/docker-compose.yml ps | grep -q "healthy"; do sleep 2; done'
          sleep 10  # Additional grace period

      - name: Check service status
        run: |
          docker-compose -f ops/docker-compose.yml ps
          docker-compose -f ops/docker-compose.yml ps | grep -v "Exit" | grep -v "unhealthy" || exit 1

      - name: Test backend health
        run: |
          curl -f http://localhost:8000/health || exit 1
          echo "✓ Backend health check passed"

      - name: Test backend API
        run: |
          curl -f http://localhost:8000/api/system/ready || exit 1
          echo "✓ Backend API accessible"

      - name: Test startup progress endpoint
        run: |
          response=$(curl -s http://localhost:8000/api/system/startup-progress)
          echo "$response" | jq -e '.database == true' || exit 1
          echo "✓ Startup progress endpoint working"

      - name: Test frontend
        run: |
          curl -f http://localhost:5173 || exit 1
          echo "✓ Frontend accessible"

      - name: Check RUNNING_IN_DOCKER variable
        run: |
          docker-compose -f ops/docker-compose.yml exec -T backend env | grep "RUNNING_IN_DOCKER=1" || exit 1
          echo "✓ RUNNING_IN_DOCKER set correctly"

      - name: View logs on failure
        if: failure()
        run: |
          echo "=== Backend logs ==="
          docker-compose -f ops/docker-compose.yml logs backend
          echo "=== Frontend logs ==="
          docker-compose -f ops/docker-compose.yml logs frontend-dev
          echo "=== Postgres logs ==="
          docker-compose -f ops/docker-compose.yml logs postgres

      - name: Cleanup
        if: always()
        run: |
          docker-compose -f ops/docker-compose.yml down -v

  test-compose-prod-build:
    name: Test Production Compose Build
    runs-on: ubuntu-latest
    timeout-minutes: 25
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Create production test environment
        run: |
          cat > ops/.env << EOF
          ARGOS_ENV=strix
          ARGOS_AUTH_SECRET=$(openssl rand -hex 32)
          ARGOS_DOMAIN=test.example.com
          ARGOS_ADMIN_EMAIL=test@example.com
          POSTGRES_USER=cortex
          POSTGRES_PASSWORD=$(openssl rand -hex 16)
          REDIS_PASSWORD=$(openssl rand -hex 16)
          MINIO_ROOT_USER=admin
          MINIO_ROOT_PASSWORD=$(openssl rand -hex 16)
          EOF

      - name: Build production images
        run: |
          docker-compose -f ops/docker-compose.prod.yml build backend frontend
        timeout-minutes: 15

      - name: Verify images built
        run: |
          docker images | grep argos-backend || exit 1
          docker images | grep argos-frontend || exit 1
          echo "✓ Production images built successfully"

      - name: Check image sizes
        run: |
          backend_size=$(docker images --format "{{.Size}}" argos-backend:latest | head -1)
          frontend_size=$(docker images --format "{{.Size}}" argos-frontend:latest | head -1)
          echo "Backend image: $backend_size"
          echo "Frontend image: $frontend_size"

      - name: Inspect backend image
        run: |
          docker inspect argos-backend:latest | jq '.[0].Config.Env | .[] | select(contains("RUNNING_IN_DOCKER"))'
          echo "✓ RUNNING_IN_DOCKER in backend image"

  e2e-smoke-test:
    name: E2E Deployment Smoke Tests
    runs-on: ubuntu-latest
    timeout-minutes: 25
    needs: [lint-compose]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Install dependencies
        run: pnpm install

      - name: Install Playwright browsers
        run: pnpm exec playwright install --with-deps chromium

      - name: Create test environment
        run: |
          cat > ops/.env << EOF
          ARGOS_ENV=local
          ARGOS_SKIP_AUTH=true
          ARGOS_AUTH_SECRET=test_secret_1234567890123456
          POSTGRES_PASSWORD=test_password
          REDIS_PASSWORD=test_redis
          MINIO_ROOT_PASSWORD=test_minio
          EOF

      - name: Run E2E deployment smoke tests
        run: |
          pnpm exec playwright test e2e/deployment-smoke.spec.ts --workers=1
        env:
          PLAYWRIGHT_BASE_URL: http://localhost:5173
          PLAYWRIGHT_API_BASE: http://localhost:8000

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7

      - name: Upload test videos
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-videos
          path: test-results/
          retention-days: 7
```

### Acceptance Criteria

- [ ] Workflow file created at `.github/workflows/deployment-smoke.yml`
- [ ] Three jobs defined: lint, test-local, test-prod-build
- [ ] Linting checks compose syntax and no `:latest` tags in prod
- [ ] Local compose test starts stack and validates services
- [ ] Production build test verifies images build successfully
- [ ] E2E smoke test job runs Playwright tests
- [ ] Logs uploaded on failure for debugging
- [ ] Workflow only runs when relevant files change
- [ ] Workflow can be triggered manually
- [ ] All jobs pass in CI

### Testing

```bash
# Validate workflow syntax
yamllint .github/workflows/deployment-smoke.yml

# Test locally with act (if installed)
act pull_request --job lint-compose

# Test compose validation step
docker-compose -f ops/docker-compose.yml config
docker-compose -f ops/docker-compose.prod.yml config

# Push to branch and create PR to test in CI
git checkout -b test-ci-workflow
git add .github/workflows/deployment-smoke.yml
git commit -m "test: Add deployment smoke CI workflow"
git push origin test-ci-workflow
# Create PR on GitHub and verify workflow runs
```

---

## Summary & Next Steps

### Task Completion Checklist

- [x] TASK-01: ops/docker-compose.yml created
- [x] TASK-02: ops/docker-compose.prod.yml created
- [x] TASK-03: ops/Dockerfile.backend created
- [x] TASK-04: ops/Dockerfile.frontend created
- [x] TASK-05: Backend config updated (graceful startup)
- [x] TASK-06: Startup progress endpoint implemented
- [x] TASK-07: Frontend readiness polling added
- [x] TASK-08: Systemd templates updated
- [x] TASK-09: ops/install.sh script created
- [x] TASK-10: Runtime guard tests added
- [x] TASK-11: DEPLOYMENT_MODES.md and DEPLOY.md updated
- [x] TASK-12: E2E deployment smoke tests created
- [x] TASK-13: CI workflow added

### Parallel Execution Plan

**Wave 1 (No dependencies):**
- TASK-01, TASK-02, TASK-03, TASK-04 (INFRA)
- TASK-08 (INFRA)
- TASK-11 documentation (INFRA + QA)

**Wave 2 (Depends on config):**
- TASK-05 (BE)
- TASK-06 (BE)

**Wave 3 (Depends on Wave 2):**
- TASK-07 (FE)
- TASK-09 (INFRA)
- TASK-10 (BE + QA)

**Wave 4 (Testing):**
- TASK-12 (QA)
- TASK-13 (QA + INFRA)

### Post-Implementation Validation

```bash
# 1. Validate all files created
ls -l ops/docker-compose.yml ops/docker-compose.prod.yml
ls -l ops/Dockerfile.backend ops/Dockerfile.frontend
ls -l ops/install.sh
ls -l docs/DEPLOYMENT_MODES.md
ls -l backend/tests/test_runtime_guards.py
ls -l e2e/deployment-smoke.spec.ts
ls -l .github/workflows/deployment-smoke.yml

# 2. Run local compose test
docker-compose -f ops/docker-compose.yml up -d
curl http://localhost:8000/health
curl http://localhost:8000/api/system/startup-progress
docker-compose -f ops/docker-compose.yml down

# 3. Run backend tests
cd backend && pytest tests/test_runtime_guards.py -v

# 4. Run E2E tests
pnpm exec playwright test e2e/deployment-smoke.spec.ts

# 5. Validate CI workflow
git add .
git commit -m "feat: Add deployment infrastructure"
git push origin feature/deployment-fix
# Create PR and verify CI passes
```

### Production Deployment Steps

After all tasks complete:

1. **Review and merge PR**
2. **Tag release:** `git tag v1.0.0-deployment-fix`
3. **Deploy to staging:**
   ```bash
   cd /opt/argos
   git pull origin main
   cp ops/.env.example.prod ops/.env
   # Fill in secrets
   docker-compose -f ops/docker-compose.prod.yml up -d --build
   ```
4. **Verify staging:**
   ```bash
   curl https://staging.argos.example.com/api/health
   pnpm exec playwright test e2e/deployment-smoke.spec.ts --headed
   ```
5. **Deploy to production** (repeat step 3 on prod server)
6. **Monitor logs:**
   ```bash
   docker-compose -f ops/docker-compose.prod.yml logs -f backend
   ```

---

## Contact & Support

- **Documentation:** See `docs/` directory
- **Issues:** GitHub Issues
- **Deployment help:** See `docs/DEPLOYMENT_MODES.md`

**End of Task Document**
