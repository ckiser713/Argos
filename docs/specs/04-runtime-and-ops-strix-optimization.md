# Runtime: AMD Strix Halo Optimization & Memory Map

## Overview
This specification details the operational deployment of Cortex on **AMD Strix Halo APUs with 128GB Unified RAM**. It focuses on memory partitioning between **vLLM (ROCm)** and **llama.cpp** to support the massive context windows required by the "Doc Atlas" and "Brain" components.

## Hardware Profile
- **SoC:** AMD Strix Halo (Ryzen AI MAX+)
- **Memory:** 128 GB LPDDR5X (Unified)
- **Shareable VRAM Target:** ~96 GB - 110 GB (leaving 18-32 GB for OS/System).

## Container Strategy
To maximize stability and context length, we split inference into two distinct containers/processes.

### Service A: "The Fast Lane" (vLLM - ROCm)
- **Engine:** vLLM (Optimized for ROCm 6.x/7.x)
- **Primary Role:** Orchestrator (Thinking), Coder, Fast-RAG.
- **Models:** Qwen3-30B-Thinking (4-bit), Qwen3-Coder-30B (4-bit).
- **Memory Budget:** **48 GB**.
- **Configuration:**
  - `GPU_MEMORY_UTILIZATION=0.45` (Approx 48GB of the 110GB pool).
  - `MAX_MODEL_LEN=32768` (Restricted context for speed).

### Service B: "The Deep Lane" (llama.cpp - OpenCL/ROCm)
- **Engine:** `llama-server` (llama.cpp)
- **Primary Role:** Super-Reader (Deep Ingest).
- **Model:** Nemotron-8B-UltraLong-4M (Q4_K_M GGUF).
- **Memory Budget:** **64 GB**.
- **Configuration:**
  - **KV Cache Offloading:** This is the critical optimization. vLLM requires contiguous VRAM for KV cache. llama.cpp allows GGUF quantization of the KV cache and smarter system RAM offloading.
  - `-c 1000000` (1M Context) to `-c 4000000` (4M Context).
  - `-ngl 99` (Offload all layers).
  - `--cache-type-k q8_0` (Quantize KV cache to 8-bit to fit 4M tokens).

## Memory Map (128 GB Total)

| Segment | Allocation | Purpose |
| :--- | :--- | :--- |
| **OS / System** | 16 GB | Desktop environment, OS overhead, Browser. |
| **Cortex Backend** | 4 GB | FastAPI, Python overhead, Vector DB (Qdrant). |
| **vLLM (Service A)** | 44 GB | Weights for Qwen-30B (~20GB) + Context Cache (~24GB). |
| **llama.cpp (Service B)** | 64 GB | Weights for Nemotron-8B (~6GB) + **Massive KV Cache (~58GB)**. |

*Note: In "Burst Mode" (running a 4M token ingest), Service A (vLLM) should be paused/scaled down to release memory to Service B.*

## Docker Compose Overrides (`ops/docker-compose.strix.yml`)

```yaml
services:
  # The Brain & Coder
  inference-vllm:
    image: vllm-rocm-strix:latest
    devices:
      - /dev/kfd
      - /dev/dri
    environment:
      - VLLM_GPU_MEMORY_UTILIZATION=0.40
    ports:
      - "8000:8000"

  # The Super-Reader
  inference-llamacpp:
    image: ghcr.io/ggerganov/llama.cpp:full-rocm
    devices:
      - /dev/kfd
      - /dev/dri
    command: -m /models/nemotron-4m.gguf -c 2000000 --port 8080 -ngl 99
    ports:
      - "8080:8080"
Operational Workflows
1. The "Seismic" Ingest (Mode: Deep Reader)
When the user uploads a massive monorepo zip:

Backend detects file size > 50MB.

IngestService routes request to CORTEX_LANE_SUPER_READER_URL (Port 8080).

llama.cpp processes the 1M+ token stream.

Constraint: User accepts slower latency (2-5 t/s) for deep analysis.

2. The "Daily Driver" (Mode: Interactive)
When the user chats or asks for a plan:

AgentService routes request to CORTEX_LLM_BASE_URL (Port 8000).

vLLM serves Qwen-Thinking at high speed (30-50 t/s).