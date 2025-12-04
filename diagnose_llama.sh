#!/bin/bash
# Simple llama-server diagnostic script

echo "=== Quick Llama Server Diagnostic ==="
echo ""

PROJECT_ROOT="/home/nexus/Argos_Chatgpt"
LLAMA_BIN="$HOME/rocm/py311-tor290/bin/llama-server"
MODEL_PATH="$PROJECT_ROOT/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# 1. Check binary
print_header "Binary Check"
if [ ! -f "$LLAMA_BIN" ]; then
    print_error "Binary not found: $LLAMA_BIN"
    exit 1
fi
print_success "Binary exists"

if [ ! -x "$LLAMA_BIN" ]; then
    print_error "Binary not executable"
    exit 1
fi
print_success "Binary is executable"

# 2. Check model
print_header "Model Check"
if [ ! -f "$MODEL_PATH" ]; then
    print_error "Model not found: $MODEL_PATH"
    exit 1
fi
print_success "Model exists"

# 3. Test basic commands
print_header "Basic Tests"

print_info "Testing --help..."
if timeout 3s "$LLAMA_BIN" --help >/dev/null 2>&1; then
    print_success "Help command works"
else
    print_error "Help command failed"
fi

# 4. Test CPU startup
print_header "CPU Startup Test"

export LD_LIBRARY_PATH="$HOME/rocm/py311-tor290/bin:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
export HIP_VISIBLE_DEVICES="0"

print_info "Testing CPU-only startup (5 second timeout)..."
timeout 5s "$LLAMA_BIN" \
    --model "$MODEL_PATH" \
    --host 127.0.0.1 \
    --port 9999 \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --threads 2 \
    --parallel 1 \
    --log-disable \
    >/dev/null 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ]; then
    print_success "CPU mode works! Server started successfully"
elif [ $EXIT_CODE -eq 0 ]; then
    print_warning "Server exited immediately (may be normal)"
else
    print_error "CPU mode failed with exit code $EXIT_CODE"
fi

# 5. Summary
print_header "Summary"
if [ $EXIT_CODE -eq 124 ]; then
    echo "🎉 SUCCESS: Llama-server is working!"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./scripts/start_llama_servers.sh start"
    echo "2. Check: ./scripts/start_llama_servers.sh --status"
    echo "3. Test: curl http://localhost:8080/health"
else
    echo "❌ FAILURE: Llama-server has issues"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check ROCm: /opt/rocm"
    echo "2. Try CPU-only: Set GPU_LAYERS=0 in start_llama_servers.sh"
    echo "3. Check logs: tail -20 logs/super_reader.log"
fi