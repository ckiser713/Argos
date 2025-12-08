# vLLM Package and Service Definition for Nix

{ pkgs ? import <nixpkgs> {}, lib ? pkgs.lib, rocmPackages ? pkgs.rocmPackages }:

let
  python = pkgs.python311;
  
  # Artifacts Directory Configuration
  # Central location for all pre-built artifacts including vLLM, PyTorch, and llama.cpp
  artifactsDir = "/home/nexus/amd-ai/artifacts";
  
  # vLLM Wheels - ROCm 7.1.1 optimized, Python 3.11 compatible
  # Primary location: artifacts/vllm_docker_rocm/
  vllmWheelPath = "${artifactsDir}/vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl";
  
  # Alternative location: artifacts/ (root level)
  vllmWheelAlt = "${artifactsDir}/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl";
  
  # PyTorch Wheel - ROCm enabled
  torchWheelPath = "${artifactsDir}/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl";
  
  # llama.cpp Archive - for future LlamaCpp integration
  llamaCppArchive = "${artifactsDir}/llama_cpp_rocm.tar.gz";

in

rec {
  # ============================================================================
  # vLLM Python Environment
  # ============================================================================
  
  pythonWithVllm = python.withPackages (ps: with ps; [
    pip
    setuptools
    wheel
    
    # FastAPI server for OpenAI-compatible API
    fastapi
    uvicorn
    pydantic
    pydantic-core
    
    # Core utilities
    numpy
    scipy
    
    # Async/HTTP support
    aiohttp
    httpx
    httpcore
    h11
    anyio
    sniffio
    certifi
    idna
    
    # Utilities
    python-dotenv
    requests
    click
    tqdm
    
    # Transformers for tokenization (if not in wheel)
    transformers
    huggingface-hub
    safetensors
  ]);

  # ============================================================================
  # vLLM Runtime Shell (for development)
  # ============================================================================
  
  vllmRuntimeShell = pkgs.mkShell {
    name = "vllm-runtime";
    description = "vLLM runtime environment with ROCm support";
    
    buildInputs = with pkgs; [
      # Python with vLLM
      pythonWithVllm
      
      # ROCm stack (GPU compute)
      rocmPackages.rocm-core
      rocmPackages.rocm-runtime
      rocmPackages.hip
      rocmPackages.hipcc
      rocmPackages.rocblas
      rocmPackages.rocrand
      rocmPackages.rocsparse
      rocmPackages.rocm-smi
      rocmPackages.rocm-device-libs
      
      # System libraries
      curl
      git
      wget
      ca-certificates
      libffi
      openssl
      
      # Development utilities
      vim
      htop
      tmux
      jq
      
      # Profiling/debugging
      gdb
      linuxPackages.perf
    ];
    
    shellHook = ''
      # Python settings
      export PYTHONUNBUFFERED=1
      export PYTHONDONTWRITEBYTECODE=1
      
      # ROCm Configuration
      export ROCM_HOME=${rocmPackages.rocm-core}
      export LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:${rocmPackages.rocblas}/lib64:${rocmPackages.rocsparse}/lib:${rocmPackages.rocrand}/lib:${rocmPackages.hip}/lib:$LD_LIBRARY_PATH
      export PATH=${rocmPackages.rocm-smi}/bin:${rocmPackages.hip}/bin:$PATH
      
      # AMD GPU Detection & Configuration
      export HIP_VISIBLE_DEVICES=0
      export HSA_OVERRIDE_GFX_VERSION=11.0.0
      export HSA_ENABLE_SDMA=1
      export HSA_ENABLE_INTERRUPT=1
      
      # vLLM Configuration
      export VLLM_TARGET_DEVICE=rocm
      export VLLM_ROCM_USE_AITER=1
      export VLLM_ROCM_USE_SKINNY_GEMM=1
      export VLLM_ROCM_GEMM_TUNING=fast
      
      # API Server Defaults
      export VLLM_HOST=0.0.0.0
      export VLLM_PORT=8000
      export GPU_MEM_UTIL=0.48
      
      # Model cache
      export HF_HOME=$HOME/.cache/huggingface
      
      echo "╔════════════════════════════════════════════════════════════╗"
      echo "║         vLLM Runtime Environment (ROCm 7.1.1)              ║"
      echo "╠════════════════════════════════════════════════════════════╣"
      echo "║ ROCM_HOME: $ROCM_HOME"
      echo "║ HIP_VISIBLE_DEVICES: $HIP_VISIBLE_DEVICES"
      echo "║ VLLM_TARGET_DEVICE: $VLLM_TARGET_DEVICE"
      echo "║ GPU Memory Util: $GPU_MEM_UTIL (48%)"
      echo "╠════════════════════════════════════════════════════════════╣"
      echo "║ Start vLLM server with:"
      echo "║   vllm-server"
      echo "║ Or with custom model:"
      echo "║   MODEL_PATH=/path/to/model vllm-server"
      echo "╚════════════════════════════════════════════════════════════╝"
    '';
  };

  # ============================================================================
  # vLLM Server Executable
  # ============================================================================
  
  vllmServer = pkgs.writeShellScriptBin "vllm-server" ''
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Configuration from environment or defaults
    HOST="''${VLLM_HOST:-0.0.0.0}"
    PORT="''${VLLM_PORT:-8000}"
    MODEL_PATH="''${MODEL_PATH:-/models/orchestrator/bf16}"
    GPU_MEM_UTIL="''${GPU_MEM_UTIL:-0.48}"
    MAX_MODEL_LEN="''${MAX_MODEL_LEN:-32768}"
    TENSOR_PARALLEL="''${TENSOR_PARALLEL_SIZE:-1}"
    PIPELINE_PARALLEL="''${PIPELINE_PARALLEL_SIZE:-1}"
    SWAP_SPACE="''${SWAP_SPACE:-8}"
    DTYPE="''${DTYPE:-bfloat16}"
    
    # ROCm Configuration
    export ROCM_HOME=${rocmPackages.rocm-core}
    export LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:${rocmPackages.rocblas}/lib64:${rocmPackages.rocsparse}/lib:${rocmPackages.rocrand}/lib:${rocmPackages.hip}/lib:$LD_LIBRARY_PATH
    export PATH=${rocmPackages.rocm-smi}/bin:${rocmPackages.hip}/bin:$PATH
    
    # AMD GPU Configuration
    export HIP_VISIBLE_DEVICES=''${HIP_VISIBLE_DEVICES:-0}
    export HSA_OVERRIDE_GFX_VERSION=''${HSA_OVERRIDE_GFX_VERSION:-11.0.0}
    export HSA_ENABLE_SDMA=1
    export HSA_ENABLE_INTERRUPT=1
    
    # vLLM Configuration
    export VLLM_TARGET_DEVICE=rocm
    export VLLM_ROCM_USE_AITER=1
    export VLLM_ROCM_USE_SKINNY_GEMM=1
    export PYTHONUNBUFFERED=1
    
    # Print configuration
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              Starting vLLM OpenAI API Server               ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ Host:                    $HOST"
    echo "║ Port:                    $PORT"
    echo "║ Model Path:              $MODEL_PATH"
    echo "║ GPU Memory Utilization:  $GPU_MEM_UTIL"
    echo "║ Max Model Length:        $MAX_MODEL_LEN tokens"
    echo "║ Data Type:               $DTYPE"
    echo "║ Tensor Parallel Size:    $TENSOR_PARALLEL"
    echo "║ Pipeline Parallel Size:  $PIPELINE_PARALLEL"
    echo "║ Swap Space:              $SWAP_SPACE GB"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ ROCm Configuration:"
    echo "║   ROCM_HOME:             $ROCM_HOME"
    echo "║   HIP_VISIBLE_DEVICES:   $HIP_VISIBLE_DEVICES"
    echo "║   HSA_OVERRIDE_GFX:      $HSA_OVERRIDE_GFX_VERSION"
    echo "║   VLLM_TARGET_DEVICE:    rocm"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ API Endpoints:"
    echo "║   Chat Completions:  POST http://$HOST:$PORT/v1/chat/completions"
    echo "║   Completions:       POST http://$HOST:$PORT/v1/completions"
    echo "║   Models:            GET  http://$HOST:$PORT/v1/models"
    echo "║   Health:            GET  http://$HOST:$PORT/health"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Verify model path exists
    if [ ! -d "$MODEL_PATH" ]; then
      echo "ERROR: Model path does not exist: $MODEL_PATH"
      exit 1
    fi
    
    # Start vLLM server
    exec ${pythonWithVllm}/bin/python -m vllm.entrypoints.openai.api_server \
      --model "$MODEL_PATH" \
      --host "$HOST" \
      --port "$PORT" \
      --gpu-memory-utilization "$GPU_MEM_UTIL" \
      --dtype "$DTYPE" \
      --tensor-parallel-size "$TENSOR_PARALLEL" \
      --pipeline-parallel-size "$PIPELINE_PARALLEL" \
      --max-model-len "$MAX_MODEL_LEN" \
      --swap-space "$SWAP_SPACE" \
      --disable-log-requests \
      ''${EXTRA_VLLM_ARGS:-}
  '';

  # ============================================================================
  # Health Check Utility
  # ============================================================================
  
  vllmHealthCheck = pkgs.writeShellScriptBin "vllm-health" ''
    #!/usr/bin/env bash
    
    HOST="''${1:-localhost}"
    PORT="''${2:-8000}"
    
    echo "Checking vLLM health at http://$HOST:$PORT..."
    
    RESPONSE=$(${pkgs.curl}/bin/curl -s -w "\n%{http_code}" "http://$HOST:$PORT/health" 2>/dev/null || echo -e "\n000")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" = "200" ]; then
      echo "✓ vLLM is healthy"
      echo "Response: $BODY"
      exit 0
    else
      echo "✗ vLLM is unhealthy (HTTP $HTTP_CODE)"
      if [ -n "$BODY" ]; then
        echo "Response: $BODY"
      fi
      exit 1
    fi
  '';

  # ============================================================================
  # OCI Container Image (using dockerTools)
  # ============================================================================
  
  vllmOciImage = pkgs.dockerTools.buildImage {
    name = "vllm-rocm-nix";
    tag = "latest";
    created = "now";
    
    # Build from scratch (minimal base)
    fromImage = null;
    
    # Include minimal filesystem
    contents = with pkgs; [
      pythonWithVllm
      rocmPackages.rocm-core
      rocmPackages.rocm-runtime
      rocmPackages.hip
      rocmPackages.rocblas
      rocmPackages.rocrand
      rocmPackages.rocsparse
      rocmPackages.hip
      rocmPackages.rocm-device-libs
      
      # Utilities
      curl
      ca-certificates
      coreutils
      bash
    ];
    
    config = {
      # Environment Variables
      Env = [
        "PYTHONUNBUFFERED=1"
        "PYTHONDONTWRITEBYTECODE=1"
        "ROCM_HOME=${rocmPackages.rocm-core}"
        "LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:${rocmPackages.rocblas}/lib64:${rocmPackages.rocsparse}/lib:${rocmPackages.rocrand}/lib:${rocmPackages.hip}/lib"
        "PATH=${rocmPackages.rocm-smi}/bin:${rocmPackages.hip}/bin:/bin:/usr/bin:/usr/local/bin"
        "HIP_VISIBLE_DEVICES=0"
        "HSA_OVERRIDE_GFX_VERSION=11.0.0"
        "VLLM_TARGET_DEVICE=rocm"
        "VLLM_ROCM_USE_AITER=1"
        "VLLM_ROCM_USE_SKINNY_GEMM=1"
        "VLLM_HOST=0.0.0.0"
        "VLLM_PORT=8000"
      ];
      
      # Entry point
      Entrypoint = [ "${vllmServer}/bin/vllm-server" ];
      
      # Exposed ports
      ExposedPorts = { "8000/tcp" = {}; };
      
      # Working directory
      WorkingDir = "/app";
      
      # Labels
      Labels = {
        "org.opencontainers.image.title" = "vLLM with ROCm (Nix-built)";
        "org.opencontainers.image.description" = "vLLM inference server optimized for AMD ROCm GPUs";
        "org.opencontainers.image.vendor" = "Cortex Project";
        "org.opencontainers.image.version" = "0.12.0";
        "org.opencontainers.image.source" = "https://github.com/vllm-project/vllm";
      };
    };
  };

  # ============================================================================
  # Systemd Service Definition
  # ============================================================================
  
  vllmSystemdService = {
    description = "vLLM Inference Server (ROCm)";
    after = [ "network.target" "dev-kfd.device" "dev-dri.device" ];
    wants = [ "dev-kfd.device" "dev-dri.device" ];
    
    serviceConfig = {
      Type = "simple";
      Restart = "always";
      RestartSec = "10s";
      
      # User and group
      User = "nexus";
      Group = "nexus";
      
      # GPU device access
      DeviceAllow = [
        "/dev/kfd rw"
        "/dev/dri rw"
        "/dev/shm rw"
      ];
      DevicePolicy = "closed";
      SupplementaryGroups = "video render";
      
      # Working directory
      WorkingDirectory = "/var/lib/vllm";
      
      # Environment variables
      Environment = [
        "PYTHONUNBUFFERED=1"
        "PYTHONDONTWRITEBYTECODE=1"
        "ROCM_HOME=${rocmPackages.rocm-core}"
        "LD_LIBRARY_PATH=${rocmPackages.rocm-runtime}/lib:${rocmPackages.rocblas}/lib:${rocmPackages.rocblas}/lib64:${rocmPackages.rocsparse}/lib:${rocmPackages.rocrand}/lib:${rocmPackages.hip}/lib"
        "HIP_VISIBLE_DEVICES=0"
        "HSA_OVERRIDE_GFX_VERSION=11.0.0"
        "VLLM_TARGET_DEVICE=rocm"
        "VLLM_ROCM_USE_AITER=1"
        "VLLM_ROCM_USE_SKINNY_GEMM=1"
        "VLLM_HOST=0.0.0.0"
        "VLLM_PORT=8000"
        "GPU_MEM_UTIL=0.48"
      ];
      
      # Start service
      ExecStart = "${vllmServer}/bin/vllm-server";
      
      # Resource limits
      MemoryLimit = "64G";
      CPUQuota = "80%";
      TasksMax = 4096;
      
      # Logging
      StandardOutput = "journal";
      StandardError = "journal";
      SyslogIdentifier = "vllm";
    };
    
    unitConfig = {
      Documentation = "https://docs.vllm.ai/";
    };
  };

  # ============================================================================
  # Combined Package (all tools)
  # ============================================================================
  
  vllmComplete = pkgs.symlinkJoin {
    name = "vllm-tools";
    paths = [
      vllmServer
      vllmHealthCheck
      pythonWithVllm
    ];
  };
}
