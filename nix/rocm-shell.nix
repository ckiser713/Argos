{ pkgs ? import <nixpkgs> { system = builtins.currentSystem; } }:

# ROCm-focused dev shell for Cortex.
#
# Includes:
# - Python 3.11 + pip for installing local wheels from ~/rocm/py311-tor290/wheels
# - Node.js 20 + pnpm for frontend/e2e tools
# - ROCm tooling (rocminfo/rocm-smi/opencl runtime) for GPU verification
# - Build essentials (clang, cmake, ninja, pkg-config) for native deps
# - Docker/compose for vLLM or other containerized inference engines
#
# Usage:
#   nix-shell nix/rocm-shell.nix
#
# Optional installs inside the shell:
#   pip install --no-index --find-links ~/rocm/py311-tor290/wheels/torch2.9 torch torchvision torchaudio
#   pip install --no-index --find-links ~/rocm/py311-tor290/wheels/common triton tokenizers

pkgs.mkShell {
  name = "cortex-rocm";

  buildInputs = with pkgs; [
    # Python
    python311
    python311Packages.pip

    # Node/e2e
    nodejs_20
    nodePackages.pnpm

    # ROCm tooling
    rocminfo
    rocm-smi
    rocm-opencl-runtime

    # Build chain
    clang
    cmake
    ninja
    pkg-config

    # Container tooling
    docker
    docker-compose

    # Utilities
    git
    curl
    jq
  ];

  shellHook = ''
    echo "Cortex ROCm dev shell"
    echo "GPU info (rocminfo):"
    rocminfo | head -n 20 || true
    echo "GPU power/temps (rocm-smi):"
    rocm-smi --showpower --showtemp --showuse || true
    echo ""
    echo "To install ROCm wheels:"
    echo "  pip install --no-index --find-links ~/rocm/py311-tor290/wheels/torch2.9 torch torchvision torchaudio"
    echo "  pip install --no-index --find-links ~/rocm/py311-tor290/wheels/common triton tokenizers"
  '';
}
