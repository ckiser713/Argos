#!/usr/bin/env python3
"""Start VLLM server with FP8 model using ROCm artifacts."""
import os
import sys
import subprocess

# Add artifacts to Python path
artifacts_path = "/home/nexus/amd-ai/artifacts"
if artifacts_path not in sys.path:
    sys.path.insert(0, artifacts_path)

# Set environment variables for ROCm
os.environ["PIP_FIND_LINKS"] = f"{artifacts_path}/vllm_docker_rocm"
os.environ["PATH"] = f"{artifacts_path}/bin:{os.environ.get('PATH', '')}"

def start_vllm_server():
    """Start VLLM server with FP8 model."""
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", "/home/nexus/Argos_Chatgpt/models/vllm/orchestrator/fp8",
        "--host", "0.0.0.0",
        "--port", "8001",
        "--tensor-parallel-size", "1",
        "--gpu-memory-utilization", "0.4",
        "--max-model-len", "32768"
    ]

    print("Starting VLLM server with command:", " ".join(cmd))
    subprocess.run(cmd)

if __name__ == "__main__":
    start_vllm_server()