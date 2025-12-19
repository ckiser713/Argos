#!/usr/bin/env bash
set -euo pipefail

# Deployment Readiness Verification Script
# Checks that all artifacts and configurations are in place

ARTIFACTS_DIR="/home/nexus/amd-ai/artifacts"
ERRORS=0
WARNINGS=0

echo "=========================================="
echo "Deployment Readiness Verification"
echo "=========================================="
echo ""

# Check artifacts directory exists
echo "Checking artifacts directory..."
if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "  ✗ Artifacts directory not found: $ARTIFACTS_DIR"
    ((ERRORS++))
else
    echo "  ✓ Artifacts directory exists"
fi

# Check vLLM wheel
echo "Checking vLLM wheel..."
VLLM_WHEEL="$ARTIFACTS_DIR/vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl"
if [ ! -f "$VLLM_WHEEL" ]; then
    echo "  ✗ vLLM wheel not found: $VLLM_WHEEL"
    ((ERRORS++))
else
    SIZE=$(du -h "$VLLM_WHEEL" | cut -f1)
    echo "  ✓ vLLM wheel found ($SIZE)"
fi

# Check PyTorch wheel
echo "Checking PyTorch wheel..."
TORCH_WHEEL="$ARTIFACTS_DIR/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl"
if [ ! -f "$TORCH_WHEEL" ]; then
    echo "  ✗ PyTorch wheel not found: $TORCH_WHEEL"
    ((ERRORS++))
else
    SIZE=$(du -h "$TORCH_WHEEL" | cut -f1)
    echo "  ✓ PyTorch wheel found ($SIZE)"
fi

# Check llama.cpp binaries
echo "Checking llama.cpp binaries..."
BIN_DIR="$ARTIFACTS_DIR/bin"
if [ ! -d "$BIN_DIR" ]; then
    echo "  ✗ Binaries directory not found: $BIN_DIR"
    ((ERRORS++))
else
    if [ ! -f "$BIN_DIR/llama-cli" ]; then
        echo "  ✗ llama-cli not found"
        ((ERRORS++))
    else
        echo "  ✓ llama-cli found"
    fi
    
    if [ ! -f "$BIN_DIR/llama-server" ]; then
        echo "  ✗ llama-server not found"
        ((ERRORS++))
    else
        echo "  ✓ llama-server found"
    fi
    
    if [ ! -f "$BIN_DIR/llama-quantize" ]; then
        echo "  ✗ llama-quantize not found"
        ((ERRORS++))
    else
        echo "  ✓ llama-quantize found"
    fi
    
    # Check symlinks
    if [ -L "$BIN_DIR/llama-cpp-tuned" ]; then
        echo "  ✓ llama-cpp-tuned symlink exists"
    else
        echo "  ⚠ llama-cpp-tuned symlink missing (non-critical)"
        ((WARNINGS++))
    fi
fi

# Check configuration files
echo ""
echo "Checking configuration files..."

# Check nix/vllm.nix
if grep -q "/home/nexus/amd-ai/artifacts" nix/vllm.nix 2>/dev/null; then
    echo "  ✓ nix/vllm.nix uses correct artifacts path"
else
    echo "  ✗ nix/vllm.nix does not use correct artifacts path"
    ((ERRORS++))
fi

# Check flake.nix
if grep -q "/home/nexus/amd-ai/artifacts" flake.nix 2>/dev/null; then
    echo "  ✓ flake.nix uses correct artifacts path"
else
    echo "  ⚠ flake.nix may not use correct artifacts path"
    ((WARNINGS++))
fi

# Check backend/config.py
if grep -q "/home/nexus/amd-ai/artifacts" backend/app/config.py 2>/dev/null; then
    echo "  ✓ backend/app/config.py uses correct artifacts path"
else
    echo "  ✗ backend/app/config.py does not use correct artifacts path"
    ((ERRORS++))
fi

# Check models directory
echo ""
echo "Checking models directory..."
if [ ! -d "/models" ]; then
    echo "  ⚠ /models directory does not exist"
    ((WARNINGS++))
else
    echo "  ✓ /models directory exists"
    
    # Check for vLLM models
    if [ -d "/models/vllm" ]; then
        VLLM_COUNT=$(find /models/vllm -type f \( -name "*.safetensors" -o -name "*.bin" \) 2>/dev/null | wc -l) || VLLM_COUNT=0
        if [ "$VLLM_COUNT" -gt 0 ]; then
            echo "  ✓ vLLM models found ($VLLM_COUNT files)"
        else
            echo "  ✓ /models/vllm directory exists (ready for model downloads)"
            echo "    ⚠ No model files found yet - run download_models.py to download"
            ((WARNINGS++)) || true
        fi
    else
        echo "  ⚠ /models/vllm directory does not exist (creating...)"
        mkdir -p /models/vllm 2>/dev/null && echo "    ✓ Created /models/vllm" || echo "    ✗ Failed to create directory"
        ((WARNINGS++)) || true
    fi
    
    # Check for GGUF models
    if [ -d "/models/gguf" ]; then
        GGUF_COUNT=$(find /models/gguf -type f -name "*.gguf" 2>/dev/null | wc -l) || GGUF_COUNT=0
        if [ "$GGUF_COUNT" -gt 0 ]; then
            echo "  ✓ GGUF models found ($GGUF_COUNT files)"
        else
            echo "  ✓ /models/gguf directory exists (ready for model downloads)"
            echo "    ⚠ No model files found yet - run download_models.py to download"
            ((WARNINGS++)) || true
        fi
    else
        echo "  ⚠ /models/gguf directory does not exist (creating...)"
        mkdir -p /models/gguf 2>/dev/null && echo "    ✓ Created /models/gguf" || echo "    ✗ Failed to create directory"
        ((WARNINGS++)) || true
    fi
fi

# Summary
echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "✓ All critical checks passed!"
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠ Some warnings present (see above)"
        echo "  Models may need to be downloaded before deployment"
        echo "  See docs/DEPLOYMENT_READINESS.md for details"
    fi
    echo ""
    echo "Artifacts and configurations are ready for deployment!"
    exit 0
else
    echo "✗ Some critical checks failed (see above)"
    exit 1
fi
