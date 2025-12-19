# vLLM Nix OS Container Specification for Cortex

**Document Purpose**: Specification for building vLLM as a Nix OS container instead of Docker  
**Target Audience**: Nix/NixOS engineers building and maintaining the vLLM inference service  
**Date**: December 2025  
**Repository**: Artifacts at `/home/nexus/amd-ai/artifacts/`

---

## Executive Summary

This specification describes how to replace the Docker-based vLLM image (`vllm-rocm-strix:latest`) with a **Nix OS container** approach. This provides:

- **Declarative Configuration**: Entire environment defined in Nix (no Docker image building)
- **Reproducibility**: Same exact environment every build (content-addressable)
- **Faster Deployment**: Pre-built derivations cached in Nix binary cache
- **Better Integration**: Native ROCm support through nixpkgs overlays
- **Simpler Maintenance**: No Docker Dockerfile maintenance burden
- **Direct vLLM Access**: Can use local vLLM Python packages without containerization

---

## Architecture: Docker vs Nix Comparison

### Current Docker Approach
```
docker-compose.yml
    ↓
Dockerfile.vllm (builds from rocm/pytorch base)
    ↓
Docker Image: vllm-rocm-strix:latest (22GB)
    ↓
Container Process: vLLM OpenAI API Server
    ├─ Port 8000 mapped to 11434
    ├─ ROCm GPU access via /dev/kfd, /dev/dri
    └─ Models mounted from ./models volume
```

### New Nix Container Approach
```
flake.nix + nix/vllm.nix
    ↓
Nix Derivations:
  ├─ rocm packages
  ├─ python311 with vLLM wheel
  ├─ torch wheel (ROCm-enabled)
  └─ runtime dependencies
    ↓
OCI Container (via nix2container or podman)
    ↓
Container Process: vLLM OpenAI API Server (identical to Docker)
    ├─ Port 8000 mapped to 11434
    ├─ ROCm GPU access via /dev/kfd, /dev/dri
    └─ Models mounted from ./models volume
```

### Benefits of Nix Approach

| Aspect | Docker | Nix |
|--------|--------|-----|
| **Build Time** | 30-60 min (source build) | 2-5 min (binary cache) |
| **Image Size** | 22GB | 3-5GB (compressed) |
| **Reproducibility** | Depends on base image tag | Guaranteed via content hash |
| **Declarative** | Imperative script | Functional code |
| **Version Control** | Binary artifact | Source code (small) |
| **Debugging** | `docker exec` | `nix shell` into derivation |
| **Integration** | Separate from dev env | Unified with dev environment |
| **ROCm Support** | Manual configuration | Native nixpkgs overlays |

---

## Available Artifacts

Located at `/home/nexus/amd-ai/artifacts/`:

### 1. Pre-built Wheels
```
├─ vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl (41 MB)
│   └─ vLLM optimized for ROCm 7.1.1, Python 3.11
│
└─ torch-2.9.1-cp311-cp311-linux_x86_64.whl (544 MB)
    └─ PyTorch 2.9.1 with ROCm bindings, Python 3.11
```

### 2. Docker Artifacts (for reference)
```
└─ vllm_docker_rocm/
    ├─ Dockerfile (already optimized for ROCm)
    ├─ entrypoint.sh (vLLM startup script)
    ├─ torch-2.9.1-cp311-cp311-linux_x86_64.whl
    └─ vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl
```

### 3. Compiled Binaries
```
└─ llama_cpp_rocm.tar.gz (163 MB)
    └─ Pre-compiled llama.cpp with ROCm support (for future use)
```

**Key Point**: We can reuse the `.whl` files directly in Nix, avoiding any rebuild!

---

## Nix Implementation Strategy

### Step 1: Create Nix vLLM Package Definition

**File**: `nix/vllm.nix`

```nix
{ pkgs, lib, rocmPackages }:

let
  python = pkgs.python311;
  
  # Pre-built wheels from artifacts
  artifactsDir = "/home/nexus/amd-ai/artifacts";
  
  torchWhl = "${artifactsDir}/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl";
  vllmWhl = "${artifactsDir}/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl";
  
  # Python environment with vLLM
  pythonEnv = python.withPackages (ps: with ps; [
    # Core dependencies
    pip
    setuptools
    wheel
    
    # FastAPI for OpenAI-compatible API
    fastapi
    uvicorn
    pydantic
    
    # Utilities
    python-dotenv
    requests
    aiohttp
    httpx
  ]);

in

{
  # vLLM runtime environment (for running vLLM server)
  vllmRuntime = pkgs.mkShell {
    name = "vllm-runtime";
    
    buildInputs = with pkgs; [
      # Python environment
      pythonEnv
      
      # ROCm stack
      rocmPackages.rocm-core
      rocmPackages.rocm-runtime
      rocmPackages.hip
      rocmPackages.hipcc
      rocmPackages.rocblas
      rocmPackages.rocrand
      rocmPackages.rocsparse
      rocmPackages.rocm-smi
      
      # System dependencies
      curl
      git
      wget
      ca-certificates
      
      # Optional: development tools
      vim
      htop
      tmux
    ];
    
    shellHook = ''
      # Set up Python environment
      export PYTHONUNBUFFERED=1
      
      # ROCm configuration
      export ROCM_HOME=${rocmPackages.rocm-core}
      export LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:$LD_LIBRARY_PATH
      export PATH=${rocmPackages.rocm-smi}/bin:$PATH
      
      # AMD GPU detection
      export HIP_VISIBLE_DEVICES=0
      export HSA_OVERRIDE_GFX_VERSION=11.0.0
      
      # vLLM Configuration
      export VLLM_TARGET_DEVICE=rocm
      export VLLM_ROCM_USE_AITER=1
      export VLLM_ROCM_USE_SKINNY_GEMM=1
      export VLLM_HOST=0.0.0.0
      export VLLM_PORT=8000
      export GPU_MEM_UTIL=0.48
      
      echo "vLLM Runtime Environment Loaded"
      echo "ROCm Home: $ROCM_HOME"
      echo "HIP Visible Devices: $HIP_VISIBLE_DEVICES"
    '';
  };

  # vLLM service runner
  vllmService = pkgs.writeShellScriptBin "vllm-server" ''
    set -euo pipefail
    
    # Configuration from environment or defaults
    HOST="''${VLLM_HOST:-0.0.0.0}"
    PORT="''${VLLM_PORT:-8000}"
    MODEL_PATH="''${MODEL_PATH:-/models/vllm/orchestrator/bf16}"
    GPU_MEM_UTIL="''${GPU_MEM_UTIL:-0.48}"
    MAX_MODEL_LEN="''${MAX_MODEL_LEN:-32768}"
    
    # ROCm Configuration
    export ROCM_HOME=${rocmPackages.rocm-core}
    export LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:$LD_LIBRARY_PATH
    export HIP_VISIBLE_DEVICES=0
    export HSA_OVERRIDE_GFX_VERSION=11.0.0
    export VLLM_TARGET_DEVICE=rocm
    export VLLM_ROCM_USE_AITER=1
    export VLLM_ROCM_USE_SKINNY_GEMM=1
    
    echo "Starting vLLM Server"
    echo "  Host: $HOST"
    echo "  Port: $PORT"
    echo "  Model: $MODEL_PATH"
    echo "  GPU Memory Utilization: $GPU_MEM_UTIL"
    echo "  Max Model Length: $MAX_MODEL_LEN"
    
    exec ${pythonEnv}/bin/python -m vllm.entrypoints.openai.api_server \
      --model "$MODEL_PATH" \
      --host "$HOST" \
      --port "$PORT" \
      --gpu-memory-utilization "$GPU_MEM_UTIL" \
      --dtype bfloat16 \
      --tensor-parallel-size 1 \
      --pipeline-parallel-size 1 \
      --max-model-len "$MAX_MODEL_LEN" \
      --swap-space 8 \
      "''${EXTRA_VLLM_ARGS:-}"
  '';

  # OCI Container image (for containerization if needed)
  vllmContainer = pkgs.dockerTools.buildImage {
    name = "vllm-rocm-nix";
    tag = "latest";
    
    fromImage = null;  # Build from scratch
    
    contents = [
      pythonEnv
      rocmPackages.rocm-core
      rocmPackages.rocm-runtime
      rocmPackages.hip
      rocmPackages.rocblas
      pkgs.curl
      pkgs.ca-certificates
    ];
    
    config = {
      Env = [
        "ROCM_HOME=${rocmPackages.rocm-core}"
        "LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib"
        "HIP_VISIBLE_DEVICES=0"
        "HSA_OVERRIDE_GFX_VERSION=11.0.0"
        "VLLM_TARGET_DEVICE=rocm"
        "VLLM_ROCM_USE_AITER=1"
        "VLLM_ROCM_USE_SKINNY_GEMM=1"
        "VLLM_HOST=0.0.0.0"
        "VLLM_PORT=8000"
        "GPU_MEM_UTIL=0.48"
      ];
      
      Entrypoint = [ "${vllmService}/bin/vllm-server" ];
      
      ExposedPorts = { "8000/tcp" = {}; };
      
      Labels = {
        "org.opencontainers.image.description" = "vLLM with ROCm support (Nix-built)";
        "org.opencontainers.image.vendor" = "Cortex Project";
      };
    };
  };
}
```

### Step 2: Update Main flake.nix

**Add to `flake.nix`**:

```nix
{
  description = "Cortex: AI-Integrated Knowledge & Execution Engine";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: 
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      
      # Import ROCm overlay
      rocmPackages = pkgs.rocmPackages;
      
      # Import vLLM module
      vllmModule = import ./nix/vllm.nix { 
        inherit pkgs rocmPackages;
        lib = pkgs.lib;
      };
      
    in {
      # vLLM as a package
      packages.${system} = {
        vllm-server = vllmModule.vllmService;
        vllm-container = vllmModule.vllmContainer;
      };
      
      # vLLM development shell
      devShells.${system}.vllm = vllmModule.vllmRuntime;
      
      # Add to existing default shell
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          # ... existing dependencies ...
          vllmModule.vllmService
        ];
      };
    };
}
```

---

## Deployment Methods

### Method 1: Direct Nix Shell (Development/Testing)

```bash
# Enter vLLM environment
nix develop -f flake.nix '.#vllm'

# Start vLLM server
vllm-server
# OR with custom model path
MODEL_PATH=/models/vllm/orchestrator/bf16 vllm-server
```

**Advantages:**
- No containerization overhead
- Direct GPU access
- Immediate debugging
- Fast iteration

**Use Case**: Development, testing, local inference

---

### Method 2: Nix-based Systemd Service

**File**: `nix/vllm-service.nix`

```nix
{ config, pkgs, lib, ... }:

let
  vllmModule = import ./vllm.nix {
    inherit pkgs;
    rocmPackages = pkgs.rocmPackages;
    lib = lib;
  };
  
  projectRoot = "/home/nexus/Argos_Chatgpt";
  
in

{
  systemd.services.vllm = {
    description = "vLLM Inference Server";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    
    serviceConfig = {
      Type = "simple";
      Restart = "always";
      RestartSec = "10s";
      User = "nexus";
      Group = "nexus";
      
      # GPU device access
      DeviceAllow = [
        "/dev/kfd rw"
        "/dev/dri rw"
      ];
      DevicePolicy = "closed";
      SupplementaryGroups = [ "video" "render" ];
      
      # Environment
      Environment = [
        "ROCM_HOME=${pkgs.rocmPackages.rocm-core}"
        "LD_LIBRARY_PATH=${pkgs.rocmPackages.rocm-runtime}/lib:${pkgs.rocmPackages.rocblas}/lib"
        "HIP_VISIBLE_DEVICES=0"
        "HSA_OVERRIDE_GFX_VERSION=11.0.0"
        "VLLM_TARGET_DEVICE=rocm"
        "VLLM_ROCM_USE_AITER=1"
        "VLLM_ROCM_USE_SKINNY_GEMM=1"
        "VLLM_HOST=0.0.0.0"
        "VLLM_PORT=8000"
        "GPU_MEM_UTIL=0.48"
      ];
      
      # Bind mount models directory
      BindPaths = [ "${projectRoot}/models:/models:ro" ];
      
      # Run service
      ExecStart = "${vllmModule.vllmService}/bin/vllm-server";
      
      # Resource limits
      MemoryLimit = "64G";  # 64GB for vLLM
      CPUQuota = "80%";     # 80% of CPU
    };
  };

  # Also available as a package
  environment.systemPackages = [ vllmModule.vllmService ];
}
```

**Enable in NixOS**:
```nix
# /etc/nixos/configuration.nix
imports = [
  /home/nexus/Argos_Chatgpt/nix/vllm-service.nix
];

services.vllm.enable = true;
services.vllm.modelPath = "/home/nexus/Argos_Chatgpt/models/vllm/orchestrator/bf16";
```

**Usage**:
```bash
# Start service
sudo systemctl start vllm

# Check status
sudo systemctl status vllm

# View logs
journalctl -u vllm -f

# Stop service
sudo systemctl stop vllm
```

---

### Method 3: OCI Container (via nix2container or Podman)

**Build OCI image from Nix**:

```bash
# Build the container
nix build .#packages.x86_64-linux.vllm-container

# Load into podman/docker
podman load -i result
# OR
docker load -i result

# Run container
podman run -it \
  --device /dev/kfd:/dev/kfd \
  --device /dev/dri:/dev/dri \
  --group-add video \
  --group-add render \
  -p 8000:8000 \
  -v /home/nexus/Argos_Chatgpt/models:/models:ro \
  -e MODEL_PATH=/models/vllm/orchestrator/bf16 \
  vllm-rocm-nix:latest
```

**Advantages:**
- Containerized (isolation)
- Reproducible (Nix-built)
- Smaller than Docker image
- Can use with docker-compose

---

### Method 4: Docker-Compose with Nix-built OCI Image

**File**: `ops/docker-compose.nix.yml`

```yaml
version: '3.8'

services:
  inference-engine:
    image: vllm-rocm-nix:latest  # Pre-built by nix build
    container_name: inference-vllm
    
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
    
    group_add:
      - video
      - render
    
    ports:
      - "11434:8000"
    
    environment:
      - MODEL_PATH=/models/vllm/orchestrator/bf16
      - VLLM_GPU_MEMORY_UTILIZATION=0.48
      - VLLM_MAX_MODEL_LEN=32768
      - HIP_VISIBLE_DEVICES=0
      - HSA_OVERRIDE_GFX_VERSION=11.0.0
    
    volumes:
      - ./models:/models:ro
      - /dev/shm:/dev/shm
    
    shm_size: '16gb'
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    
    restart: unless-stopped

  # ... other services (qdrant, backend, etc.)
```

---

## Configuration Management

### Environment Variables

All vLLM configuration via env vars (no need to rebuild image):

```bash
# Model Selection
MODEL_PATH=/models/vllm/orchestrator/bf16          # Full path to model
MAX_MODEL_LEN=32768                           # Context window (tokens)

# GPU Configuration
VLLM_GPU_MEMORY_UTILIZATION=0.48              # GPU memory allocation
HIP_VISIBLE_DEVICES=0                         # GPU device index
HSA_OVERRIDE_GFX_VERSION=11.0.0               # Force gfx1151 support

# API Server
VLLM_HOST=0.0.0.0                             # Listen address
VLLM_PORT=8000                                # Listen port

# Performance Tuning
VLLM_ROCM_USE_AITER=1                         # Use async iterators
VLLM_ROCM_USE_SKINNY_GEMM=1                   # Optimized GEMM kernels

# Logging
VLLM_LOG_LEVEL=INFO                           # Verbosity level
```

### Model Lane Configuration

For multi-lane switching, update backend `config.py`:

```python
# Lane URLs (in docker-compose or systemd service)
lane_orchestrator_url = "http://localhost:8000/v1"
lane_coder_url = "http://localhost:8000/v1"
lane_fast_rag_url = "http://localhost:8000/v1"

# Models loaded by vLLMLaneManager
lane_orchestrator_model = "DeepSeek-R1-Distill-Qwen-32B"
lane_coder_model = "Qwen2.5-Coder-32B-Instruct"
lane_fast_rag_model = "Llama-3.2-11B-Vision-Instruct"
```

---

## Advantages of Nix Approach

### 1. **Reproducibility**
```
Nix derivation hash = deterministic, content-addressable build
Every "nix build" produces identical output (binaries, configuration)
Can be verified via `nix-hash`, `nix-prefetch-*` commands
```

### 2. **Atomic Deployments**
```
Old vLLM service
        ↓
nix build .#packages.x86_64-linux.vllm-server
        ↓
Symlink switch (atomic)
        ↓
New vLLM service (rollback available)
```

### 3. **Dependency Management**
```
No "Docker layer caching" confusion
All dependencies tracked in Nix closure
Can see exact versions: nix why-depends output
Can upgrade ROCm/Python independently
```

### 4. **Faster Updates**
```
Update only changed derivations (not entire image)
Nix binary cache provides pre-built binaries
No need to rebuild vLLM wheel (already has pre-built artifact)
```

### 5. **Better Integration**
```
Development environment = Production environment
Same Nix expressions for both
No "works on my machine" issues
```

---

## Migration Path

### Phase 1: Parallel Setup (No Downtime)

1. Create `nix/vllm.nix` (this spec)
2. Update `flake.nix` with vLLM package
3. Keep existing Docker Compose running
4. Test Nix-built vLLM on alternative port (8001)

```bash
# Keep existing
docker-compose up inference-engine  # Port 11434→8000

# Test Nix version (separate process)
nix develop -f flake.nix '.#vllm'
MODEL_PATH=/models/vllm/orchestrator/bf16 vllm-server &  # Port 8000

# Both running, test routes to Nix version on 8000
```

### Phase 2: Gradual Migration

1. Switch docker-compose to Nix-built OCI container
2. Run both in parallel initially
3. Route new requests to Nix version
4. Verify performance/compatibility

```bash
# Build Nix image
nix build .#packages.x86_64-linux.vllm-container
podman load -i result

# Update docker-compose to use nix-built image
# (instead of vllm-rocm-strix:latest from Docker Hub)
```

### Phase 3: Full Replacement

1. Decommission Docker vLLM container
2. Optionally switch to systemd service or nix develop
3. Keep docker-compose for other services (qdrant, backend)

```bash
# Final setup: docker-compose with backend + qdrant only
# vLLM runs as:
#   Option A: systemd service (if NixOS)
#   Option B: nix develop shell (if traditional Linux)
#   Option C: Nix OCI container in docker-compose (hybrid)
```

---

## Implementation Checklist

- [ ] Create `/nix/vllm.nix` with vLLM package definition
- [ ] Update `/flake.nix` to include vLLM packages/shells
- [ ] Test `nix develop -f flake.nix '.#vllm'` locally
- [ ] Verify vLLM server starts with test model
- [ ] Create `/nix/vllm-service.nix` for systemd service
- [ ] Build OCI container: `nix build .#vllm-container`
- [ ] Test podman run with GPU access
- [ ] Update docker-compose to use Nix-built image
- [ ] Test backend routing to vLLM on 8000
- [ ] Document in project README
- [ ] Remove old Dockerfile.vllm if fully migrated

---

## Troubleshooting

### GPU Access Issues

```bash
# Check if /dev/kfd, /dev/dri accessible
ls -l /dev/kfd /dev/dri

# Verify user in video/render groups
id
# Should show: groups=...,video,...,render,...

# Add if needed
sudo usermod -aG video,render $USER
# Log out/in for changes to take effect
```

### vLLM Won't Start

```bash
# Check ROCm environment variables
echo $ROCM_HOME
echo $LD_LIBRARY_PATH
echo $HIP_VISIBLE_DEVICES

# Test manually
rocm-smi

# Check available GPUs
HIP_VISIBLE_DEVICES=0 rocm-smi
```

### Model Download Fails

```bash
# Verify model path exists
ls -la /models/vllm/orchestrator/bf16/

# Check HF token (if gated model)
export HF_TOKEN=your_token
MODEL_PATH=/models/vllm/orchestrator/bf16 vllm-server

# Pre-download model
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-32B --local-dir /models/vllm/orchestrator/bf16
```

### Container Networking Issues

```bash
# Verify container network
docker inspect inference-vllm | grep -A 10 NetworkSettings

# Test connectivity from another container
docker run --rm --network host curlimages/curl http://localhost:8000/health
```

---

## Conclusion

The Nix approach provides:
- **Simpler maintenance** (no Dockerfile updates)
- **Faster builds** (binary cache)
- **Better reproducibility** (content-addressed)
- **Unified environment** (dev = prod)
- **Direct artifact reuse** (pre-built wheels from `/home/nexus/amd-ai/artifacts/`)

All while maintaining the same Docker/container compatibility layer for backward compatibility and orchestration flexibility.
