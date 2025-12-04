#!/usr/bin/env python3
"""Download remaining models for Cortex"""
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
from pathlib import Path
import os

models_dir = Path("models")
print("=== Downloading Remaining Models ===\n")

# 1. Download FAST_RAG model
print("1. FAST_RAG Model (Llama 3.2 Vision)...")
fast_rag_dir = models_dir / "vllm" / "fast_rag" / "bf16"
fast_rag_dir.mkdir(parents=True, exist_ok=True)

existing_size = sum(f.stat().st_size for f in fast_rag_dir.rglob('*') if f.is_file())
if existing_size > 1024 * 1024:  # > 1MB
    print(f"   ✅ Already downloaded ({existing_size / (1024**3):.1f} GB)\n")
else:
    try:
        print("   Downloading... (this may take a while)")
        snapshot_download(
            repo_id="meta-llama/Llama-3.2-11B-Vision-Instruct",
            local_dir=str(fast_rag_dir),
            local_dir_use_symlinks=False,
            token=os.getenv("HF_TOKEN")
        )
        size_gb = sum(f.stat().st_size for f in fast_rag_dir.rglob('*') if f.is_file()) / (1024**3)
        print(f"   ✅ Downloaded ({size_gb:.1f} GB)\n")
    except Exception as e:
        print(f"   ⚠️ Error: {str(e)[:100]}\n")

# 2. Download embedding models
print("2. Embedding Models...")
for model_name in [
    "sentence-transformers/all-MiniLM-L6-v2",
    "jinaai/jina-embeddings-v2-base-code",
    "microsoft/codebert-base",
]:
    try:
        print(f"   Loading {model_name.split('/')[-1]}...")
        SentenceTransformer(model_name)
        print(f"   ✅ Cached\n")
    except Exception as e:
        print(f"   ⚠️ {str(e)[:80]}\n")

print("=== Complete ===")

