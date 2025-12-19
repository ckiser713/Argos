#!/usr/bin/env bash
set -euo pipefail

# Download a tiny vLLM model and a tiny GGUF model for smoke tests.
# This keeps deployments runnable before full production models land.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
MODELS_DIR="${MODELS_DIR:-${PROJECT_ROOT}/models}"

VLLM_REPO="${VLLM_MINIMAL_REPO:-TinyLlama/TinyLlama-1.1B-Chat-v1.0}"
GGUF_REPO="${GGUF_MINIMAL_REPO:-bartowski/TinyLlama-1.1B-Chat-v1.0-GGUF}"

VLLM_TARGET="${VLLM_MINIMAL_PATH:-${MODELS_DIR}/minimal/vllm/TinyLlama-1.1B-Chat-v1.0}"
GGUF_TARGET_DIR="$(dirname "${GGUF_MINIMAL_PATH:-${MODELS_DIR}/minimal/gguf/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf"}")"

echo "== Cortex minimal model downloader =="
echo "Models dir: ${MODELS_DIR}"
echo "vLLM repo:  ${VLLM_REPO}"
echo "GGUF repo:  ${GGUF_REPO}"
echo ""

mkdir -p "$MODELS_DIR" "$VLLM_TARGET" "$GGUF_TARGET_DIR"

python3 - <<'PY'
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except ImportError as exc:  # pragma: no cover - runtime guard
    sys.stderr.write("ERROR: huggingface_hub is required. Install with:\n")
    sys.stderr.write("  pip install --upgrade huggingface_hub\n")
    sys.exit(1)

vllm_repo = os.environ["VLLM_REPO"]
gguf_repo = os.environ["GGUF_REPO"]
vllm_target = Path(os.environ["VLLM_TARGET"])
gguf_target_dir = Path(os.environ["GGUF_TARGET_DIR"])
hf_token = os.environ.get("HF_TOKEN")

print(f"Downloading vLLM repo {vllm_repo} -> {vllm_target}")
snapshot_download(
    repo_id=vllm_repo,
    local_dir=str(vllm_target),
    local_dir_use_symlinks=False,
    token=hf_token,
    allow_patterns=["*.safetensors", "*.json", "tokenizer.*", "*.model", "*.txt", "*.py"],
)

print(f"Downloading GGUF repo {gguf_repo} -> {gguf_target_dir}")
snapshot_download(
    repo_id=gguf_repo,
    local_dir=str(gguf_target_dir),
    local_dir_use_symlinks=False,
    token=hf_token,
    allow_patterns=["*Q4_K_M.gguf"],
)

print("✓ Minimal models downloaded.")
PY

echo ""
echo "Expected sizes (approx):"
echo "- TinyLlama vLLM weights: ~2-3GB"
echo "- TinyLlama GGUF Q4_K_M:  ~0.7GB"
echo ""
echo "Paths:"
echo "- vLLM: ${VLLM_TARGET}"
echo "- GGUF: ${GGUF_TARGET_DIR}"

