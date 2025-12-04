#!/bin/bash
# Download FAST_RAG model in background
cd /home/nexus/Argos_Chatgpt

echo "Starting FAST_RAG model download..."
echo "This will download ~22GB. Monitor progress with:"
echo "  tail -f /tmp/fast_rag_download.log"
echo "  watch -n 10 'du -sh models/vllm/fast_rag/bf16'"
echo ""

nohup python3 << 'PYEOF' > /tmp/fast_rag_download.log 2>&1 &
import os
from huggingface_hub import snapshot_download
from pathlib import Path

fast_rag_dir = Path("models/vllm/fast_rag/bf16")
fast_rag_dir.mkdir(parents=True, exist_ok=True)

token = os.getenv("HF_TOKEN")
if not token:
    print("ERROR: HF_TOKEN not set")
    exit(1)

print("Downloading FAST_RAG model (Llama-3.2-11B-Vision-Instruct)...")
print("Expected size: ~22GB")
print("This may take 30-60 minutes depending on connection speed\n")

try:
    snapshot_download(
        repo_id="meta-llama/Llama-3.2-11B-Vision-Instruct",
        local_dir=str(fast_rag_dir),
        token=token
    )
    size_gb = sum(f.stat().st_size for f in fast_rag_dir.rglob('*') if f.is_file()) / (1024**3)
    print(f"\n✅ Download complete! Size: {size_gb:.1f} GB")
except Exception as e:
    print(f"\n❌ Error: {e}")
PYEOF

echo "Download started in background (PID: $!)"
echo "Check progress: tail -f /tmp/fast_rag_download.log"

