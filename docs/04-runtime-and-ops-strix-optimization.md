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
- **Models:** DeepSeek-R1-Distill-Qwen-32B (4-bit), Qwen2.5-Coder-32B-Instruct (4-bit).
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
version: '3.8'

services:
  # The Brain & Coder
  inference-vllm:
    image: vllm-rocm-strix:latest
    container_name: cortex-vllm-fast-lane
    devices:
      - /dev/kfd
      - /dev/dri
    environment:
      - VLLM_GPU_MEMORY_UTILIZATION=0.40
      - VLLM_MAX_MODEL_LEN=32768
      - VLLM_HOST=0.0.0.0
      - VLLM_PORT=8000
    ports:
      - "8000:8000"
    volumes:
      - /models/vllm:/models
    deploy:
      resources:
        limits:
          memory: 48G
        reservations:
          memory: 48G
    restart: unless-stopped
    networks:
      - cortex-network

  # The Super-Reader
  inference-llamacpp:
    image: ghcr.io/ggerganov/llama.cpp:full-rocm
    container_name: cortex-llamacpp-deep-lane
    devices:
      - /dev/kfd
      - /dev/dri
    command: >
      -m /models/nemotron-4m.gguf
      -c 2000000
      --port 8080
      -ngl 99
      --cache-type-k q8_0
      --host 0.0.0.0
    ports:
      - "8080:8080"
    volumes:
      - /models/gguf:/models
    deploy:
      resources:
        limits:
          memory: 64G
        reservations:
          memory: 64G
    restart: unless-stopped
    networks:
      - cortex-network

networks:
  cortex-network:
    driver: bridge
```

## Operational Workflows

### 1. The "Seismic" Ingest (Mode: Deep Reader)

When the user uploads a massive monorepo zip:

1. **Backend detects file size > 50MB.**
2. **IngestService routes request to `ARGOS_LANE_SUPER_READER_URL` (Port 8080).**
3. **llama.cpp processes the 1M+ token stream.**
4. **Constraint:** User accepts slower latency (2-5 t/s) for deep analysis.

**Implementation:**
```python
# In IngestService.process_job()
if self._should_use_deep_ingest(file_path):
    # Route to SUPER_READER lane
    analysis = generate_text(
        prompt=deep_analysis_prompt,
        project_id=job.project_id,
        lane=ModelLane.SUPER_READER,
        max_tokens=4000,  # Allow longer responses
    )
```

### 2. The "Daily Driver" (Mode: Interactive)

When the user chats or asks for a plan:

1. **AgentService routes request to `ARGOS_LLM_BASE_URL` (Port 8000).**
2. **vLLM serves Qwen-Thinking at high speed (30-50 t/s).**

**Implementation:**
```python
# In ProjectManagerGraph
response = generate_text(
    prompt=user_prompt,
    project_id=project_id,
    lane=ModelLane.ORCHESTRATOR,  # Fast lane
    max_tokens=1000,
)
```

### 3. Burst Mode: Memory Reallocation

When running a 4M token ingest:

1. **Pause/Scale Down vLLM Service:**
   ```bash
   docker-compose -f ops/docker-compose.strix.yml stop inference-vllm
   ```

2. **Increase llama.cpp memory allocation:**
   ```yaml
   # Temporarily increase memory limit
   deploy:
     resources:
       limits:
         memory: 96G  # Use freed vLLM memory
   ```

3. **Restart llama.cpp with larger context:**
   ```bash
   docker-compose -f ops/docker-compose.strix.yml up -d inference-llamacpp
   ```

4. **After ingest completes, restore normal operation:**
   ```bash
   docker-compose -f ops/docker-compose.strix.yml start inference-vllm
   ```

## Performance Targets

| Lane | Model | Context Window | Tokens/sec | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **ORCHESTRATOR** | DeepSeek-R1-Distill-Qwen-32B | 32k - 128k | 30-50 t/s | Interactive planning |
| **CODER** | Qwen2.5-Coder-32B-Instruct | 128k - 500k | 20-40 t/s | Code analysis |
| **SUPER-READER** | Nemotron-8B-UltraLong | 1M - 4M | 2-5 t/s | Deep ingest |
| **FAST-RAG** | Llama-3.2-11B-Vision-Instruct | 16k - 128k | 40-60 t/s | RAG queries |
| **GOVERNANCE** | granite-3.0-8b-instruct | 200k | 10-20 t/s | Compliance checks |

## Monitoring & Health Checks

### Memory Monitoring

```bash
# Check memory usage
watch -n 1 'free -h && echo "---" && docker stats --no-stream'
```

### Service Health Endpoints

- **vLLM Health:** `http://localhost:8000/health`
- **llama.cpp Health:** `http://localhost:8080/health` (if supported)

### Cortex Backend Health

The Cortex backend should monitor lane availability:

```python
# In backend/app/services/llm_service.py
def check_lane_health(lane: ModelLane) -> bool:
    """Check if a lane's endpoint is available."""
    try:
        base_url, model_name, backend = resolve_lane_config(lane)
        # Simple HTTP check
        import requests
        health_url = base_url.replace("/v1", "/health")
        response = requests.get(health_url, timeout=2)
        return response.status_code == 200
    except Exception:
        return False
```

## Troubleshooting

### Issue: OOM (Out of Memory) Errors

**Symptoms:** Service crashes or requests fail with memory errors.

**Solutions:**
1. Reduce `VLLM_GPU_MEMORY_UTILIZATION` (e.g., from 0.40 to 0.35)
2. Reduce context window (`MAX_MODEL_LEN`)
3. Enable burst mode (pause one service)
4. Use more aggressive quantization (Q4_K_M → Q3_K_M)

### Issue: Slow Inference

**Symptoms:** Tokens/sec lower than targets.

**Solutions:**
1. Check ROCm driver version (should be 6.x/7.x)
2. Verify GPU layers are offloaded (`-ngl 99`)
3. Check CPU/GPU utilization (`htop`, `rocm-smi`)
4. Reduce context window if not needed

### Issue: Port Conflicts

**Symptoms:** Services fail to start, port already in use.

**Solutions:**
1. Check existing containers: `docker ps`
2. Stop conflicting services
3. Modify port mappings in docker-compose.yml

## Deployment Checklist

- [ ] ROCm drivers installed and verified (`rocm-smi`)
- [ ] Models downloaded to `/models/vllm` and `/models/gguf`
- [ ] Docker Compose override file configured
- [ ] Environment variables set (see Configuration Parameters)
- [ ] Memory limits verified (`free -h`)
- [ ] Ports 8000 and 8080 available
- [ ] Health checks passing
- [ ] Test requests to each lane endpoint

## Future Optimizations

1. **Dynamic Memory Allocation:** Automatically adjust memory allocation based on workload
2. **Model Caching:** Keep frequently used models in memory
3. **Request Queuing:** Queue requests when a lane is busy
4. **Predictive Scaling:** Pre-scale services based on time-of-day patterns
5. **Multi-GPU Support:** Distribute models across multiple GPUs if available
