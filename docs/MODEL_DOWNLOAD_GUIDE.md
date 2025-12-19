# Model Download Guide

This guide explains how to download all models required for Cortex Model Lanes **outside of containers** for persistent storage and reuse.

## Overview

Models are stored in a shared directory structure that can be mounted into containers. This approach:
- ✅ Prevents re-downloading models on container restart
- ✅ Allows sharing models between containers
- ✅ Enables model management outside Docker
- ✅ Reduces container image size

## Quick Start

### Option 1: Using the Shell Script (Recommended)

```bash
# Download all models
cd /path/to/Argos_Chatgpt
./ops/download_all_models.sh

# Or specify custom models directory
./ops/download_all_models.sh --models-dir /data/cortex-models
```

**Production note:** set `MODELS_PATH` in `.env` (for example, `/data/cortex-models`) so Docker Compose mounts the correct host directory and the preflight check can validate model files before inference containers start.

### Option 2: Using Python Script

```bash
# Set models directory
export ARGOS_MODELS_DIR=/data/cortex-models
export MODELS_PATH=/data/cortex-models  # Used by docker-compose.prod model volume

# Download specific models
export ARGOS_DOWNLOAD_SUPER_READER=true
export ARGOS_DOWNLOAD_GOVERNANCE=true
export ARGOS_DOWNLOAD_VLLM=true

# Run download script
python3 backend/scripts/download_models.py
```

## Model Directory Structure

After downloading, models are organized as follows:

```
models/
├── vllm/                    # vLLM-compatible models
│   ├── orchestrator/bf16/  # ORCHESTRATOR lane (DeepSeek-R1-Distill-Qwen-32B)
│   ├── coder/bf16/         # CODER lane (Qwen2.5-Coder-32B-Instruct)
│   └── fast_rag/bf16/      # FAST_RAG lane (Llama-3.2-11B-Vision-Instruct)
├── gguf/                    # GGUF models for llama.cpp
│   ├── Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf  # SUPER_READER lane
│   └── granite-3.0-8b-instruct-Q4_K_M.gguf   # GOVERNANCE lane
└── embeddings/              # Embedding models (via Python script)
    └── (cached in ~/.cache/huggingface/)
```

## Required Models by Lane

### ORCHESTRATOR Lane
- **Model**: DeepSeek-R1-Distill-Qwen-32B (bf16)
- **Alternate**: `neuralmagic/DeepSeek-R1-Distill-Qwen-32B-fp8` (lower VRAM)
- **Format**: vLLM (Hugging Face)
- **Location**: `models/vllm/orchestrator/bf16/`

### CODER Lane
- **Model**: Qwen2.5-Coder-32B-Instruct (bf16)
- **Alternate**: `neuralmagic/Qwen2.5-Coder-32B-Instruct-fp8`
- **Format**: vLLM (Hugging Face)
- **Location**: `models/vllm/coder/bf16/`

### SUPER_READER Lane
- **Model**: Nemotron-8B-UltraLong-4M
- **Format**: GGUF (Q4_K_M quantization)
- **Filename**: `Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf`
- **Location**: `models/gguf/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf`

### FAST_RAG Lane
- **Model**: meta-llama/Llama-3.2-11B-Vision-Instruct (bf16)
- **Format**: vLLM (Hugging Face)
- **Location**: `models/vllm/fast_rag/bf16/`

### GOVERNANCE Lane
- **Model**: granite-3.0-8b-instruct (Q4_K_M)
- **Format**: GGUF (Q4_K_M quantization)
- **Filename**: `granite-3.0-8b-instruct-Q4_K_M.gguf`
- **Location**: `models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf`

### Minimal smoke-test models (for bring-up)
- **Purpose**: keep services startable and enable post-deploy smoke tests before full production models land.
- **Download**: `./ops/download_minimal_models.sh` (uses `huggingface_hub`; optional `HF_TOKEN` if rate-limited).
- **Paths (after download)**:
  - vLLM: `/models/minimal/vllm/TinyLlama-1.1B-Chat-v1.0` (~2–3GB)
  - GGUF: `/models/minimal/gguf/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf` (~0.7GB)
- **When to use**: smoke tests, CI bring-up, or while waiting on production-scale downloads.

## Environment Variables

### Download Control

```bash
# Enable downloading specific model types
export ARGOS_DOWNLOAD_SUPER_READER=true
export ARGOS_DOWNLOAD_GOVERNANCE=true
export ARGOS_DOWNLOAD_VLLM=true
export ARGOS_DOWNLOAD_EMBEDDINGS=true

# Set models directory
export ARGOS_MODELS_DIR=/data/cortex-models

# Hugging Face token (for gated models)
export HF_TOKEN=your_token_here
```

### Model Path Configuration

After downloading, set these environment variables:

```bash
# GGUF Models (llama.cpp)
export ARGOS_LANE_SUPER_READER_MODEL_PATH=/data/cortex-models/gguf/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf
export ARGOS_LANE_GOVERNANCE_MODEL_PATH=/data/cortex-models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf

# vLLM Models (configured via docker-compose volumes)
export ARGOS_LANE_ORCHESTRATOR_URL=http://localhost:8000/v1
export ARGOS_LANE_ORCHESTRATOR_MODEL=DeepSeek-R1-Distill-Qwen-32B
export ARGOS_LANE_CODER_URL=http://localhost:8000/v1
export ARGOS_LANE_CODER_MODEL=Qwen2.5-Coder-32B-Instruct
export ARGOS_LANE_FAST_RAG_URL=http://localhost:8000/v1
export ARGOS_LANE_FAST_RAG_MODEL=Llama-3.2-11B-Vision-Instruct
```

## Docker Compose Configuration

Update `ops/docker-compose.strix.yml` to mount the models directory:

```yaml
services:
  inference-vllm:
    volumes:
      - /data/cortex-models/vllm:/models/vllm  # vLLM models
      - /data/cortex-models/vllm:/root/.cache/huggingface  # Hugging Face cache
  
  inference-llamacpp:
    volumes:
      - /data/cortex-models/gguf:/models/gguf  # GGUF models
```

Or use relative path:

```yaml
services:
  inference-vllm:
    volumes:
      - ./models/vllm:/models/vllm
      - ./models/vllm:/root/.cache/huggingface
  
  inference-llamacpp:
    volumes:
      - ./models/gguf:/models/gguf
```

## Download Scripts

### Shell Script: `ops/download_all_models.sh`

Comprehensive script that downloads all models:

```bash
# Download all models
./ops/download_all_models.sh

# Skip specific model types
./ops/download_all_models.sh --skip-vllm
./ops/download_all_models.sh --skip-gguf
./ops/download_all_models.sh --skip-embeddings

# Custom directory
./ops/download_all_models.sh --models-dir /data/cortex-models
```

### Python Script: `backend/scripts/download_models.py`

More flexible Python-based downloader:

```bash
# Download embeddings only
python3 backend/scripts/download_models.py

# Download GGUF models
export ARGOS_DOWNLOAD_SUPER_READER=true
export ARGOS_DOWNLOAD_GOVERNANCE=true
python3 backend/scripts/download_models.py

# Download vLLM models
export ARGOS_DOWNLOAD_VLLM=true
python3 backend/scripts/download_models.py
```

## Verification

After downloading, verify models are present:

```bash
# Check vLLM models
ls -lh models/vllm/*/

# Check GGUF models
ls -lh models/gguf/*.gguf

# Check disk usage
du -sh models/
```

Expected sizes:
- vLLM models: ~30-60GB each (depending on quantization)
- GGUF models: ~5GB each
- Embeddings: ~500MB total

## Troubleshooting

### Model Not Found

If a model repository doesn't exist or has a different name:
1. Check Hugging Face Hub: https://huggingface.co/models
2. Update model names in `download_models.py` or `download_all_models.sh`
3. Some models may require authentication (set `HF_TOKEN`)

### Insufficient Disk Space

Models require significant disk space:
- **Minimum**: ~50GB for essential models
- **Recommended**: ~200GB for all models
- **Full**: ~500GB+ for unquantized models

Use quantization to reduce size:
- 4-bit quantization: ~50% size reduction
- 8-bit quantization: ~25% size reduction

### Download Failures

1. **Network issues**: Check internet connection
2. **Authentication**: Set `HF_TOKEN` for gated models
3. **Disk space**: Ensure sufficient free space
4. **Permissions**: Ensure write access to models directory

### Container Can't Find Models

1. Verify volume mounts in docker-compose.yml
2. Check model paths match environment variables
3. Ensure models directory is accessible from container
4. Check file permissions (models should be readable)

## Post-deploy smoke test

- vLLM API (any non-5xx response is acceptable for smoke):  
  `curl -s -o /tmp/vllm-smoke.txt -w "%{http_code}" -X POST http://localhost:8000/v1/completions -H "Content-Type: application/json" -d '{"model":"smoke-test","prompt":"ping"}'`
- llama.cpp health:  
  `curl -s -o /tmp/llama-smoke.txt -w "%{http_code}" http://localhost:8080/health`
- If either returns 5xx or times out, re-run `ops/model-preflight.sh <path>` and inspect `docker compose logs`.

## Next Steps

After downloading models:

1. **Update Docker Compose**: Mount models directory
2. **Set Environment Variables**: Configure model paths
3. **Start Services**: Launch containers with models
4. **Verify**: Test each lane with sample requests

See `docs/specs/04-runtime-and-ops-strix-optimization.md` for deployment details.
