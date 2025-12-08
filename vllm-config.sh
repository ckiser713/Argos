# vLLM Nix Deployment Configuration
# 
# This file contains all configuration for the vLLM Nix environment
# Edit these values to customize your deployment
# 
# Source this file before deploying:
#   source vllm-config.sh
#   ./deploy-vllm.sh <mode>

# ============================================================================
# ARTIFACTS CONFIGURATION
# ============================================================================

# Central artifacts directory for all pre-built components
# Contains: vLLM wheels, PyTorch wheels, llama.cpp archive, etc.
export ARTIFACTS_DIR="/home/nexus/amd-ai/artifacts"

# Verify artifacts exist (run with: check_artifacts_dir)
VLLM_WHEEL_PATH="${ARTIFACTS_DIR}/vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl"
TORCH_WHEEL_PATH="${ARTIFACTS_DIR}/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl"
LLAMA_CPP_ARCHIVE="${ARTIFACTS_DIR}/llama_cpp_rocm.tar.gz"

# ============================================================================
# vLLM SERVER CONFIGURATION
# ============================================================================

# Model path - REQUIRED for deployment
# Examples:
#   /models/orchestrator/bf16        (Large orchestrator model)
#   /models/coder/bf16               (Code generation model)
#   /models/fast-rag/bf16            (RAG model)
export MODEL_PATH="/models/orchestrator/bf16"

# GPU memory utilization (0.0 to 1.0)
# - 0.48: Conservative, safe for most setups
# - 0.60: Moderate, recommended for dedicated inference servers
# - 0.80: Aggressive, maximum throughput (test first)
export GPU_MEM_UTIL="0.48"

# Maximum model length (tokens)
# Impacts memory usage and context window
# - 32768: Default for most models
# - 131072: Extended context (if model supports and memory available)
export MAX_MODEL_LEN="32768"

# Data type for inference
# - bfloat16: Default, good precision/performance balance
# - float16: Lower precision, slightly faster
# - float32: Higher precision, uses more VRAM
export DTYPE="bfloat16"

# Listen address and port
export VLLM_HOST="0.0.0.0"
export VLLM_PORT="8000"

# Parallel processing settings
# - TENSOR_PARALLEL_SIZE: Split model across GPUs (1 = single GPU)
# - PIPELINE_PARALLEL_SIZE: Pipeline parallelism (1 = disabled)
# - SWAP_SPACE: CPU swap space for offloading (GB)
export TENSOR_PARALLEL_SIZE="1"
export PIPELINE_PARALLEL_SIZE="1"
export SWAP_SPACE="8"

# ============================================================================
# ROCm GPU CONFIGURATION
# ============================================================================

# GPU device selection
# 0 = GPU 0, can be 0,1 for multiple GPUs
export HIP_VISIBLE_DEVICES="0"

# GPU architecture override
# 11.0.0 = gfx1151 (AMD Radeon)
# See: https://rocmdocs.amd.com/en/latest/deploy/linux/index.html
export HSA_OVERRIDE_GFX_VERSION="11.0.0"

# ROCm GPU optimization settings
export HSA_ENABLE_SDMA="1"           # Enable SDMA for data transfer
export HSA_ENABLE_INTERRUPT="1"      # Enable GPU interrupts
export VLLM_ROCM_USE_AITER="1"       # Use AMD iterative methods
export VLLM_ROCM_USE_SKINNY_GEMM="1" # Optimize for skinny GEMM operations
export VLLM_ROCM_GEMM_TUNING="fast"  # Fast GEMM tuning (vs "default")

# Target device (should be 'rocm' for AMD GPU)
export VLLM_TARGET_DEVICE="rocm"

# ============================================================================
# PYTHON CONFIGURATION
# ============================================================================

# Python output buffering
export PYTHONUNBUFFERED="1"

# Don't write .pyc files
export PYTHONDONTWRITEBYTECODE="1"

# Hugging Face model cache
export HF_HOME="$HOME/.cache/huggingface"

# ============================================================================
# DEPLOYMENT-SPECIFIC SETTINGS
# ============================================================================

# For Shell Deployment
SHELL_DEPLOYMENT_MODE="interactive"  # interactive or batch

# For Systemd Deployment
SYSTEMD_USER="nexus"
SYSTEMD_GROUP="nexus"
SYSTEMD_MEMORY_LIMIT="64G"
SYSTEMD_CPU_QUOTA="80%"
SYSTEMD_RESTART="always"
SYSTEMD_RESTART_SEC="10s"

# For Container Deployment
CONTAINER_NAME="vllm-rocm-nix"
CONTAINER_TAG="latest"
CONTAINER_REGISTRY=""  # Optional: registry.example.com/

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log level for vLLM
# DEBUG, INFO, WARNING, ERROR
export LOG_LEVEL="INFO"

# Disable request logging (for high-throughput scenarios)
# Remove this line to enable detailed request logging
export VLLM_DISABLE_LOG_REQUESTS="true"

# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

# Additional vLLM arguments (if needed)
# Example: "--enable-lora --lora-modules module1=/path/to/module1"
export EXTRA_VLLM_ARGS=""

# CUDA compute capability (not used with ROCm, kept for compatibility)
# export CUDA_VISIBLE_DEVICES="-1"  # Disable CUDA

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

check_artifacts_dir() {
  echo "Checking artifacts directory: $ARTIFACTS_DIR"
  
  if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "ERROR: Artifacts directory not found: $ARTIFACTS_DIR"
    return 1
  fi
  
  echo "✓ Artifacts directory exists"
  
  if [ -f "$VLLM_WHEEL_PATH" ]; then
    echo "✓ vLLM wheel found"
  else
    echo "⚠ vLLM wheel not found at: $VLLM_WHEEL_PATH"
  fi
  
  if [ -f "$TORCH_WHEEL_PATH" ]; then
    echo "✓ PyTorch wheel found"
  else
    echo "⚠ PyTorch wheel not found at: $TORCH_WHEEL_PATH"
  fi
  
  if [ -f "$LLAMA_CPP_ARCHIVE" ]; then
    echo "✓ llama.cpp archive found"
  else
    echo "⚠ llama.cpp archive not found at: $LLAMA_CPP_ARCHIVE"
  fi
  
  return 0
}

verify_model_path() {
  if [ -z "$MODEL_PATH" ]; then
    echo "ERROR: MODEL_PATH not set"
    return 1
  fi
  
  if [ ! -d "$MODEL_PATH" ]; then
    echo "ERROR: Model path does not exist: $MODEL_PATH"
    return 1
  fi
  
  echo "✓ Model path verified: $MODEL_PATH"
  return 0
}

show_config() {
  echo "╔═══════════════════════════════════════════════════════════════════════════╗"
  echo "║                 vLLM Configuration Summary                               ║"
  echo "╠═══════════════════════════════════════════════════════════════════════════╣"
  echo "║ Artifacts:"
  echo "║   Directory:        $ARTIFACTS_DIR"
  echo "║   vLLM wheel:       $([ -f "$VLLM_WHEEL_PATH" ] && echo "✓" || echo "✗")"
  echo "║   PyTorch wheel:    $([ -f "$TORCH_WHEEL_PATH" ] && echo "✓" || echo "✗")"
  echo "║   llama.cpp:        $([ -f "$LLAMA_CPP_ARCHIVE" ] && echo "✓" || echo "✗")"
  echo "║"
  echo "║ vLLM Server:"
  echo "║   Model Path:       $MODEL_PATH"
  echo "║   Host:             $VLLM_HOST:$VLLM_PORT"
  echo "║   GPU Memory:       $GPU_MEM_UTIL"
  echo "║   Max Model Len:    $MAX_MODEL_LEN tokens"
  echo "║   Data Type:        $DTYPE"
  echo "║"
  echo "║ GPU Configuration:"
  echo "║   Target Device:    $VLLM_TARGET_DEVICE"
  echo "║   GPU Device:       $HIP_VISIBLE_DEVICES"
  echo "║   GPU Arch:         $HSA_OVERRIDE_GFX_VERSION"
  echo "║   Tensor Parallel:  $TENSOR_PARALLEL_SIZE"
  echo "║   Pipeline Parallel:$PIPELINE_PARALLEL_SIZE"
  echo "║"
  echo "║ Systemd (if deployed):"
  echo "║   User:             $SYSTEMD_USER"
  echo "║   Memory Limit:     $SYSTEMD_MEMORY_LIMIT"
  echo "║   CPU Quota:        $SYSTEMD_CPU_QUOTA"
  echo "╚═══════════════════════════════════════════════════════════════════════════╝"
}
