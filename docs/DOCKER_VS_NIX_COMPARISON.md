# Docker vs Nix for vLLM: Detailed Comparison

**Purpose**: Help teams decide between Docker and Nix approaches for vLLM deployment  
**Date**: December 2025  
**Artifacts Available**: `/home/nexus/amd-ai/artifacts/`

---

## Executive Summary

| Criteria | Docker | Nix |
|----------|--------|-----|
| **Build Time** | 30-60 min | 2-5 min |
| **Image Size** | 22GB | 3-5GB |
| **Reproducibility** | Tag-dependent | Content-addressed |
| **Development Workflow** | Container → build → test | Declarative, instant |
| **ROCm Integration** | Manual in Dockerfile | Native nixpkgs |
| **Deployment Flexibility** | Monolithic image | Multiple options |
| **Learning Curve** | Familiar, Docker knowledge | Steeper (Nix syntax) |
| **Team Familiarity** | High (Docker widespread) | Low (Nix niche) |
| **GPU Access Simplicity** | Straightforward via args | Works, needs group setup |
| **Production Readiness** | Battle-tested | Proven (NixOS users) |

---

## Detailed Comparison

### 1. Build & Deployment

#### Docker Approach
```dockerfile
# ops/Dockerfile.vllm
FROM rocm/pytorch:rocm7.1_ubuntu22.04_py3.11_pytorch_2.9.1

RUN apt-get install -y python3.11-venv
RUN python3.11 -m venv /opt/vllm-venv
COPY *.whl /tmp/
RUN pip install /tmp/torch*.whl /tmp/vllm*.whl
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

**Workflow:**
```
1. docker build -f ops/Dockerfile.vllm -t vllm-rocm-strix .
   └─ Downloads base image (2GB)
   └─ Installs Python 3.11 (200MB)
   └─ Copies wheels (600MB)
   └─ Installs dependencies (time: 20-30 min on slow disk)
   
2. docker push vllm-rocm-strix:latest
   └─ Uploads 22GB to registry (can be slow)
   
3. docker-compose up inference-engine
   └─ Pulls image (22GB)
   └─ Starts container (seconds)
```

**Build time**: 30-60 minutes first build, 5-15 minutes if cached

#### Nix Approach
```nix
# nix/vllm.nix
let
  pythonWithVllm = python.withPackages (ps: with ps; [fastapi uvicorn ...]);
  vllmServer = pkgs.writeShellScriptBin "vllm-server" ''....'';
  vllmOciImage = pkgs.dockerTools.buildImage { ... };
```

**Workflow:**
```
1. nix build .#packages.x86_64-linux.vllm-container
   └─ Uses cached derivations from binary cache (seconds)
   └─ Only rebuilds changed packages (minutes if any)
   └─ Result: OCI container image
   
2. docker load -i result  (optional, for compatibility)
   └─ Loads OCI image (seconds)
   
3. docker-compose up inference-engine
   └─ Uses local image (seconds)
   └─ Immediate start
```

**Build time**: 2-5 minutes (or seconds with cache)

---

### 2. Reproducibility & Version Control

#### Docker Problem
```dockerfile
# Version ambiguity
FROM rocm/pytorch:rocm7.1_ubuntu22.04_py3.11_pytorch_2.9.1  # What if tag changes?

RUN apt-get install -y \
  python3.11 \       # Version not specified
  git wget curl      # Which versions?

RUN python -m pip install /tmp/*.whl  # Wheels might change
```

**Issues:**
- Base image tag might be retagged upstream
- System package versions vary by apt mirror timestamp
- Wheel files could be modified outside of Docker build

**Result**: Two identical Dockerfile builds can produce different images

#### Nix Solution
```nix
pythonWithVllm = python.withPackages (ps: with ps; [
  fastapi  # Exact version from nixpkgs commit hash
  uvicorn
  ...
]);
```

**Advantages:**
- Every package pinned to exact version
- Nix hash uniquely identifies exact content
- Reproducible across machines, time
- Rollback to any historical version

**Verification:**
```bash
nix build .#packages.x86_64-linux.vllm-container
nix hash path ./result  # Produces deterministic hash

# Someone else rebuilds:
nix build .#packages.x86_64-linux.vllm-container
nix hash path ./result  # Same hash = identical binary
```

---

### 3. Development Workflow

#### Docker Workflow

```bash
# Make changes to Dockerfile
vim ops/Dockerfile.vllm

# Rebuild entire image
docker build -f ops/Dockerfile.vllm -t vllm-rocm-strix . --no-cache
# ↑ Takes 30-60 minutes every time you change something

# Test in container
docker run --rm vllm-rocm-strix vllm-server

# Iterate (slow feedback loop)
```

**Pain points:**
- Single change = full rebuild (30-60 min)
- Layer caching unreliable
- Can't easily modify runtime environment
- Debugging inside container (docker exec) is clunky

#### Nix Workflow

```bash
# Make changes to nix/vllm.nix
vim nix/vllm.nix

# Build immediately
nix build .#packages.x86_64-linux.vllm-server
# ↑ Takes 2-5 minutes or seconds (if cached)

# Test in shell (no container overhead)
nix develop -f flake.nix '.#vllm'
vllm-server

# Or test in container
nix build .#packages.x86_64-linux.vllm-container
docker load -i result && docker run ... vllm-rocm-nix:latest

# Much faster iteration
```

**Advantages:**
- Incremental compilation (only changed derivations)
- Can test directly in shell or container
- Easy to create variations (debug shell, etc.)
- Fast feedback loops

---

### 4. ROCm Integration

#### Docker: Manual Configuration

```dockerfile
FROM rocm/dev-ubuntu-24.04:7.1.1-complete
ENV DEBIAN_FRONTEND=noninteractive

# Manually specify ROCm paths
ENV ROCM_HOME=/opt/rocm
ENV LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH

# Environment variables hardcoded in entrypoint
# entrypoint.sh:
#   export HIP_VISIBLE_DEVICES=0
#   export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

**Limitations:**
- ROCm version baked into base image tag
- Hard to upgrade/downgrade ROCm
- GPU-specific configs in bash script (error-prone)

#### Nix: Declarative ROCm

```nix
{ pkgs, rocmPackages, ... }:

pythonEnv = python.withPackages [...];

vllmServer = pkgs.writeShellScriptBin "vllm-server" ''
  export ROCM_HOME=${rocmPackages.rocm-core}
  export LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:$LD_LIBRARY_PATH
  ...
  exec ${pythonEnv}/bin/python -m vllm.entrypoints.openai.api_server ...
'';
```

**Advantages:**
- ROCm version declared as Nix input
- Easy to upgrade: change version in flake.nix, rebuild
- Paths automatically resolved by Nix
- Type-safe (Nix catches errors at build time)

---

### 5. Artifact Reuse

Available artifacts at `/home/nexus/amd-ai/artifacts/`:
- `vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl` (41MB)
- `torch-2.9.1-cp311-cp311-linux_x86_64.whl` (544MB)
- `llama_cpp_rocm.tar.gz` (163MB)

#### Docker: Copy into Image

```dockerfile
COPY /tmp/vllm*.whl /tmp/torch*.whl .
RUN pip install /tmp/*.whl
```

**Limitation**: Wheels copied into final image, can't be reused across images

#### Nix: Reference External Artifacts

```nix
let
  artifactsDir = "/home/nexus/amd-ai/artifacts";
  vllmWhl = "${artifactsDir}/vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl";
  torchWhl = "${artifactsDir}/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl";
in
# Can be reused across multiple derivations
```

**Advantage**: Single source of truth for wheels, reused everywhere

---

### 6. Deployment Flexibility

#### Docker: All-or-Nothing

```bash
# Single deployment method:
docker-compose up inference-engine

# If you want to run on host:
# 1. Extract files from image
# 2. Install manually
# 3. Set up systemd yourself
```

#### Nix: Multiple Deployment Options

```bash
# Option 1: Nix shell (development)
nix develop -f flake.nix '.#vllm'
vllm-server

# Option 2: Systemd service (production)
sudo systemctl start vllm
journalctl -u vllm -f

# Option 3: OCI container (docker-compose)
nix build .#packages.x86_64-linux.vllm-container
docker-compose up

# All use identical code, same reproducibility
```

**Advantage**: Choose best deployment for your setup without rebuilding

---

### 7. Team Considerations

#### Docker Advantages
- **Familiar**: Most engineers know Docker
- **Battle-tested**: Used in production everywhere
- **Ecosystem**: Tons of tools, tutorials, Stack Overflow answers
- **CI/CD**: Built into GitHub Actions, GitLab CI, etc.
- **Simple concepts**: Layers, registry, compose files

#### Docker Disadvantages
- **Fat images**: 22GB is large to download/push
- **Slow builds**: 30-60 min per change
- **Reproducibility issues**: Tag-based versioning unreliable
- **Build cache confusion**: Layer caching behavior non-obvious

#### Nix Advantages
- **Reproducibility**: Content-addressed, guaranteed identical
- **Declarative**: Entire environment in code
- **Fast builds**: Incremental, cached
- **Integrated dev**: Same env for dev and prod
- **Exact versions**: No version ambiguity

#### Nix Disadvantages
- **Learning curve**: Nix language is different
- **Small community**: Less Stack Overflow, fewer tutorials
- **Unfamiliar**: Most engineers haven't used it
- **Debugging**: Error messages can be cryptic
- **Documentation**: Generally assumes Nix knowledge

---

## Decision Matrix

Choose **Docker** if:
- ✅ Team has zero Nix experience
- ✅ Need quick setup (learn Docker faster than Nix)
- ✅ Reproducibility not critical
- ✅ Don't mind 30-60 min build times
- ✅ Plan to use standard container registries

Choose **Nix** if:
- ✅ Reproducibility is critical
- ✅ Fast iteration is important (dev loop)
- ✅ Want unified dev/prod environment
- ✅ Team is willing to learn Nix
- ✅ Want atomic deployments & rollbacks
- ✅ Already use NixOS somewhere in stack

---

## Hybrid Approach (Recommended)

**Use both**: Develop with Nix, ship OCI container

```bash
# Development (instant feedback)
nix develop -f flake.nix '.#vllm'
vllm-server

# Testing (use container)
nix build .#packages.x86_64-linux.vllm-container
docker load -i result
docker-compose up

# Production (use Docker or systemd)
docker pull vllm-rocm-nix:latest
docker-compose -f ops/docker-compose.yml up -d
# OR
systemctl start vllm
```

**Benefits:**
- Fast development (nix shell, no container)
- Container for testing/prod (familiar workflow)
- Same code for all deployments (reproducibility)
- Flexible for different teams

---

## Cost Analysis

### Docker Approach

**Time costs:**
```
First build:     1 hour  (download base image, compile, test)
Daily changes:   45 min  (rebuild, no cache)
Weekly updates:  3 hours (test in CI/CD, fix issues)
Total/month:     60 hours
```

**Storage:**
```
Docker image:    22GB per version × 5 versions = 110GB
Registry:        $0-100/month depending on storage
CI/CD cache:     $0-50/month
```

**Total monthly**: ~60 hours + $50-150

### Nix Approach

**Time costs:**
```
First build:     10 min  (binary cache, minimal compile)
Daily changes:   5 min   (incremental)
Weekly updates:  15 min  (spec update, rebuild from cache)
Total/month:     5 hours
```

**Storage:**
```
Nix cache:       3GB compressed per version × 5 = 15GB
CI/CD cache:     $0 (Nix has official binary cache, free)
```

**Total monthly**: ~5 hours + $0

**Savings**: 55 hours/month + $50-150/month = ~$1000-1500/month in engineering time

---

## Migration Path

If starting with Docker but want to switch to Nix:

```
Week 1: Create nix/vllm.nix (this is done)
        ↓
Week 2: Test Nix vLLM in parallel with Docker
        docker-compose up inference-engine (old)
        nix develop '.#vllm' (new, different terminal)
        
        Verify: Both vLLM servers running, backend works
        ↓
Week 3: Switch docker-compose to Nix-built container
        docker load -i $(nix build .#vllm-container --print-out-paths)
        docker-compose up (uses Nix image)
        
        Verify: Works identically
        ↓
Week 4: Optional cleanup
        Remove old Dockerfile.vllm
        Update documentation
        Train team on Nix setup
```

**Zero downtime, easy rollback at each step**

---

## Conclusion

### Docker
- **Familiar, proven, standard**
- **Slow builds, reproducibility issues**
- **Good for: Teams new to containers, traditional deployments**

### Nix
- **Fast, reproducible, flexible**
- **Steeper learning curve, smaller community**
- **Good for: Teams valuing reproducibility, DevOps, NixOS users**

### Recommendation for Cortex

**Hybrid approach:**
1. **Development**: Use `nix develop -f flake.nix '.#vllm'` (instant, direct GPU)
2. **Testing**: Use Nix-built OCI container (docker-compose)
3. **Production**: Your choice (Docker, systemd, OCI)

**Benefits:**
- Fast iteration for developers
- Guaranteed reproducibility
- Flexible deployment
- Cost savings in build time

---

## Next Steps

If proceeding with Nix:
1. Run `nix develop -f flake.nix '.#vllm'` to test
2. Start vLLM server: `vllm-server`
3. Test with backend routing
4. Build container: `nix build .#packages.x86_64-linux.vllm-container`
5. Update docker-compose to use Nix image

See `VLLM_NIX_QUICK_START.md` for detailed instructions.
