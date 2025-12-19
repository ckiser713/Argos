#!/usr/bin/env python3
"""Download FP8 quantized models for memory-efficient deployment."""
from pathlib import Path
from huggingface_hub import snapshot_download
import os

models_dir = Path("models")
print("=== Downloading FP8 Models for Memory Efficiency ===\n")

# 1. Download DeepSeek-R1 FP8 for ORCHESTRATOR
print("1. ORCHESTRATOR FP8 Model (DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic)...")
orchestrator_dir = models_dir / "vllm" / "orchestrator" / "fp8"
orchestrator_dir.mkdir(parents=True, exist_ok=True)

# Check if already downloaded (look for safetensors files)
safetensors_files = list(orchestrator_dir.glob("*.safetensors"))
if safetensors_files:
    size_gb = sum(f.stat().st_size for f in safetensors_files) / (1024**3)
    print(f"   ✅ Already downloaded ({size_gb:.1f} GB)")
else:
    try:
        print("   Downloading... (this may take 10-20 minutes)")
        snapshot_download(
            repo_id="neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic",
            local_dir=str(orchestrator_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
            max_workers=4
        )
        size_gb = sum(f.stat().st_size for f in orchestrator_dir.rglob('*') if f.is_file()) / (1024**3)
        print(f"   ✅ Downloaded ({size_gb:.1f} GB)")
    except Exception as e:
        print(f"   ⚠️ Error: {str(e)[:100]}")

# 2. Download Qwen Coder FP8
print("\n2. CODER FP8 Model (Qwen2.5-Coder-32B-Instruct-FP8-Dynamic)...")
coder_dir = models_dir / "vllm" / "coder" / "fp8"
coder_dir.mkdir(parents=True, exist_ok=True)

# Check if already downloaded (look for safetensors files)
safetensors_files = list(coder_dir.glob("*.safetensors"))
if safetensors_files:
    size_gb = sum(f.stat().st_size for f in safetensors_files) / (1024**3)
    print(f"   ✅ Already downloaded ({size_gb:.1f} GB)")
else:
    try:
        print("   Downloading... (this may take 10-20 minutes)")
        snapshot_download(
            repo_id="BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic",
            local_dir=str(coder_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
            max_workers=4
        )
        size_gb = sum(f.stat().st_size for f in coder_dir.rglob('*') if f.is_file()) / (1024**3)
        print(f"   ✅ Downloaded ({size_gb:.1f} GB)")
    except Exception as e:
        print(f"   ⚠️ Error: {str(e)[:100]}")

print("\n=== Download Summary ===")
print("These FP8 models are ~25% the size of BF16 versions.")
print("With 96GB VRAM, you'll have:")
print("- ORCHESTRATOR: ~16GB")
print("- CODER: ~16GB")
print("- FAST_RAG: ~40GB")
print("- Total: ~72GB (comfortably under 96GB limit)")
print("\nRun this script again to resume interrupted downloads.")