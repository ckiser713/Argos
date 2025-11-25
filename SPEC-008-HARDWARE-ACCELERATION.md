# SPEC-008: ROCm & vLLM Hardware Acceleration

## Context
The PRD specifies an **AMD Ryzen AI MAX+ 395**. Standard PyTorch builds will not utilize the NPU/GPU efficiently. We must build a custom vLLM container.

## Requirements
- **Base Image:** `rocm/pytorch:latest` (ROCm 6.1+ compatible).
- **Inference Engine:** vLLM compiled for ROCm.
- **Model:** `Llama-3-70B-Instruct-AWQ` (Quantized) to fit comfortably in ~40GB VRAM, leaving room for context.

## Implementation Guide

### 1. `ops/Dockerfile.vllm`
```dockerfile
FROM rocm/pytorch:rocm6.1_ubuntu22.04_py3.10_pytorch_2.1.2

# Install build deps
RUN apt-get update && apt-get install -y git build-essential

# Install vLLM from source (optimized for ROCm)
RUN pip uninstall -y torch torchvision
RUN pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/rocm6.1
RUN pip install vllm==0.4.2 --no-build-isolation

# Environment for AMD
ENV HIP_VISIBLE_DEVICES=0
ENV HSA_OVERRIDE_GFX_VERSION=11.0.0 

ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "casperhansen/llama-3-70b-instruct-awq", "--gpu-memory-utilization", "0.85", "--port", "8000"]
```

### 2. ops/docker-compose.yml Additions
YAML

  inference-engine:
    build:
      context: .
      dockerfile: Dockerfile.vllm
    devices:
      - "/dev/kfd"
      - "/dev/dri"
    ports:
      - "11434:8000" # Maps to standard OpenAI port internally
    shm_size: '16gb'
    volumes:
      - ./models:/root/.cache/huggingface