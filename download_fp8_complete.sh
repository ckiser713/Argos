#!/bin/bash
# Complete FP8 model downloads using nohup for uninterrupted background execution

set -e

echo "=== FP8 Model Download (Uninterrupted) ==="
echo "Starting downloads that will run in background..."
echo "Monitor progress with: tail -f download_fp8.log"
echo ""

# Create download script
cat > download_fp8_process.sh << 'EOF'
#!/bin/bash
echo "$(date): Starting FP8 model downloads..."

# Download ORCHESTRATOR FP8
echo "$(date): Downloading ORCHESTRATOR FP8..."
hf download neuralmagic/DeepSeek-R1-Distill-Qwen-32B-FP8-dynamic \
    --local-dir models/vllm/orchestrator/fp8

# Verify ORCHESTRATOR
if ls models/vllm/orchestrator/fp8/*.safetensors 2>/dev/null; then
    size=$(du -sh models/vllm/orchestrator/fp8 | cut -f1)
    echo "$(date): ✅ ORCHESTRATOR FP8 downloaded ($size)"
else
    echo "$(date): ❌ ORCHESTRATOR FP8 download failed"
    exit 1
fi

# Download CODER FP8
echo "$(date): Downloading CODER FP8..."
hf download BCCard/Qwen2.5-Coder-32B-Instruct-FP8-Dynamic \
    --local-dir models/vllm/coder/fp8

# Verify CODER
if ls models/vllm/coder/fp8/*.safetensors 2>/dev/null; then
    size=$(du -sh models/vllm/coder/fp8 | cut -f1)
    echo "$(date): ✅ CODER FP8 downloaded ($size)"
else
    echo "$(date): ❌ CODER FP8 download failed"
    exit 1
fi

echo "$(date): 🎉 All FP8 models downloaded successfully!"
echo "$(date): Total FP8 model sizes:"
du -sh models/vllm/orchestrator/fp8 models/vllm/coder/fp8 models/vllm/fast_rag/bf16
EOF

chmod +x download_fp8_process.sh

# Run in background with nohup
echo "Starting background download process..."
nohup ./download_fp8_process.sh > download_fp8.log 2>&1 &
echo "Download PID: $!"

echo ""
echo "📋 Monitoring commands:"
echo "  tail -f download_fp8.log          # View progress"
echo "  ps aux | grep download_fp8        # Check if running"
echo "  kill PID_HERE                     # Stop download if needed"
echo ""
echo "Downloads will take 30-60 minutes. Check download_fp8.log for completion."