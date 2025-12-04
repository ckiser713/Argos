#!/bin/bash
# =============================================================================
# Cortex llama.cpp Server Launcher
# =============================================================================
# Starts native llama-server instances for SUPER_READER and GOVERNANCE lanes
# Uses locally-built ROCm binaries optimized for gfx1151 (Strix Point)
#
# Usage:
#   ./scripts/start_llama_servers.sh         # Start both servers
#   ./scripts/start_llama_servers.sh --stop  # Stop all servers
#   ./scripts/start_llama_servers.sh --status # Check status
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LLAMA_BIN_DIR="$HOME/rocm/py311-tor290/bin"
MODELS_DIR="$PROJECT_ROOT/models/gguf"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/.pids"

# Model configurations - REDUCED for minimal resource usage
# Using Llama 3.1 8B instead of Nemotron (which has ring buffer issues)
SUPER_READER_MODEL="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
SUPER_READER_PORT=8080
SUPER_READER_CTX=4096   # Reduced to avoid memory issues
SUPER_READER_THREADS=1  # Single thread to minimize resources

GOVERNANCE_MODEL="granite-3.0-8b-instruct-Q4_K_M.gguf"
GOVERNANCE_PORT=8081
GOVERNANCE_CTX=2048    # Reduced to avoid memory issues
GOVERNANCE_THREADS=1   # Single thread to minimize resources

# GPU settings - Using GPU with recompiled ROCm binaries
# Binaries are tuned for gfx1151, HSA override removed for native detection
# TEMPORARILY SET TO CPU-ONLY FOR TESTING
GPU_LAYERS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

mkdir -p "$LOG_DIR" "$PID_DIR"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_binary() {
    if [ ! -x "$LLAMA_BIN_DIR/llama-server" ]; then
        log_error "llama-server binary not found at $LLAMA_BIN_DIR/llama-server"
        log_error "Please build llama.cpp with ROCm support for gfx1151"
        exit 1
    fi
    log_info "✓ Binary found: $LLAMA_BIN_DIR/llama-server"
}

check_models() {
    if [ ! -f "$MODELS_DIR/$SUPER_READER_MODEL" ]; then
        log_error "SUPER_READER model not found: $MODELS_DIR/$SUPER_READER_MODEL"
        exit 1
    fi
    if [ ! -f "$MODELS_DIR/$GOVERNANCE_MODEL" ]; then
        log_error "GOVERNANCE model not found: $MODELS_DIR/$GOVERNANCE_MODEL"
        exit 1
    fi
}

start_server() {
    local name=$1
    local model=$2
    local port=$3
    local ctx=$4
    local threads=$5
    local pid_file="$PID_DIR/${name}.pid"
    local log_file="$LOG_DIR/${name}.log"

    # Check if already running
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "$name already running (PID: $(cat "$pid_file"))"
        return 0
    fi

    log_info "Starting $name on port $port..."
    log_info "Model: $MODELS_DIR/$model"
    log_info "Binary: $LLAMA_BIN_DIR/llama-server"
    log_info "GPU Layers: $GPU_LAYERS"

    # Set comprehensive environment for ROCm - DISABLE GPU COMPLETELY
    export LD_LIBRARY_PATH="$LLAMA_BIN_DIR:/opt/rocm/lib:/opt/rocm/lib64:$LD_LIBRARY_PATH"
    export HIP_VISIBLE_DEVICES=""  # Empty string disables GPU
    export HSA_ENABLE_SDMA="0"
    export ROCR_VISIBLE_DEVICES=""  # Empty string disables GPU

    # Additional ROCm environment variables for stability
    export HIP_FORCE_DEV_KERNARG="1"
    export AMD_LOG_LEVEL="0"

    log_info "Environment:"
    log_info "  LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
    log_info "  HIP_VISIBLE_DEVICES=$HIP_VISIBLE_DEVICES"
    log_info "  HSA_ENABLE_SDMA=$HSA_ENABLE_SDMA"

    # Test binary before starting (simplified to avoid hangs)
    log_info "Testing binary execution..."
    if ! timeout 2s "$LLAMA_BIN_DIR/llama-server" --help >/dev/null 2>&1; then
        log_error "Binary test failed - cannot run --help command"
        return 1
    fi
    log_info "✓ Binary test passed"

    # Start server in background with enhanced error handling
    log_info "Starting process in background..."
    nohup "$LLAMA_BIN_DIR/llama-server" \
        --model "$MODELS_DIR/$model" \
        --host 0.0.0.0 \
        --port "$port" \
        --ctx-size "$ctx" \
        --n-gpu-layers "$GPU_LAYERS" \
        --threads "$threads" \
        --parallel 2 \
        --timeout 300 \
        --log-format json \
        > "$log_file" 2>&1 &

    local pid=$!
    echo "$pid" > "$pid_file"
    log_info "Process started with PID: $pid"

    # Check if process is actually running immediately
    sleep 1
    if ! kill -0 "$pid" 2>/dev/null; then
        log_error "Process failed to start immediately - PID $pid not found"
        log_error "Check logs: $log_file"
        # Show last few lines of log
        if [ -f "$log_file" ]; then
            log_error "Last log entries:"
            tail -10 "$log_file" 2>/dev/null || true
        fi
        rm -f "$pid_file"
        return 1
    fi

    # Wait for startup with better health check
    local retries=15  # Reduced from 60 to 15 (30 seconds total)
    log_info "Waiting for server to become healthy..."
    while [ $retries -gt 0 ]; do
        # Check if process is still running
        if ! kill -0 "$pid" 2>/dev/null; then
            log_error "Process died during startup"
            log_error "Check logs: $log_file"
            tail -10 "$log_file" 2>/dev/null || true
            rm -f "$pid_file"
            return 1
        fi

        # Try health check - check if server is listening on port
        if nc -z localhost "$port" 2>/dev/null; then
            log_info "✓ $name started successfully (PID: $pid)"
            return 0
        fi

        sleep 2
        retries=$((retries - 1))
        log_info "Waiting... ($retries retries left)"
    done

    log_error "$name failed to start within timeout. Check logs: $log_file"
    # Show full log for debugging
    if [ -f "$log_file" ]; then
        log_error "Full log contents:"
        cat "$log_file" 2>/dev/null || true
    fi
    return 1
}

stop_server() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    fi
}

status() {
    echo "=== Cortex llama.cpp Server Status ==="
    echo ""
    
    for name in super_reader governance; do
        local pid_file="$PID_DIR/${name}.pid"
        local port=$([[ "$name" == "super_reader" ]] && echo $SUPER_READER_PORT || echo $GOVERNANCE_PORT)
        
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            # Check if server is listening on port
            if nc -z localhost "$port" 2>/dev/null; then
                echo -e "$name: ${GREEN}RUNNING${NC} (PID: $(cat "$pid_file"), Port: $port)"
            else
                echo -e "$name: ${YELLOW}STARTING${NC} (PID: $(cat "$pid_file"), Port: $port)"
            fi
        else
            echo -e "$name: ${RED}STOPPED${NC}"
        fi
    done
    echo ""
}

case "${1:-start}" in
    start)
        check_binary
        check_models
        log_info "Starting Cortex llama.cpp servers..."
        start_server "super_reader" "$SUPER_READER_MODEL" "$SUPER_READER_PORT" "$SUPER_READER_CTX" "$SUPER_READER_THREADS"
        start_server "governance" "$GOVERNANCE_MODEL" "$GOVERNANCE_PORT" "$GOVERNANCE_CTX" "$GOVERNANCE_THREADS"
        echo ""
        status
        ;;
    stop|--stop)
        log_info "Stopping Cortex llama.cpp servers..."
        stop_server "super_reader"
        stop_server "governance"
        # Also kill any stray processes
        pkill -f "llama-server.*$SUPER_READER_MODEL" 2>/dev/null || true
        pkill -f "llama-server.*$GOVERNANCE_MODEL" 2>/dev/null || true
        log_info "All servers stopped"
        ;;
    restart)
        $0 --stop
        sleep 2
        $0 start
        ;;
    status|--status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
