#!/bin/bash
# Simple test to run llama-server manually

cd /home/nexus/Argos_Chatgpt

echo "Testing llama-server manually with CPU only..."

# Set environment
export LD_LIBRARY_PATH="/home/nexus/rocm/py311-tor290/bin:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

# Run for 10 seconds to see if it starts
timeout 10s /home/nexus/rocm/py311-tor290/bin/llama-server \
    --model models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    --ctx-size 4096 \
    --n-gpu-layers 0 \
    --threads 4 \
    --parallel 1 \
    --log-disable

echo "Exit code: $?"