#!/bin/bash
cd /home/nexus/Argos_Chatgpt
echo "Checking server status..."
./scripts/start_llama_servers.sh status

echo ""
echo "Checking log file..."
if [ -f logs/super_reader.log ]; then
    echo "Log file contents (last 20 lines):"
    tail -20 logs/super_reader.log
else
    echo "No log file found at logs/super_reader.log"
    ls -la logs/
fi