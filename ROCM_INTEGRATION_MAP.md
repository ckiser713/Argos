# ROCm Integration Map: `~/rocm/py311-tor290` → Cortex Project

This document provides a comprehensive overview of all files in `~/rocm/py311-tor290` and maps them to relevant files in the Cortex project that should reference or use these ROCm artifacts.

**Date**: Generated from exploration  
**ROCm Directory**: `/home/nexus/rocm/py311-tor290`  
**Target Architecture**: gfx1151 (AMD Radeon)  
**ROCm Version**: 7.1.0  
**Python Version**: 3.11.9  
**PyTorch Version**: 2.9.1

---

## Directory Structure Overview

```
~/rocm/py311-tor290/
├── bin/                    # Compiled binaries (llama.cpp tools) - 162 MB
│   ├── llama-bench         # Symlink → llama-bench-tuned
│   ├── llama-bench-tuned   # Performance benchmarking tool (54 MB)
│   ├── llama-cpp           # Symlink → llama-cpp-tuned
│   ├── llama-cpp-tuned     # Main inference engine (56 MB)
│   ├── llama-quantize      # Symlink → llama-quantize-tuned
│   └── llama-quantize-tuned # Model quantization tool (53 MB)
│
├── images/                 # Docker images (vLLM) - 22 GB
│   ├── vllm_rocm_image.tar # Complete vLLM Docker image with ROCm support
│   └── vllm_rocm_image.tar.sha256 # SHA256 checksum
│
└── wheels/                 # Python wheel packages - 387 MB
    ├── common/             # Common dependencies (303 MB)
    │   ├── tokenizers-0.22.2.dev0-cp39-abi3-linux_x86_64.whl (3.2 MB)
    │   └── triton-3.5.0+gitc3c476f3-cp311-cp311-linux_x86_64.whl (300 MB)
    └── torch2.9/           # PyTorch stack (84 MB)
        ├── torch-2.9.1a0+gitd38164a-cp311-cp311-linux_x86_64.whl (83 MB)
        ├── torchaudio-2.9.1+a224ab2-cp311-cp311-linux_x86_64.whl (489 KB)
        └── torchvision-0.25.0a0+617079d-cp311-cp311-linux_x86_64.whl (1.3 MB)
```

---

## File-to-Project Mapping

### 1. **Binaries (`/bin`) → Project Integration**

#### Files:
- `llama-cpp-tuned` (56 MB) - Main llama.cpp inference engine
- `llama-bench-tuned` (54 MB) - Performance benchmarking tool
- `llama-quantize-tuned` (53 MB) - Model quantization tool

#### Associated Cortex Project Files:

**Primary Integration Points:**
- **`backend/app/services/llm_service.py`**
  - Currently uses OpenAI-compatible API client
  - Should be extended to support local llama.cpp inference via these binaries
  - Add `LanguageModelRunner` interface implementation for llama.cpp

- **`backend/app/config.py`**
  - Add configuration for llama.cpp binary path:
    ```python
    llama_cpp_binary_path: str = Field(
        default="/home/nexus/rocm/py311-tor290/bin/llama-cpp",
        env="CORTEX_LLAMA_CPP_BINARY"
    )
    llama_cpp_model_path: str = Field(
        default="",  # Path to GGUF model files
        env="CORTEX_LLAMA_CPP_MODEL_PATH"
    )
    ```

- **`ops/docker-compose.yml`**
  - Consider mounting the binaries directory if running in containers:
    ```yaml
    volumes:
      - ~/rocm/py311-tor290/bin:/usr/local/bin/llama-cpp-tools:ro
    ```

**Potential New Files:**
- **`backend/app/services/llama_cpp_service.py`** (NEW)
  - Service wrapper for llama.cpp binary execution
  - Handles subprocess calls, model loading, inference
  - Implements `LanguageModelRunner` interface

- **`backend/app/runners/llama_cpp_runner.py`** (NEW)
  - Runner class for llama.cpp integration
  - Manages model lifecycle, context windows, quantization

**Usage Example:**
```python
# In llm_service.py or new llama_cpp_service.py
import subprocess
import json

def call_llama_cpp(prompt: str, model_path: str, **kwargs) -> str:
    binary = settings.llama_cpp_binary_path
    cmd = [
        binary,
        "-m", model_path,
        "-p", prompt,
        "--temp", str(kwargs.get("temperature", 0.7)),
        "--n-predict", str(kwargs.get("max_tokens", 512)),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

---

### 2. **Docker Images (`/images`) → Project Integration**

#### Files:
- `vllm_rocm_image.tar` (22 GB) - Complete vLLM Docker image with ROCm support
- `vllm_rocm_image.tar.sha256` (99 bytes) - SHA256 checksum

#### Associated Cortex Project Files:

**Primary Integration Points:**
- **`ops/Dockerfile.vllm`**
  - **CURRENT STATE**: Builds from `rocm/pytorch:rocm7.1_ubuntu22.04_py3.11_pytorch_2.9.1`
  - **RECOMMENDED CHANGE**: Load pre-built image instead of building:
    ```dockerfile
    # Option 1: Load pre-built image
    # docker load -i ~/rocm/py311-tor290/images/vllm_rocm_image.tar
    # Then use: FROM vllm-rocm-strix:latest
    
    # Option 2: Update docker-compose.yml to load image
    ```

- **`ops/docker-compose.yml`**
  - **CURRENT STATE**: Builds inference-engine from Dockerfile.vllm
  - **RECOMMENDED CHANGE**: Load pre-built image and use it:
    ```yaml
    inference-engine:
      # Option 1: Load image manually, then use:
      image: vllm-rocm-strix:latest
      
      # Option 2: Use build with image load step
      build:
        context: .
        dockerfile: Dockerfile.vllm
        args:
          ROCM_IMAGE_PATH: ~/rocm/py311-tor290/images/vllm_rocm_image.tar
    ```

**Integration Script:**
- **`ops/load_rocm_image.sh`** (NEW)
  ```bash
  #!/bin/bash
  # Load ROCm vLLM image
  docker load -i ~/rocm/py311-tor290/images/vllm_rocm_image.tar
  
  # Verify checksum
  cd ~/rocm/py311-tor290/images
  sha256sum -c vllm_rocm_image.tar.sha256
  
  echo "ROCm vLLM image loaded successfully"
  ```

**Configuration Updates:**
- **`backend/app/config.py`**
  - Already has `llm_base_url` pointing to inference engine
  - Default: `http://localhost:11434/v1` (mapped from container port 8000)
  - No changes needed, but ensure vLLM container uses correct port

---

### 3. **Python Wheels (`/wheels`) → Project Integration**

#### Files:

**Common Dependencies (`/wheels/common`):**
- `tokenizers-0.22.2.dev0-cp39-abi3-linux_x86_64.whl` (3.2 MB)
- `triton-3.5.0+gitc3c476f3-cp311-cp311-linux_x86_64.whl` (300 MB)

**PyTorch Stack (`/wheels/torch2.9`):**
- `torch-2.9.1a0+gitd38164a-cp311-cp311-linux_x86_64.whl` (83 MB)
- `torchvision-0.25.0a0+617079d-cp311-cp311-linux_x86_64.whl` (1.3 MB)
- `torchaudio-2.9.1+a224ab2-cp311-cp311-linux_x86_64.whl` (489 KB)

#### Associated Cortex Project Files:

**Primary Integration Points:**
- **`backend/pyproject.toml`**
  - **CURRENT STATE**: No PyTorch dependencies listed
  - **RECOMMENDED CHANGE**: Add PyTorch stack (optional, for custom PyTorch tools):
    ```toml
    [tool.poetry.dependencies]
    # ... existing dependencies ...
    
    # PyTorch stack (ROCm-enabled, installed from local wheels)
    # Note: Install manually using:
    # pip install --no-index --find-links ~/rocm/py311-tor290/wheels/torch2.9 torch torchvision torchaudio
    # pip install --no-index --find-links ~/rocm/py311-tor290/wheels/common triton tokenizers
    ```

- **`backend/README-backend.md`**
  - Add installation instructions for ROCm wheels:
    ```markdown
    ## ROCm PyTorch Installation (Optional)
    
    For custom PyTorch tools requiring ROCm support:
    
    ```bash
    export PIP_NO_INDEX=1
    export PIP_FIND_LINKS=~/rocm/py311-tor290/wheels
    
    pip install --find-links ~/rocm/py311-tor290/wheels/torch2.9 \
      torch torchvision torchaudio
    
    pip install --find-links ~/rocm/py311-tor290/wheels/common \
      triton tokenizers
    ```
    
    Verify installation:
    ```bash
    python3.11 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'ROCm: {torch.version.hip}')"
    ```
    ```

**Installation Script:**
- **`backend/scripts/install_rocm_wheels.sh`** (NEW)
  ```bash
  #!/bin/bash
  # Install ROCm-enabled PyTorch wheels
  
  ROCM_WHEELS_DIR="$HOME/rocm/py311-tor290/wheels"
  
  if [ ! -d "$ROCM_WHEELS_DIR" ]; then
    echo "Error: ROCm wheels directory not found at $ROCM_WHEELS_DIR"
    exit 1
  fi
  
  export PIP_NO_INDEX=1
  export PIP_FIND_LINKS="$ROCM_WHEELS_DIR"
  
  echo "Installing PyTorch stack from ROCm wheels..."
  pip install --find-links "$ROCM_WHEELS_DIR/torch2.9" \
    torch torchvision torchaudio
  
  echo "Installing common dependencies..."
  pip install --find-links "$ROCM_WHEELS_DIR/common" \
    triton tokenizers
  
  echo "Verifying installation..."
  python3.11 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'ROCm: {torch.version.hip}')"
  ```

**Nix Integration (Optional):**
- **`backend/flake.nix`** or **`nix/overlays.nix`**
  - Could add overlay to use local wheels, but Poetry handles Python deps
  - Consider adding ROCm libraries if building custom tools:
    ```nix
    # In overlays.nix
    rocmPackages = prev.rocmPackages.overrideScope' (rocmFinal: rocmPrev: {
      # Custom ROCm configuration
    });
    ```

**Potential New Files (if custom PyTorch tools needed):**
- **`backend/app/services/pytorch_service.py`** (NEW)
  - Service for custom PyTorch-based inference/training
  - Uses ROCm-enabled PyTorch from wheels
  - Implements `CodeModelRunner` or `EmbeddingRunner` interfaces

- **`backend/app/runners/pytorch_rocm_runner.py`** (NEW)
  - Runner for PyTorch models with ROCm acceleration
  - Handles GPU memory management, model loading

---

## Integration Summary by Component

### A. **llama.cpp Integration** (Binaries)

**Status**: Not currently integrated  
**Priority**: Medium (alternative to vLLM for local inference)

**Files to Modify:**
1. `backend/app/config.py` - Add llama.cpp configuration
2. `backend/app/services/llm_service.py` - Add llama.cpp support option

**Files to Create:**
1. `backend/app/services/llama_cpp_service.py` - Service wrapper
2. `backend/app/runners/llama_cpp_runner.py` - Runner implementation

**Dependencies:**
- llama.cpp binaries: `~/rocm/py311-tor290/bin/llama-cpp-tuned`
- GGUF model files (user-provided)

---

### B. **vLLM Integration** (Docker Image)

**Status**: Partially integrated (Dockerfile exists, but builds from source)  
**Priority**: High (primary inference engine)

**Files to Modify:**
1. `ops/Dockerfile.vllm` - Use pre-built image or load it
2. `ops/docker-compose.yml` - Load pre-built image

**Files to Create:**
1. `ops/load_rocm_image.sh` - Image loading script
2. `ops/verify_rocm_image.sh` - Checksum verification

**Dependencies:**
- vLLM Docker image: `~/rocm/py311-tor290/images/vllm_rocm_image.tar`
- Docker with ROCm device access (`/dev/kfd`, `/dev/dri`)

---

### C. **PyTorch Stack Integration** (Wheels)

**Status**: Not integrated (not required for current backend)  
**Priority**: Low (only needed for custom PyTorch tools)

**Files to Modify:**
1. `backend/pyproject.toml` - Document optional PyTorch installation
2. `backend/README-backend.md` - Add installation instructions

**Files to Create:**
1. `backend/scripts/install_rocm_wheels.sh` - Installation script

**Dependencies:**
- PyTorch wheels: `~/rocm/py311-tor290/wheels/torch2.9/*.whl`
- Common wheels: `~/rocm/py311-tor290/wheels/common/*.whl`
- Python 3.11 environment

---

## Recommended Integration Order

1. **Phase 1: vLLM Docker Image** (High Priority)
   - Load pre-built vLLM image
   - Update docker-compose.yml to use it
   - Verify inference engine works

2. **Phase 2: llama.cpp Binaries** (Medium Priority)
   - Add configuration for llama.cpp
   - Create service wrapper
   - Integrate as alternative inference backend

3. **Phase 3: PyTorch Wheels** (Low Priority)
   - Only if custom PyTorch tools are needed
   - Create installation script
   - Document usage

---

## Environment Variables

Add to `.env` or `backend/.env`:

```bash
# ROCm Integration
CORTEX_ROCM_WHEELS_DIR=~/rocm/py311-tor290/wheels
CORTEX_ROCM_BIN_DIR=~/rocm/py311-tor290/bin
CORTEX_ROCM_IMAGE_PATH=~/rocm/py311-tor290/images/vllm_rocm_image.tar

# llama.cpp (if using)
CORTEX_LLAMA_CPP_BINARY=~/rocm/py311-tor290/bin/llama-cpp
CORTEX_LLAMA_CPP_MODEL_PATH=/path/to/models

# vLLM (already configured)
CORTEX_LLM_BASE_URL=http://localhost:11434/v1
CORTEX_LLM_API_KEY=ollama
CORTEX_LLM_MODEL=llama3
```

---

## Verification Checklist

- [ ] vLLM Docker image loads successfully
- [ ] vLLM container runs with ROCm device access
- [ ] Inference engine responds at configured URL
- [ ] llama.cpp binaries are executable (if integrated)
- [ ] PyTorch wheels install correctly (if needed)
- [ ] ROCm version detected: `torch.version.hip` shows 7.1.0
- [ ] GPU visible: `torch.cuda.is_available()` returns False (ROCm, not CUDA)
- [ ] HIP visible: `torch.version.hip` shows version string

---

## Notes

1. **Offline Installation**: All wheels are offline-capable (no network required)
2. **Architecture**: All artifacts built for Linux x86_64, Python 3.11
3. **CUDA-Free**: No NVIDIA/CUDA dependencies, pure ROCm implementation
4. **Image Size**: vLLM image is 22 GB - ensure sufficient disk space
5. **Device Access**: Docker containers need `/dev/kfd` and `/dev/dri` access for ROCm

---

## References

- ROCm Directory README: `~/rocm/py311-tor290/README.md`
- Build Report: `~/ROCM_APU_VALIDATION/GMKTEC_BUILD_REPORT.json`
- Build Summary: `~/ROCM_APU_VALIDATION/GMKTEC_BUILD_SUMMARY.md`
- Cortex Architecture: `System Blueprint & Architecture_ Project Cortex.md`
- Cortex README: `README.md`

