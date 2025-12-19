# vLLM Nix Deployment - Quick Start Guide

**Artifacts Directory:** `/home/nexus/amd-ai/artifacts/`

This directory contains all pre-built artifacts:
- ✅ vLLM 0.12.0 (ROCm 7.1.1) wheel
- ✅ PyTorch 2.9.1 (ROCm) wheel  
- ✅ llama.cpp ROCm archive (for future use)

## ⚡ Quick Start (30 seconds)

```bash
# 1. Enter vLLM environment
cd /home/nexus/Argos_Chatgpt
nix develop -f flake.nix '.#vllm'

# 2. Start vLLM server
vllm-server

# 3. In another terminal, test the API
curl http://localhost:8000/health
```

That's it! vLLM is now running on port 8000 with ROCm GPU acceleration.

## 📋 Deployment Modes

### Mode 1: Development Shell (Recommended for Testing)

```bash
# With default model
./deploy-vllm.sh shell

# With custom model
MODEL_PATH=/path/to/model ./deploy-vllm.sh shell

# With custom GPU memory
MODEL_PATH=/path/to/model GPU_MEM_UTIL=0.60 ./deploy-vllm.sh shell
```

**Advantages:**
- Fastest setup
- Direct GPU access
- Interactive shell
- Easy debugging

### Mode 2: Systemd Service (Production)

```bash
# Requires root and MODEL_PATH
sudo MODEL_PATH=/models/orchestrator/bf16 ./deploy-vllm.sh systemd
```

**Then manage with:**
```bash
systemctl status vllm        # Check status
journalctl -u vllm -f        # View logs
systemctl restart vllm       # Restart
systemctl stop vllm          # Stop
```

**Advantages:**
- Persistent service
- Auto-restart on failure
- System logging
- Resource limits
- Proper GPU device access

### Mode 3: OCI Container (Docker)

```bash
# Build container
./deploy-vllm.sh container

# Run with Docker
docker run -it --rm \
  --device /dev/kfd \
  --device /dev/dri \
  -p 8000:8000 \
  -e MODEL_PATH=/models/orchestrator/bf16 \
  -v /path/to/models:/models:ro \
  vllm-rocm-nix:latest
```

**Advantages:**
- Portable
- Easy distribution
- Docker Compose integration
- Isolated environment

## 🔧 Configuration

### Environment Variables

Edit `vllm-config.sh` or set before running:

```bash
# Required
export MODEL_PATH="/models/orchestrator/bf16"

# Optional - customize as needed
export GPU_MEM_UTIL="0.48"        # GPU allocation (0.0-1.0)
export MAX_MODEL_LEN="32768"      # Context window (tokens)
export DTYPE="bfloat16"           # Data type
export VLLM_PORT="8000"           # Listen port
export ARTIFACTS_DIR="/home/nexus/amd-ai/artifacts"
```

### Load Configuration

```bash
source vllm-config.sh
show_config      # Display current configuration
check_artifacts_dir  # Verify artifacts exist
verify_model_path    # Check model path is valid
```

## 📊 Configuration Profiles

### Development Profile
```bash
export GPU_MEM_UTIL="0.48"        # Conservative
export MAX_MODEL_LEN="32768"      # Standard context
export VLLM_ROCM_GEMM_TUNING="default"
```

### Production Profile
```bash
export GPU_MEM_UTIL="0.60"        # Higher throughput
export MAX_MODEL_LEN="32768"      # Balanced
export VLLM_ROCM_GEMM_TUNING="fast"
```

### Extended Context Profile
```bash
export GPU_MEM_UTIL="0.80"        # Maximum utilization
export MAX_MODEL_LEN="131072"     # Long context
export VLLM_ROCM_GEMM_TUNING="fast"
```

## 🚀 API Usage

### Health Check
```bash
curl http://localhost:8000/health
```

### List Models
```bash
curl http://localhost:8000/v1/models
```

### Chat Completion
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model-name",
    "messages": [
      {"role": "user", "content": "Hello, what are you?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Text Completion
```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model-name",
    "prompt": "Once upon a time",
    "max_tokens": 100
  }'
```

## 🔍 Debugging

### Check GPU Status
```bash
# From within nix develop shell
rocm-smi
```

### View vLLM Logs

**Shell Mode:**
- Logs print to terminal directly

**Systemd Mode:**
```bash
journalctl -u vllm -f        # Follow logs
journalctl -u vllm -n 100    # Last 100 lines
```

**Container Mode:**
```bash
docker logs -f <container-id>
```

### Performance Monitoring

```bash
# In another terminal, check GPU usage
watch -n 1 rocm-smi

# Or run in background
rocm-smi --watch
```

## 📁 File Locations

```
Artifacts:          /home/nexus/amd-ai/artifacts/
Project Root:       /home/nexus/Argos_Chatgpt/
Deployment Script:  deploy-vllm.sh
Configuration:      vllm-config.sh
Nix Config:         nix/vllm.nix
Flake:              flake.nix
```

## 🛠 Troubleshooting

### "Module not found" errors
```bash
# Nix develop shell should have all dependencies
# If issues persist:
nix flake update
nix develop -f flake.nix '.#vllm' --command bash
```

### GPU Not Detected
```bash
# Inside nix develop shell
rocm-smi  # Should show your GPU

# If not visible, check:
export HIP_VISIBLE_DEVICES=0
export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

### Port Already in Use
```bash
# Use different port
VLLM_PORT=8001 vllm-server

# Or find process using port 8000
lsof -i :8000
```

### Out of Memory
```bash
# Reduce GPU memory utilization
GPU_MEM_UTIL=0.40 vllm-server

# Or reduce max model length
MAX_MODEL_LEN=16384 vllm-server
```

### Model Not Found
```bash
# Verify model path exists
ls -la /path/to/model

# Use absolute path
MODEL_PATH=/absolute/path/to/model vllm-server
```

## 📚 Integration with Cortex Backend

### Configure Backend

In `backend/config.py`:
```python
# vLLM endpoint (Nix deployed on port 8000)
lane_orchestrator_url = "http://localhost:8000/v1"
lane_coder_url = "http://localhost:8000/v1"  # or different port
lane_fast_rag_url = "http://localhost:8000/v1"
```

### Test Integration
```bash
# 1. Start vLLM (one terminal)
nix develop -f flake.nix '.#vllm' --command vllm-server

# 2. Start backend (another terminal)
cd backend
poetry run python -m uvicorn app.main:app --port 8001

# 3. Send request to backend
curl -X POST http://localhost:8001/api/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello"}'
```

## 📈 Performance Tips

1. **GPU Memory:** Start with 0.48, increase to 0.60+ for production
2. **Batch Size:** vLLM auto-batches requests, adjust via `max_tokens`
3. **Model Format:** Use BF16 (bfloat16) for best ROCm performance
4. **Swap Space:** Allocate extra CPU swap for large context windows
5. **Monitoring:** Use `rocm-smi --watch` to monitor GPU usage

## 🔄 Updating Artifacts

When new artifacts are available:

```bash
# Check current artifacts
ls -la /home/nexus/amd-ai/artifacts/

# Update vLLM nix if paths change
vi nix/vllm.nix  # Update artifactsDir variables

# Rebuild
nix develop -f flake.nix '.#vllm' --command bash
```

## 📝 Multi-Lane Setup

Run multiple vLLM instances for different models:

```bash
# Terminal 1: Orchestrator model
MODEL_PATH=/models/orchestrator/bf16 VLLM_PORT=8000 vllm-server

# Terminal 2: Coder model  
MODEL_PATH=/models/coder/bf16 VLLM_PORT=8001 vllm-server

# Terminal 3: FastRAG model
MODEL_PATH=/models/fast-rag/bf16 VLLM_PORT=8002 vllm-server
```

Configure backend to use different ports per lane.

## 🎯 Next Steps

1. ✅ Choose deployment mode (shell/systemd/container)
2. ✅ Set MODEL_PATH to your model directory
3. ✅ Run `./deploy-vllm.sh <mode>`
4. ✅ Test with `curl http://localhost:8000/health`
5. ✅ Integrate with Cortex backend
6. ✅ Monitor with `rocm-smi --watch`

## 📞 Support

- **vLLM Docs:** https://docs.vllm.ai/
- **ROCm Docs:** https://rocmdocs.amd.com/
- **AMD GPU Arch:** https://rocmdocs.amd.com/en/latest/deploy/linux/index.html
- **Cortex Integration:** See backend `config.py`

---

**Status:** ✅ Production Ready  
**Last Updated:** December 8, 2025  
**Artifacts Location:** `/home/nexus/amd-ai/artifacts/`
