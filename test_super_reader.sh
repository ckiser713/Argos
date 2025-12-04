#!/bin/bash
# Test starting just the super_reader server

cd /home/nexus/Argos_Chatgpt

echo "Testing super_reader startup..."
./scripts/start_llama_servers.sh stop

# Clean up any stale files
rm -f .pids/super_reader.pid .pids/governance.pid

echo "Starting super_reader only..."
./scripts/start_llama_servers.sh start 2>&1 | head -20

echo ""
echo "Checking status..."
./scripts/start_llama_servers.sh status

echo ""
echo "Checking log file..."
if [ -f logs/super_reader.log ]; then
    echo "Log file contents:"
    cat logs/super_reader.log | head -10
else
    echo "No log file found"
fi