# vLLM Docker Image Specification for Cortex

**Document Purpose**: Comprehensive specification for building/understanding the vLLM Docker image in the Cortex project  
**Target Audience**: AI/ML engineers building or maintaining the vLLM Docker image  
**Date**: December 2025

---

## Executive Summary

The vLLM Docker image (`vllm-rocm-strix:latest`) is the **primary inference engine** for the Cortex project. It serves as the high-performance LLM inference backend for multiple specialized "lanes" in the system, enabling fast model switching and multi-model orchestration on AMD ROCm-equipped hardware (specifically gfx1151 architecture with unified memory).

The image is a **pre-built, optimized artifact** (22GB) rather than built from source in most deployments. It contains:
- ROCm 7.1 support for AMD Radeon GPUs
- PyTorch 2.9.1 with ROCm bindings
- vLLM inference engine optimized for long-context models
- OpenAI-compatible API server
- Support for multiple quantization formats (BF16, AWQ, GPTQ)

---

## System Architecture Context

### Where vLLM Fits in Cortex

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CORTEX SYSTEM                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  FastAPI Backend                LangGraph Orchestration             │
│  (Port 8000)                     (Agent Planning/Routing)           │
│        ▲                                 ▲                          │
│        │                                 │                          │
│        └──────────────────────┬──────────┘                          │
│                               │ Routes requests by Lane            │
│                               │ (Orchestrator/Coder/FastRAG)       │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │          INFERENCE LAYER (Multi-Lane Orchestration)         │  │
│  ├─────────────────────────────────────────────────────────────┤  │
│  │                                                             │  │
│  │  ┌──────────────────────┐  ┌──────────────────────────┐  │  │
│  │  │ vLLM Container       │  │ llama.cpp Servers        │  │  │
│  │  │ (This Document)      │  │ (Separate Instances)     │  │  │
│  │  ├──────────────────────┤  ├──────────────────────────┤  │  │
│  │  │ Shared GPU Memory:   │  │ Super Reader (Port 8080) │  │  │
│  │  │ - 48GB for vLLM      │  │ Governance (Port 8081)   │  │  │
│  │  │                      │  │                          │  │  │
│  │  │ Lanes (Sequential):  │  │ Dedicated/Persistent:    │  │  │
│  │  │ 1. Orchestrator      │  │ - Always available       │  │  │
│  │  │    (30B-Thinking)    │  │ - No switching overhead  │  │  │
│  │  │                      │  │                          │  │  │
│  │  │ 2. Coder            │  │                          │  │  │
│  │  │    (30B-Coder)       │  │                          │  │  │
│  │  │                      │  │                          │  │  │
│  │  │ 3. FastRAG          │  │                          │  │  │
│  │  │    (7B-Mistral)      │  │                          │  │  │
│  │  │                      │  │                          │  │  │
│  │  │ Features:            │  │                          │  │  │
│  │  │ - Request Queuing    │  │                          │  │  │
│  │  │ - Model Switching    │  │                          │  │  │
│  │  │ - GPU Memory Mgmt    │  │                          │  │  │
│  │  └──────────────────────┘  └──────────────────────────┘  │  │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Storage Layer: Qdrant (Vector DB) + PostgreSQL (Metadata)        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Hardware: AMD Radeon (gfx1151) with 128GB unified memory + ROCm 7.1
```

---

## Detailed vLLM Container Specification

### 1. Core Responsibilities

The vLLM Docker image must handle:

#### A. **Multi-Lane Model Serving**
- **Orchestrator Lane**: DeepSeek-R1-Distill-Qwen-32B (planning, routing, decision-making)
- **Coder Lane**: Qwen2.5-Coder-32B-Instruct (code analysis, refactoring, gap analysis)
- **FastRAG Lane**: Llama-3.2-11B-Vision-Instruct (retrieval-augmented generation, chat)

Each lane has a distinct model with different capabilities:
- **Context Window Sizes**: 32K-1M tokens
- **Model Sizes**: 7B-30B parameters
- **Specialized Training**: Task-specific fine-tuning (thinking, coding, retrieval)

#### B. **Sequential Model Switching**
- Load one model from the three vLLM-based lanes into GPU VRAM at a time
- Switch between models when a different lane is requested
- Handle switching overhead (30-60 seconds per model load)
- Queue incoming requests during model transitions
- Ensure no requests are lost during switches

#### C. **OpenAI-Compatible API Server**
- Listen on port 8000 (mapped to 11434 externally)
- Implement `/v1/completions`, `/v1/chat/completions` endpoints
- Support streaming responses (SSE)
- Provide `/v1/models` endpoint listing available models
- Implement health checks at `/health`
- Accept model names in requests to trigger lane selection

#### D. **GPU Memory Management**
- Allocate 48GB GPU VRAM for vLLM (out of 128GB total)
- Reserve 64GB for llama.cpp services (Super Reader, Governance)
- Support BF16 (bfloat16) precision for efficient memory usage
- Implement GPU memory utilization monitoring
- Provide memory usage metrics in API responses or logs

#### E. **Performance Optimization for ROCm**
- Use AMD ROCm 7.1 for GPU acceleration
- Target gfx1151 architecture (specific AMD GPU)
- Leverage unified memory architecture (RDMA between GPU and system RAM)
- Support FlashAttention or similar for long-context inference
- Optimize for models with 256K-1M token context windows

---

### 2. Base Image & Dependencies

#### Base Image
```dockerfile
FROM rocm/pytorch:rocm7.1_ubuntu22.04_py3.11_pytorch_2.9.1
```

**Why this base image:**
- ROCm 7.1: Latest AMD GPU compute toolkit (backward compatible)
- Ubuntu 22.04: LTS, stable, well-supported
- Python 3.11: Matches Cortex backend requirements
- PyTorch 2.9.1: Latest stable with ROCm support

#### Key System Dependencies
- **CUDA/ROCm Libraries**: hipblaslt, rocblas, rocrand (GPU compute)
- **Build Tools**: gcc, g++, make, cmake (for vLLM compilation)
- **Python Development**: python3.11-dev, python3.11-venv
- **Network**: curl (for health checks)
- **Storage**: git (for model downloading if needed)

#### Python Package Stack

**Core Dependencies:**
- **vLLM** (0.6.1+): Main inference engine
  - Includes optimized attention mechanisms
  - ROCm support built-in
  - Handles model loading, scheduling, memory management

- **PyTorch** (2.9.1 ROCm-enabled): Deep learning framework
  - Pre-installed in base image
  - Used by vLLM for model inference
  - ROCm HIP bindings for GPU acceleration

- **Transformers** (4.46+): Hugging Face model loading
  - Required by vLLM for model downloading
  - Handles tokenization, model configuration
  - Supports quantization formats (AWQ, GPTQ, BF16)

- **pydantic** (2.0+): Request/response validation
  - Used for OpenAI API schema compliance
  - Type checking and serialization

- **httpx/aiohttp**: Async HTTP client
  - Used internally by vLLM
  - Supports streaming responses

**Optional Dependencies (recommended):**
- **flash-attn** (2.5+): Optimized attention for long contexts
  - Dramatically improves inference speed
  - Reduces memory footprint
  - Not always installable on ROCm (fallback to standard attention)

- **lm-format-enforcer**: Constrains model output format
  - Useful for structured outputs (JSON, code)
  - Optional for chat/completion use cases

- **openai** (1.0+): For testing
  - Verify API compatibility

---

### 3. Environment Configuration

#### Required Environment Variables

These variables MUST be configurable at runtime (passed to container):

```bash
# Model Selection (determines which model to load first)
VLLM_MODEL="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"  # Orchestrator model by default
# OR specify full model path if already cached:
VLLM_MODEL="/models/vllm/orchestrator/bf16/model.safetensors"

# GPU/Hardware Configuration
HIP_VISIBLE_DEVICES=0                       # Which AMD GPU to use (0-indexed)
HSA_OVERRIDE_GFX_VERSION=11.0.0            # Force gfx1151 support
VLLM_GPU_MEMORY_UTILIZATION=0.45           # 48GB for vLLM out of 128GB total

# API Server Configuration
VLLM_HOST=0.0.0.0                          # Listen on all interfaces
VLLM_PORT=8000                             # OpenAI-compatible API port
VLLM_LOG_REQUESTS=true                     # Log API requests for debugging

# Model Configuration
VLLM_MAX_MODEL_LEN=32768                   # Context window (tokens)
VLLM_TENSOR_PARALLEL_SIZE=1                # Single GPU (no distribution needed)
VLLM_PIPELINE_PARALLEL_SIZE=1              # No pipeline parallelism

# Quantization & Precision
VLLM_DTYPE=bfloat16                        # Use BF16 for efficient memory
VLLM_ENFORCE_EAGER=0                       # Use graph execution (faster)

# Performance Tuning
VLLM_BLOCK_SIZE=16                         # KV cache block size
VLLM_SWAP_SPACE=4                          # CPU swap space in GB (for context overflow)
VLLM_NUM_GPU_BLOCKS_OVERRIDE=None           # Auto-calculate GPU blocks

# Authentication (optional)
VLLM_API_KEY=None                          # No key required for internal network

# Logging
VLLM_LOG_LEVEL=INFO                        # Verbosity level
LOG_DIRECTORY=/var/log/vllm                # Persist logs outside container
```

#### Environment Variables for Testing

```bash
# Enable verbose output for debugging
VLLM_LOGGING_LEVEL=DEBUG

# Use smaller test model for quick startup
VLLM_MODEL="TinyLlama/TinyLlama-1.1B"

# Disable GPU (CPU-only mode for testing)
VLLM_CPU_ONLY=0  # Set to 1 if GPU unavailable

# Skip model downloading (for offline testing)
HF_DATASETS_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

#### Hugging Face Integration

```bash
# For authenticated model access
HF_TOKEN=${HF_TOKEN:-}  # Passed at build or runtime
HF_HOME=/root/.cache/huggingface  # Model cache location
HF_HUB_OFFLINE=0  # Allow online downloads

# Unsafe SSL (only for development)
HF_ALLOW_CODE_EVAL=0  # Security: disable code execution
TRANSFORMERS_TRUST_REMOTE_CODE=1  # Trust HF model code
```

---

### 4. Ports & Network Interface

#### Port Mapping

| Port | Protocol | Purpose | Routing |
|------|----------|---------|---------|
| **8000** | HTTP | OpenAI-compatible API | Internal (FastAPI ↔ vLLM) |
| **8000** | TCP (Raw) | Metrics/health | `GET /health`, `GET /metrics` |

**Port Mapping in docker-compose.yml:**
```yaml
ports:
  - "11434:8000"  # External: 11434 → Internal: 8000
```

This maps the standard Ollama port (11434) externally, allowing clients to treat vLLM like a standard Ollama server.

#### Network Configuration

- **Host Mode**: NO (security, isolation)
- **Network**: Custom bridge network (shared with backend, qdrant)
- **DNS**: Inherited from docker engine
- **Service Discovery**: Docker DNS (`inference-vllm:8000` from other containers)

**Typical docker-compose network config:**
```yaml
services:
  inference-engine:
    networks:
      - cortex-network
    # FastAPI backend connects via: http://inference-vllm:8000/v1
```

---

### 5. Storage & Model Loading

#### Volume Mounts

```yaml
volumes:
  # Model cache: Persistent storage for downloaded models
  - ./models:/root/.cache/huggingface
    # Inside container: models are cached at ~/.cache/huggingface
    # Host directory: ./models/ (project root)
    # Purpose: Avoid re-downloading models on restart
    # Size: ~50GB+ for multiple large models
  
  # Shared memory: Large buffer for communication
  - /dev/shm:/dev/shm
    # Required for: tensor parallelism, shared buffers
    # Size: 16GB (set via shm_size)
    # Purpose: Inter-process communication, temporary buffers
  
  # Optional: Logs persistence
  - ./logs:/var/log/vllm
    # Persist API request logs, errors outside container
    # Useful for: debugging, monitoring, audit trails
  
  # Optional: Cache optimization
  - /tmp/.cache:/tmp/cache
    # Temporary files, intermediate results
    # Volatile (can be cleared between runs)
```

**Shared Memory Configuration:**
```yaml
shm_size: '16gb'  # Essential for large models
# Without this, tensor operations may fail or be slow
```

#### Model Loading Strategy

**Approach 1: Pre-loaded Models (Recommended)**
```
Project Structure:
  /models/
    ├── vllm/
    │   ├── orchestrator/bf16/  # DeepSeek-R1-Distill-Qwen-32B
    │   │   └── model.safetensors, config.json, tokenizer.model
    │   ├── coder/bf16/         # Qwen2.5-Coder-32B-Instruct
    │   │   └── ...
    │   └── fast_rag/bf16/      # Llama-3.2-11B-Vision-Instruct
    │       └── ...
    └── vllm-cache/             # HF hub cache (fallback)
        └── (huggingface_hub downloads here)
```

**Benefits:**
- No network download on startup (faster cold start)
- Models are under version control
- Deterministic behavior
- Offline deployment support

**Approach 2: On-Demand Download (Fallback)**
- If model not found locally, download from Hugging Face
- Requires HF_TOKEN for gated models
- First startup slower (30-60s per model)
- Cached for subsequent loads

#### Disk Space Requirements

```
Orchestrator (DeepSeek-R1-Distill-Qwen-32B):     ~70GB (BF16)
Coder (Qwen2.5-Coder-32B-Instruct):      ~70GB (BF16)
FastRAG (Llama-3.2-11B-Vision-Instruct):        ~20GB (BF16)
─────────────────────────────────────
Total for 3 models:           ~160GB
Plus HF hub overhead:         +10GB
────────────────────────────────────
Recommended volume size:      200GB+
```

---

### 6. GPU & Hardware Integration

#### Hardware Access

**Required Device Passes:**
```yaml
devices:
  - "/dev/kfd"      # AMD Kernel Fusion Driver (GPU compute)
  - "/dev/dri"      # Direct Rendering Interface (GPU access)
```

**Why:**
- `/dev/kfd`: Direct GPU compute access via HIP
- `/dev/dri`: Display/render interfaces (even in headless mode)

**Required Group Additions:**
```yaml
group_add:
  - video           # GPU device ownership
  - render          # Render device ownership
```

**User Running Container:**
- Should be in `video` and `render` groups on host
- Otherwise, GPU access will be denied

#### ROCm-Specific Configuration

```bash
# AMD GPU Detection & Optimization
HIP_VISIBLE_DEVICES=0              # Use GPU 0
HSA_OVERRIDE_GFX_VERSION=11.0.0   # Force gfx1151 compatibility

# ROCm Runtime Options
export ROCM_HOME=/opt/rocm         # ROCm installation dir (in image)
export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH
export PATH=/opt/rocm/bin:$PATH

# Performance Tuning
HSA_ENABLE_SDMA=1                  # Enable SDMA (System DMA) engines
HSA_ENABLE_INTERRUPT=1             # Enable interrupts for responsiveness
```

#### Memory Architecture

**Cortex Hardware Assumption:**
```
┌─────────────────────────────────────────┐
│  128GB Unified Memory (System + GPU)    │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────┐               │
│  │  GPU VRAM (Visible) │               │
│  │  ~48GB allocated    │               │
│  │  ├─ Model Weights   │  ← vLLM      │
│  │  ├─ KV Caches       │  Manages     │
│  │  └─ Attention Buffers               │
│  └─────────────────────┘               │
│                                         │
│  ┌─────────────────────┐               │
│  │  System RAM         │               │
│  │  ~64GB allocated    │               │
│  │  ├─ Swap Space (4GB)               │
│  │  ├─ llama.cpp (~24GB)             │
│  │  ├─ OS/Backend (~8GB)             │
│  │  └─ Cache/Buffers                  │
│  └─────────────────────┘               │
│                                         │
│  ┌─────────────────────┐               │
│  │  Unified Memory     │               │
│  │  Architecture       │               │
│  │  ├─ Direct GPU      │ ← AMD        │
│  │     access to       │  Specific    │
│  │     system RAM      │             │
│  │  └─ Fast page      │             │
│  │     migration       │             │
│  └─────────────────────┘               │
│                                         │
└─────────────────────────────────────────┘
```

**vLLM GPU Memory Settings:**
```bash
VLLM_GPU_MEMORY_UTILIZATION=0.45
# Interpretation:
# - 45% of 128GB = 57.6GB available
# - But container only sees "GPU VRAM" (48GB physically on GPU)
# - So 45% of 48GB = 21.6GB for model + 26.4GB for KV caches & buffers
# - Actual allocation depends on model size and sequence length
```

---

### 7. API Endpoints & Behavior

#### Core Endpoints (OpenAI-Compatible)

**1. Chat Completions** (Most Common)
```
POST /v1/chat/completions
Content-Type: application/json

Request:
{
  "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",  // Lane selector
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false
}

Response:
{
  "id": "chatcmpl-xxx",
  "object": "text_completion",
  "created": 1733686400,
  "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  }
}

Streaming Response (stream=true):
  Returns SSE (Server-Sent Events) with chunked text data
  Format: data: {"choices":[{"delta":{"content":"token"}}]}
```

**2. Text Completions** (Legacy/Testing)
```
POST /v1/completions
Content-Type: application/json

Request:
{
  "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
  "prompt": "The future of AI is",
  "temperature": 0.8,
  "max_tokens": 100
}

Response:
{
  "id": "cmpl-xxx",
  "object": "text_completion",
  "created": 1733686400,
  "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
  "choices": [
    {
      "index": 0,
      "text": "...",
      "finish_reason": "stop"
    }
  ],
  "usage": {...}
}
```

**3. List Models**
```
GET /v1/models

Response:
{
  "object": "list",
  "data": [
    {
      "id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
      "object": "model",
      "created": 1733686400,
      "owned_by": "vllm"
    },
    ...
  ]
}
```

**4. Health Check** (Docker healthcheck)
```
GET /health

Response:
{
  "status": "ok"
}

Status Codes:
  200: Healthy, ready to serve
  503: Unhealthy (loading model, switching lanes, etc.)
```

#### Cortex Backend Integration Points

**From `backend/app/main.py`:**
```python
# Configuration examples:
llm_backend = "openai"  # Use OpenAI-compatible client
llm_base_url = "http://localhost:11434/v1"  # Maps to inference-vllm:8000 in docker-compose
llm_model_name = "DeepSeek-R1-Distill-Qwen-32B"

# In Strix environment:
lane_orchestrator_url = "http://inference-vllm:8000/v1"  # Route to vLLM
lane_orchestrator_model = "DeepSeek-R1-Distill-Qwen-32B"

lane_coder_url = "http://inference-vllm:8000/v1"
lane_coder_model = "Qwen2.5-Coder-32B-Instruct"

lane_fast_rag_url = "http://inference-vllm:8000/v1"
lane_fast_rag_model = "Llama-3.2-11B-Vision-Instruct"
```

**From `backend/app/services/vllm_lane_manager.py`:**
```python
# Automatic lane switching:
# 1. Request comes for Orchestrator lane
# 2. VLLMLaneManager checks currently loaded model
# 3. If different, triggers model switch (30-60s)
# 4. Queues new requests while switching
# 5. Resumes normal operation
```

---

### 8. Monitoring & Health

#### Health Check Configuration

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s        # Check every 30 seconds
  timeout: 10s         # Fail if no response in 10s
  retries: 3           # Mark unhealthy after 3 failures
  start_period: 60s    # Wait 60s before starting checks
```

**States:**
- **Healthy**: Container responding to API requests normally
- **Unhealthy**: Model loading, switching, or GPU error
- **Starting**: Container launched but model still loading

#### Logging Output

**vLLM logs to stdout** (captured by docker logs):
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

# API Requests (if VLLM_LOG_REQUESTS=true):
INFO:     "POST /v1/chat/completions HTTP/1.1" 200
INFO:     Generated 256 tokens in 8.234 seconds

# Model Loading:
INFO:     Loading model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B...
INFO:     Model loaded successfully
```

**Access logs:**
```bash
docker logs -f inference-vllm
```

#### Metrics & Monitoring (Optional)

**Prometheus-compatible endpoint (not native in vLLM):**
- Can be exposed via:
  - Custom middleware in vLLM fork
  - Sidecar container proxying requests
  - Direct GPU metrics from ROCm

**Key metrics to track:**
- Request latency (time-to-first-token, total time)
- GPU memory utilization (% of 48GB)
- GPU utilization (compute percentage)
- Queue depth (requests waiting during model switch)
- Model switch frequency & duration
- Errors/failures

---

### 9. Error Handling & Resilience

#### Expected Failure Modes

**1. GPU Not Available**
```
Error: Could not find AMD GPU device
Solution: Verify /dev/kfd, /dev/dri exist and are accessible
          Check group membership (video, render groups)
          Verify HIP_VISIBLE_DEVICES=0 matches available GPUs
```

**2. Out of Memory**
```
Error: CUDA out of memory. Tried to allocate 2.5GB
Solution: Reduce GPU_MEMORY_UTILIZATION
          Reduce MAX_MODEL_LEN (context window)
          Use quantized model (AWQ/GPTQ instead of BF16)
          Increase swap space
```

**3. Model Download Fails**
```
Error: Failed to download model from Hugging Face
Solution: Check internet connectivity
          Verify HF_TOKEN if model is gated
          Pre-download model to /models/ volume
          Use TRANSFORMERS_OFFLINE=1 for offline mode
```

**4. Model Load Timeout**
```
Error: Timeout waiting for model to load
Solution: Increase start_period in healthcheck
          Check logs for actual loading duration
          Verify disk space (model file may be corrupted)
```

**5. API Connection Issues**
```
Error: Connection refused on port 8000
Solution: Wait for container startup (up to 60s)
          Check healthcheck logs
          Verify port mapping (11434:8000)
          Ensure container is in correct network
```

#### Graceful Degradation

**vLLM container restarts:**
1. Cortex backend detects connection failure to inference-vllm:8000
2. Falls back to secondary inference source:
   - llama.cpp services (SUPER_READER, GOVERNANCE)
   - Remote API (if configured)
   - Returns error with retry guidance
3. Automatically attempts reconnection every 5 seconds
4. Logs failure reason with diagnostic info

---

### 10. Dockerfile Structure (Reference)

**Complete Dockerfile for building from source:**
```dockerfile
# ROCm Base Image with PyTorch
FROM rocm/pytorch:rocm7.1_ubuntu22.04_py3.11_pytorch_2.9.1

# 1. System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Python Environment Setup
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

# 3. vLLM Installation
# Option A: From PyPI (easiest, may not be latest ROCm-optimized)
RUN pip install --upgrade pip && \
    pip install vllm>=0.6.1 transformers pydantic

# Option B: From Source (most control, slower)
# RUN git clone https://github.com/vllm-project/vllm.git && \
#     cd vllm && \
#     pip install -e . --no-build-isolation

# 4. ROCm Environment Variables (in container)
ENV HIP_VISIBLE_DEVICES=0
ENV HSA_OVERRIDE_GFX_VERSION=11.0.0
ENV ROCM_HOME=/opt/rocm
ENV LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH

# 5. Entry Point
EXPOSE 8000
ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
```

---

### 11. Deployment & Lifecycle

#### Startup Sequence

```
1. docker-compose up -d inference-engine
2. Container created, /dev/kfd, /dev/dri mounted
3. ROCm libraries initialized (HIP runtime)
4. vLLM process started
5. Model loading begins (prints to logs)
   - Downloads model from HF if needed (5-20 min on first run)
   - Loads model weights to GPU (2-5 min)
   - Initializes tokenizer & attention kernels (30s)
6. API server listening on 0.0.0.0:8000
7. Healthcheck succeeds → container marked HEALTHY
8. FastAPI backend connects and starts serving requests
Total time: 5-30 minutes (depends on model size, network, GPU)
```

#### Graceful Shutdown

```
docker-compose down inference-engine
OR
docker stop inference-vllm

Sequence:
1. SIGTERM signal sent to container
2. vLLM handles ongoing requests (up to 10s grace period)
3. GPU memory released
4. Process exits
5. Container stopped (can be restarted immediately)
```

#### Model Switching (Runtime)

**Triggered by:**
- New request arrives for different lane
- Backend calls different endpoint with different model name

**Process:**
```
Current: Orchestrator model loaded in GPU
↓
Request arrives for Coder model
↓
1. Queue request (waiting state)
2. Unload Orchestrator model (release GPU memory)
3. Load Coder model (30-60s)
4. Process queued request
5. Subsequent requests for Coder model processed immediately
```

---

### 12. Testing & Validation

#### Pre-Deployment Checks

```bash
# 1. GPU Access
docker run --rm \
  --device /dev/kfd --device /dev/dri \
  rocm/rocm-terminal \
  rocm-smi

# 2. Model Download (with HF token if needed)
docker run --rm \
  -e HF_TOKEN=${HF_TOKEN} \
  -v ./models:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('deepseek-ai/DeepSeek-R1-Distill-Qwen-32B')"

# 3. vLLM Server Startup
docker-compose up inference-engine
sleep 60  # Wait for model loading
docker logs inference-vllm | grep "Application startup complete"

# 4. API Connectivity
curl -X GET http://localhost:11434/v1/models

# 5. Simple Inference Test
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
  }'
```

#### Integration Test (E2E)

```bash
# From Cortex backend:
1. Start backend service
2. POST /api/agents/run with task requiring Orchestrator lane
3. Backend routes request to inference-vllm:8000/v1/chat/completions
4. Verify response received and processed
5. Check agent step created with LLM output
```

---

### 13. Configuration Examples

#### Development Setup (CPU Testing)

```yaml
# docker-compose.dev.yml
inference-engine:
  image: vllm/vllm-openai:latest
  ports:
    - "11434:8000"
  environment:
    - VLLM_MODEL=TinyLlama/TinyLlama-1.1B
    - VLLM_GPU_MEMORY_UTILIZATION=0.9
    - VLLM_MAX_MODEL_LEN=4096
  shm_size: '4gb'
  # No GPU devices needed
```

#### Strix Production Setup (ROCm AMD)

```yaml
# ops/docker-compose.yml
inference-engine:
  image: vllm-rocm-strix:latest
  devices:
    - "/dev/kfd"
    - "/dev/dri"
  group_add:
    - video
    - render
  ports:
    - "11434:8000"
  environment:
    - VLLM_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-32B  # Orchestrator
    - HIP_VISIBLE_DEVICES=0
    - HSA_OVERRIDE_GFX_VERSION=11.0.0
    - VLLM_GPU_MEMORY_UTILIZATION=0.45
    - VLLM_MAX_MODEL_LEN=32768
  volumes:
    - ./models:/root/.cache/huggingface
    - /dev/shm:/dev/shm
  shm_size: '16gb'
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 120s
```

---

## Summary

The vLLM Docker image is the **high-performance inference backbone** of Cortex. It must:

1. **Serve multiple specialized models** through a unified OpenAI-compatible API
2. **Handle sequential model switching** on constrained GPU memory (48GB shared of 128GB total)
3. **Optimize for long-context inference** (32K-1M tokens) using ROCm and AMD GPUs
4. **Queue requests gracefully** during model transitions (30-60s overhead)
5. **Integrate seamlessly** with FastAPI backend and LangGraph orchestration
6. **Provide real-time monitoring** through health checks and logging
7. **Support offline deployment** with pre-cached models

**Key Technical Points:**
- Base: ROCm 7.1 + PyTorch 2.9.1 on Ubuntu 22.04
- Models: 3 vLLM lanes (Orchestrator, Coder, FastRAG) + 2 llama.cpp lanes (Super Reader, Governance)
- Memory: 48GB GPU VRAM for vLLM, 64GB system RAM for other services
- API: OpenAI-compatible `/v1/*` endpoints on port 8000
- Hardware: AMD Radeon gfx1151 with unified memory architecture

This specification provides everything needed to understand, build, deploy, and maintain the vLLM Docker image for the Cortex project.
