#!/bin/bash
# Script to launch host-level services for Strix Halo Hybrid Deployment

echo "🚀 Starting Super-Reader Lane on host..."

# Define the command and log file
# The user's home directory is expanded using the ~ character.
CMD="~/rocm/py311-tor290/bin/llama-cpp-tuned --server --model models/gguf/nemotron-8b-instruct.Q4_K_M.gguf --port 8080 --ctx-size 131072 --n-gpu-layers 99 --threads 8"
LOG_FILE="logs/host_super_reader.log"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Command: $CMD"
echo "Logging to: $LOG_FILE"

# Execute the command in the background
# Nohup ensures the process continues running even if the terminal is closed.
# Output (stdout and stderr) is redirected to the log file.
nohup $CMD > "$LOG_FILE" 2>&1 &

# Get the Process ID (PID) of the background job
PID=$!

echo "✓ Super-Reader service started in the background with PID: $PID"
echo "To monitor its status, run: tail -f $LOG_FILE"
echo "To stop the service, run: kill $PID"
