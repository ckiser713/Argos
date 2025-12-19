# vLLM Nix Setup: Quick Start Guide

**Last Updated**: December 8, 2025  
**Status**: Ready for Testing  
**Artifacts Location**: `/home/nexus/amd-ai/artifacts/`

---

## What Changed

Instead of using Docker for vLLM, we now have a **Nix-based setup** that:

1. Uses pre-built ROCm-optimized wheels from artifacts
2. Defines vLLM as a Nix package (reproducible, declarative)
3. Supports multiple deployment methods (shell, systemd, container)
4. No need to rebuild the Docker image (saves 30-60 minutes)

---

## Quick Start (3 Options)

### Option 1: Run vLLM in Nix Shell (Simplest)

```bash
# Enter vLLM environment
nix develop -f flake.nix '.#vllm'

# You're now in the vLLM shell with all dependencies
# Start the server:
vllm-server

# Output should show:
# ╔════════════════════════════════════════════════════════════╗
# ║         vLLM Runtime Environment (ROCm 7.1.1)              ║
# ║ Starting vLLM OpenAI API Server                            ║
# ...

# Test in another terminal:
curl http://localhost:8000/health
```

**Advantages:**
- No containerization overhead
- Direct GPU access
- Fast to start
- Perfect for development

**Configuration:**
```bash
# Use different model
MODEL_PATH=/models/vllm/orchestrator/bf16 vllm-server

# Adjust GPU memory
GPU_MEM_UTIL=0.45 vllm-server

# Custom context window
MAX_MODEL_LEN=64000 vllm-server

# All custom args
MODEL_PATH=/models/vllm/coder/bf16 \
  VLLM_GPU_MEMORY_UTILIZATION=0.50 \
  MAX_MODEL_LEN=32768 \
  vllm-server
```

---

### Option 2: Run as Systemd Service (Production)

**Prerequisites:**
- Running NixOS (or Linux with systemd)
- ROCm-capable GPU
- `/home/nexus/Argos_Chatgpt/models/` directory with models

**Setup:**

1. Update NixOS configuration:

```bash
sudo nano /etc/nixos/configuration.nix
```

2. Add vLLM service:

```nix
{
  imports = [ /home/nexus/Argos_Chatgpt/nix/services.nix ];
  
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
      
      DeviceAllow = [ "/dev/kfd rw" "/dev/dri rw" ];
      SupplementaryGroups = [ "video" "render" ];
      
      Environment = [
        "ROCM_HOME=${pkgs.rocmPackages.rocm-core}"
        "LD_LIBRARY_PATH=${pkgs.rocmPackages.rocm-runtime}/lib:${pkgs.rocmPackages.rocblas}/lib"
        "HIP_VISIBLE_DEVICES=0"
        "HSA_OVERRIDE_GFX_VERSION=11.0.0"
        "VLLM_TARGET_DEVICE=rocm"
        "GPU_MEM_UTIL=0.48"
        "MODEL_PATH=/home/nexus/Argos_Chatgpt/models/vllm/orchestrator/bf16"
      ];
      
      ExecStart = "${pkgs.vllm-server}/bin/vllm-server";
      
      MemoryLimit = "64G";
      CPUQuota = "80%";
    };
  };
}
```

3. Apply changes:

```bash
sudo nixos-rebuild switch
```

4. Manage service:

```bash
# Start service
sudo systemctl start vllm

# Check status
sudo systemctl status vllm

# View logs
journalctl -u vllm -f

# Stop service
sudo systemctl stop vllm

# Enable on boot
sudo systemctl enable vllm
```

**Advantages:**
- Automatic restart on failure
- Integrated with system logging
- Resource limits enforced
- Background operation

---

### Option 3: Run as OCI Container (Docker-Compose Compatible)

**Build container:**

```bash
# Build OCI image from Nix
nix build .#packages.x86_64-linux.vllm-container

# This creates a `result` symlink with the image tarball
```

**Option 3A: With Podman**

```bash
# Load into podman
podman load -i result

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

# Test
curl http://localhost:8000/health
```

**Option 3B: With Docker**

```bash
# Load into docker
docker load -i result

# Run container
docker run -it \
  --device /dev/kfd:/dev/kfd \
  --device /dev/dri:/dev/dri \
  --group-add video \
  --group-add render \
  -p 11434:8000 \
  -v /home/nexus/Argos_Chatgpt/models:/models:ro \
  -e MODEL_PATH=/models/vllm/orchestrator/bf16 \
  vllm-rocm-nix:latest

# Test on external port 11434
curl http://localhost:11434/health
```

**Option 3C: With docker-compose**

Create `ops/docker-compose.vllm.yml`:

```yaml
version: '3.8'

services:
  inference-engine:
    # Use Nix-built image
    image: vllm-rocm-nix:latest
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
      - GPU_MEM_UTIL=0.48
      - HIP_VISIBLE_DEVICES=0
      - HSA_OVERRIDE_GFX_VERSION=11.0.0
    
    volumes:
      - ./models:/models:ro
      - /dev/shm:/dev/shm:rw
    
    shm_size: '16gb'
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    
    restart: unless-stopped
```

Run with:

```bash
# Build Nix image first
nix build .#packages.x86_64-linux.vllm-container
docker load -i result

# Start compose
docker-compose -f ops/docker-compose.vllm.yml up -d

# Check logs
docker logs -f inference-vllm

# Stop
docker-compose -f ops/docker-compose.vllm.yml down
```

---

## Configuration Reference

### All Supported Environment Variables

```bash
# Model Selection (REQUIRED)
MODEL_PATH=/path/to/model                    # Path to model weights

# GPU Configuration
HIP_VISIBLE_DEVICES=0                        # GPU device (0-indexed)
HSA_OVERRIDE_GFX_VERSION=11.0.0             # Force gfx1151 (AMD GPU)
VLLM_GPU_MEMORY_UTILIZATION=0.48            # GPU memory allocation (0.45-0.95)

# API Server
VLLM_HOST=0.0.0.0                           # Listen address
VLLM_PORT=8000                              # Listen port

# Model Parameters
MAX_MODEL_LEN=32768                         # Context window (tokens)
DTYPE=bfloat16                              # Precision (bfloat16, float16, float32)

# Parallelization (usually 1 for single GPU)
TENSOR_PARALLEL_SIZE=1                      # Tensor parallelism
PIPELINE_PARALLEL_SIZE=1                    # Pipeline parallelism

# Memory Management
SWAP_SPACE=8                                # CPU swap for context overflow (GB)

# Advanced ROCm Options
VLLM_ROCM_USE_AITER=1                       # Use async iterators
VLLM_ROCM_USE_SKINNY_GEMM=1                 # Optimized GEMM kernels
VLLM_ROCM_GEMM_TUNING=fast                  # Tune for speed vs precision
```

### Example Configurations

**Fast RAG Lane (Small Model)**
```bash
MODEL_PATH=/models/vllm/fast_rag/bf16 \
  MAX_MODEL_LEN=131072 \
  GPU_MEM_UTIL=0.30 \
  vllm-server
```

**Orchestrator Lane (Large Model)**
```bash
MODEL_PATH=/models/vllm/orchestrator/bf16 \
  MAX_MODEL_LEN=32768 \
  GPU_MEM_UTIL=0.50 \
  vllm-server
```

**Testing with Small Model**
```bash
MODEL_PATH=TinyLlama/TinyLlama-1.1B \
  MAX_MODEL_LEN=2048 \
  GPU_MEM_UTIL=0.10 \
  vllm-server
```

---

## Testing & Verification

### Health Check

```bash
# Check vLLM is running
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### List Available Models

```bash
curl http://localhost:8000/v1/models
# Shows currently loaded model
```

### Simple Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
  }'
```

### Streaming Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "messages": [{"role": "user", "content": "Count from 1 to 5"}],
    "stream": true
  }'
```

---

## Troubleshooting

### GPU Not Found

```bash
# Check if GPUs visible
rocm-smi

# Verify /dev/kfd exists
ls -l /dev/kfd /dev/dri

# Check user groups
id
# Should include: video, render

# Add to groups if needed
sudo usermod -aG video,render $USER
# Log out/in for changes
```

### vLLM Won't Start

```bash
# Check ROCm environment
nix develop -f flake.nix '.#vllm'
echo $ROCM_HOME
rocm-smi

# Test model path exists
ls -la /models/vllm/orchestrator/bf16/

# Run with verbose output
PYTHONVERBOSE=1 vllm-server
```

### Out of Memory

```bash
# Reduce GPU memory usage
GPU_MEM_UTIL=0.40 vllm-server

# Reduce context window
MAX_MODEL_LEN=16384 vllm-server

# Or use smaller model
MODEL_PATH=/models/vllm/fast_rag/bf16 vllm-server
```

### Container Port Conflicts

```bash
# Check if port in use
lsof -i :8000
# or
netstat -tulpn | grep 8000

# Kill existing process
pkill -f vllm

# Use alternative port
VLLM_PORT=8001 vllm-server
```

---

## Integration with Cortex Backend

### Configure Backend to Use Nix vLLM

Update `backend/app/config.py`:

```python
# vLLM (Nix-based)
lane_orchestrator_url = "http://localhost:8000/v1"
lane_orchestrator_model = "DeepSeek-R1-Distill-Qwen-32B"
lane_orchestrator_backend = "vllm"

lane_coder_url = "http://localhost:8000/v1"
lane_coder_model = "Qwen2.5-Coder-32B-Instruct"
lane_coder_backend = "vllm"

lane_fast_rag_url = "http://localhost:8000/v1"
lane_fast_rag_model = "Llama-3.2-11B-Vision-Instruct"
lane_fast_rag_backend = "vllm"
```

### Start Full Stack

```bash
# Terminal 1: vLLM
nix develop -f flake.nix '.#vllm'
vllm-server

# Terminal 2: Backend
cd backend && poetry run uvicorn app.main:app --reload

# Terminal 3: Frontend
cd frontend && pnpm dev

# Terminal 4 (optional): Docker services (Qdrant, n8n)
docker-compose -f ops/docker-compose.yml up -d
```

---

## Next Steps

1. **Test vLLM in nix shell**: `nix develop -f flake.nix '.#vllm'` then `vllm-server`
2. **Verify with backend**: Route requests from FastAPI to vLLM on port 8000
3. **Build OCI image**: `nix build .#packages.x86_64-linux.vllm-container`
4. **Deploy to docker-compose**: Update `ops/docker-compose.yml` to use Nix image
5. **Optional systemd**: Set up as systemd service for production

---

## Advantages Summary

| Aspect | Docker | Nix (Now) |
|--------|--------|----------|
| Build Time | 30-60 min | 2-5 min (cached) |
| Image Size | 22GB | 3-5GB (compressed) |
| Reproducibility | Tag-based | Content-addressed hash |
| Update Speed | Full rebuild | Only changed derivations |
| Integration | Separate | Unified with dev env |
| ROCm Support | Manual config | Native nixpkgs |

---

## Files Changed

- `nix/vllm.nix` - NEW: Complete vLLM package definition
- `flake.nix` - UPDATED: Added vLLM packages and shells
- `VLLM_NIX_CONTAINER_SPECIFICATION.md` - NEW: Full specification
- `VLLM_DOCKER_IMAGE_SPECIFICATION.md` - EXISTING: Docker reference (kept for comparison)

---

## Questions?

See:
- `VLLM_NIX_CONTAINER_SPECIFICATION.md` for detailed spec
- `nix/vllm.nix` for implementation details
- Check `flake.nix` for integration points
