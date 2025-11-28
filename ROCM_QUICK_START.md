# ROCm Integration Quick Start Guide

This guide provides quick steps to integrate ROCm artifacts into Cortex.

## Prerequisites

- ROCm artifacts installed at `~/rocm/py311-tor290/`
- Docker installed (for vLLM)
- Python 3.11+ (for backend)

## Quick Setup

### 1. Load vLLM Docker Image (Recommended)

```bash
# Load pre-built ROCm vLLM image
./ops/load_rocm_image.sh

# Verify image loaded
docker images | grep vllm-rocm-strix
```

### 2. Update Docker Compose

Edit `ops/docker-compose.yml`:

```yaml
inference-engine:
  # Use pre-built image instead of building
  image: vllm-rocm-strix:latest
  # Comment out or remove 'build:' section
```

### 3. Start Services

```bash
# Start inference engine
docker-compose -f ops/docker-compose.yml up -d inference-engine

# Check logs
docker-compose -f ops/docker-compose.yml logs -f inference-engine
```

### 4. Verify Inference Engine

```bash
# Test API endpoint
curl http://localhost:11434/v1/models

# Or check backend config
# CORTEX_LLM_BASE_URL=http://localhost:11434/v1
```

## Alternative: Use llama.cpp (Local Binary)

If you prefer local inference without Docker:

```bash
# Set environment variables
export CORTEX_LLM_BACKEND=llama_cpp
export CORTEX_LLAMA_CPP_BINARY=~/rocm/py311-tor290/bin/llama-cpp
export CORTEX_LLAMA_CPP_MODEL_PATH=/path/to/model.gguf

# Run backend
cd backend
uvicorn app.main:app --reload
```

**Note**: You need GGUF model files. Download from HuggingFace or convert your own.

## Optional: Install PyTorch Wheels

Only needed if building custom PyTorch tools:

```bash
# Install ROCm PyTorch wheels
./backend/scripts/install_rocm_wheels.sh

# Verify
python3.11 -c "import torch; print(torch.version.hip)"
```

## Troubleshooting

### Docker Image Not Found

```bash
# Check if image exists
docker images | grep vllm

# Reload if needed
./ops/load_rocm_image.sh
```

### llama.cpp Binary Not Found

```bash
# Check binary exists
ls -lh ~/rocm/py311-tor290/bin/llama-cpp

# Make executable if needed
chmod +x ~/rocm/py311-tor290/bin/llama-cpp*
```

### ROCm Device Access Issues

```bash
# Check device permissions
ls -l /dev/kfd /dev/dri

# Add user to render group (if needed)
sudo usermod -a -G render,video $USER
# Log out and back in for changes to take effect
```

## Configuration Reference

### Environment Variables

```bash
# LLM Backend Selection
CORTEX_LLM_BACKEND=openai          # Use OpenAI API (vLLM/Ollama)
CORTEX_LLM_BACKEND=llama_cpp       # Use local llama.cpp binary

# OpenAI API Settings (when backend=openai)
CORTEX_LLM_BASE_URL=http://localhost:11434/v1
CORTEX_LLM_API_KEY=ollama
CORTEX_LLM_MODEL=llama3

# llama.cpp Settings (when backend=llama_cpp)
CORTEX_LLAMA_CPP_BINARY=~/rocm/py311-tor290/bin/llama-cpp
CORTEX_LLAMA_CPP_MODEL_PATH=/path/to/model.gguf
CORTEX_LLAMA_CPP_N_CTX=4096        # Context window size
CORTEX_LLAMA_CPP_N_THREADS=4       # CPU threads
```

## Next Steps

- See `ROCM_INTEGRATION_MAP.md` for detailed file mappings
- See `backend/README-backend.md` for backend setup
- See `ops/docker-compose.yml` for service configuration


