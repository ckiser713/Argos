#!/bin/bash
echo "$(date): Starting FP8 model downloads..."

# Download ORCHESTRATOR FP8
echo "$(date): Downloading ORCHESTRATOR FP8..."
hf download neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic \
    --local-dir models/vllm/orchestrator/fp8

# Verify ORCHESTRATOR
if ls models/vllm/orchestrator/fp8/*.safetensors 2>/dev/null; then
    size=$(du -sh models/vllm/orchestrator/fp8 | cut -f1)
    echo "$(date): ✅ ORCHESTRATOR FP8 downloaded ($size)"
else
    echo "$(date): ❌ ORCHESTRATOR FP8 download failed"
    exit 1
fi

# Download CODER FP8
echo "$(date): Downloading CODER FP8..."
hf download BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic \
    --local-dir models/vllm/coder/fp8

# Verify CODER
if ls models/vllm/coder/fp8/*.safetensors 2>/dev/null; then
    size=$(du -sh models/vllm/coder/fp8 | cut -f1)
    echo "$(date): ✅ CODER FP8 downloaded ($size)"
else
    echo "$(date): ❌ CODER FP8 download failed"
    exit 1
fi

echo "$(date): 🎉 All FP8 models downloaded successfully!"
echo "$(date): Total FP8 model sizes:"
du -sh models/vllm/orchestrator/fp8 models/vllm/coder/fp8 models/vllm/fast_rag/bf16
