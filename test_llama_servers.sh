#!/bin/bash
# Test script to start llama.cpp servers manually

export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

echo "Starting super_reader server..."
nohup $HOME/rocm/py311-tor290/bin/llama-server \
  --model models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 32768 \
  --n-gpu-layers 99 \
  --threads 16 \
  --parallel 2 \
  --log-disable > logs/super_reader_test.log 2>&1 &

echo "Starting governance server..."
nohup $HOME/rocm/py311-tor290/bin/llama-server \
  --model models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8081 \
  --ctx-size 16384 \
  --n-gpu-layers 99 \
  --threads 8 \
  --parallel 2 \
  --log-disable > logs/governance_test.log 2>&1 &

echo "Servers started. Check logs for status."