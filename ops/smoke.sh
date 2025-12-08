#!/usr/bin/env bash
set -euo pipefail

BASE_URL_BACKEND="${BASE_URL_BACKEND:-http://localhost:8000}"
VLLM_URL="${VLLM_URL:-http://localhost:8000}"
LLAMA_SR_URL="${LLAMA_SR_URL:-http://localhost:8080}"
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"

echo "[1/4] Backend docs..."
curl -f "${BASE_URL_BACKEND}/api/docs" >/dev/null
echo "OK"

echo "[2/4] vLLM health..."
curl -f "${VLLM_URL}/health" >/dev/null
echo "OK"

echo "[3/4] llama.cpp (super reader) health..."
curl -f "${LLAMA_SR_URL}/health" >/dev/null
echo "OK"

echo "[4/4] Qdrant health..."
curl -f "${QDRANT_URL}/healthz" >/dev/null
echo "OK"

echo "Smoke checks passed."
