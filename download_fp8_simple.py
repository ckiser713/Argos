#!/usr/bin/env python3
"""Simple FP8 model downloader with progress reporting."""
import os
from pathlib import Path
from huggingface_hub import snapshot_download, HfApi
import time

models_dir = Path("models")
print("=== Simple FP8 Model Downloader ===")

# Check available models
api = HfApi()
print("\nChecking model availability...")

models_to_download = [
    ("neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic", "orchestrator"),
    ("BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic", "coder")
]

for repo_id, lane in models_to_download:
    try:
        info = api.model_info(repo_id)
        print(f"✅ {lane}: {repo_id} - {info.safetensors.total_size / (1024**3):.1f}GB" if hasattr(info, 'safetensors') and info.safetensors else f"✅ {lane}: {repo_id}")
    except Exception as e:
        print(f"❌ {lane}: {repo_id} - {str(e)[:50]}")

print("\nStarting downloads...\n")

for repo_id, lane in models_to_download:
    target_dir = models_dir / "vllm" / lane / "fp8"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    safetensors_files = list(target_dir.glob("*.safetensors"))
    if safetensors_files:
        size_gb = sum(f.stat().st_size for f in safetensors_files) / (1024**3)
        print(f"✅ {lane.upper()} already downloaded ({size_gb:.1f}GB)")
        continue

    print(f"Downloading {lane.upper()} FP8: {repo_id}")
    start_time = time.time()

    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
            max_workers=4
        )

        # Verify download
        safetensors_files = list(target_dir.glob("*.safetensors"))
        if safetensors_files:
            size_gb = sum(f.stat().st_size for f in safetensors_files) / (1024**3)
            elapsed = time.time() - start_time
            print(f"✅ {lane.upper()} downloaded successfully ({size_gb:.1f}GB in {elapsed:.1f}s)")
        else:
            print(f"❌ {lane.upper()} download failed - no model files found")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ {lane.upper()} download failed after {elapsed:.1f}s: {str(e)[:100]}")
print("\n=== Download Summary ===")
print("FP8 models provide ~75% memory savings vs BF16")

# Show final sizes
for repo_id, lane in models_to_download:
    target_dir = models_dir / "vllm" / lane / "fp8"
    if target_dir.exists():
        safetensors_files = list(target_dir.glob("*.safetensors"))
        if safetensors_files:
            size_gb = sum(f.stat().st_size for f in safetensors_files) / (1024**3)
            print(f"  {lane.upper()}: {size_gb:.1f}GB")
print("\nWith FAST_RAG BF16 (40GB), total VRAM usage: ~72GB")