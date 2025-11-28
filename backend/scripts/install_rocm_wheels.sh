#!/bin/bash
# Install ROCm-enabled PyTorch wheels from local directory
# This script installs PyTorch 2.9.1 with ROCm support for custom PyTorch tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"
ROCM_WHEELS_DIR="${ROCM_WHEELS_DIR:-$HOME/rocm/py311-tor290/wheels}"

echo "=========================================="
echo "ROCm PyTorch Wheels Installer"
echo "=========================================="
echo ""

# Check if wheels directory exists
if [ ! -d "$ROCM_WHEELS_DIR" ]; then
    echo "Error: ROCm wheels directory not found at: $ROCM_WHEELS_DIR"
    echo ""
    echo "Please ensure the wheels directory exists, or set ROCM_WHEELS_DIR:"
    echo "  export ROCM_WHEELS_DIR=/path/to/wheels"
    exit 1
fi

echo "Wheels directory: $ROCM_WHEELS_DIR"
echo ""

# Check for required subdirectories
if [ ! -d "$ROCM_WHEELS_DIR/torch2.9" ]; then
    echo "Error: PyTorch wheels directory not found: $ROCM_WHEELS_DIR/torch2.9"
    exit 1
fi

if [ ! -d "$ROCM_WHEELS_DIR/common" ]; then
    echo "Error: Common wheels directory not found: $ROCM_WHEELS_DIR/common"
    exit 1
fi

# Check Python version
PY_BIN=$(command -v python3.11 || command -v python3 || true)
if [ -z "$PY_BIN" ]; then
    echo "Error: python3.11 or python3 not found; please install Python 3.11"
    exit 1
fi
PYTHON_VERSION=$($PY_BIN --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo "Python version: $PYTHON_VERSION (binary: $PY_BIN)"

if [[ ! "$PYTHON_VERSION" =~ ^3\.11 ]]; then
    echo "⚠ Warning: PyTorch wheels are built for Python 3.11"
    echo "  Current Python version: $PYTHON_VERSION"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ] && [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "⚠ Warning: Not in a virtual environment"
    echo "  It's recommended to use a virtual environment (venv, conda, poetry)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Virtual environment detected: ${VIRTUAL_ENV:-$CONDA_DEFAULT_ENV}"
fi

echo ""
echo "Installing PyTorch stack from ROCm wheels..."
echo ""

# Set environment for offline installation
export PIP_NO_INDEX=1
export PIP_FIND_LINKS="$ROCM_WHEELS_DIR"

# Install PyTorch stack
echo "Installing PyTorch, TorchVision, TorchAudio..."
$PY_BIN -m pip install --find-links "$ROCM_WHEELS_DIR/torch2.9" \
    torch torchvision torchaudio \
    || {
        echo "Error: Failed to install PyTorch stack"
        exit 1
    }

echo ""
echo "Installing common dependencies (Triton, Tokenizers)..."
$PY_BIN -m pip install --find-links "$ROCM_WHEELS_DIR/common" \
    triton tokenizers \
    || {
        echo "Error: Failed to install common dependencies"
        exit 1
    }

echo ""
echo "=========================================="
echo "✓ Installation complete!"
echo "=========================================="
echo ""

# Verify installation
echo "Verifying installation..."
$PY_BIN << 'EOF'
import sys
try:
    import torch
    print(f"✓ PyTorch version: {torch.__version__}")
    
    # Check ROCm support
    if hasattr(torch.version, 'hip'):
        hip_version = torch.version.hip
        print(f"✓ ROCm version: {hip_version}")
    else:
        print("⚠ Warning: ROCm version not detected")
    
    # Check CUDA (should be False for ROCm build)
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        print("⚠ Warning: CUDA is available (expected False for ROCm build)")
    else:
        print("✓ CUDA not available (expected for ROCm build)")
    
    # Try to import other packages
    import torchvision
    print(f"✓ TorchVision version: {torchvision.__version__}")
    
    import torchaudio
    print(f"✓ TorchAudio version: {torchaudio.__version__}")
    
    print("")
    print("All packages installed successfully!")
    
except ImportError as e:
    print(f"✗ Error importing package: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
# End heredoc
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "Installation verified successfully!"
    echo ""
    echo "Note: These wheels are for custom PyTorch tools only."
    echo "The main inference engine (vLLM) runs in Docker and doesn't need these."
else
    echo ""
    echo "⚠ Installation completed but verification failed."
    echo "  Please check the error messages above."
    exit 1
fi


