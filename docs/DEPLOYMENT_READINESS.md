# Deployment Readiness Status

## Artifacts Integration ✅

All ROCm artifacts have been configured to use `/home/nexus/amd-ai/artifacts`:

- **vLLM Wheel**: `/home/nexus/amd-ai/artifacts/vllm_docker_rocm/vllm-0.12.0+rocm711-cp311-cp311-linux_x86_64.whl` ✅
- **PyTorch Wheel**: `/home/nexus/amd-ai/artifacts/vllm_docker_rocm/torch-2.9.1-cp311-cp311-linux_x86_64.whl` ✅
- **llama.cpp Binaries**: `/home/nexus/amd-ai/artifacts/bin/` ✅
  - `llama-cli` (symlinked as `llama-cpp-tuned`)
  - `llama-server`
  - `llama-quantize` (symlinked as `llama-quantize-tuned`)

## Configuration Updates ✅

### Nix Configuration
- `nix/vllm.nix`: Updated to use artifacts directory and install wheels automatically
- `flake.nix`: Updated all paths from `~/rocm/py311-tor290` to `/home/nexus/amd-ai/artifacts`

### Backend Configuration
- `backend/app/config.py`: Updated default paths for llama.cpp binaries
- `backend/scripts/install_rocm_wheels.sh`: Updated to use new artifacts location
- `backend/pyproject.toml`: Updated documentation comments

## Model Status ⚠️

### Required Models (Not Yet Downloaded)

#### vLLM Models (for `/models/vllm/`)
These need to be downloaded using `backend/scripts/download_models.py`:

1. **Orchestrator**: `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
   - Target: `/models/vllm/orchestrator/bf16/`
   - Size: ~60GB

2. **Coder**: `Qwen/Qwen2.5-Coder-32B-Instruct`
   - Target: `/models/vllm/coder/bf16/`
   - Size: ~60GB

3. **Fast RAG**: `meta-llama/Llama-3.2-11B-Vision-Instruct`
   - Target: `/models/vllm/fast_rag/bf16/`
   - Size: ~22GB

#### GGUF Models (for `/models/gguf/`)
These need to be downloaded using `backend/scripts/download_models.py`:

1. **Super Reader**: `Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf`
   - Target: `/models/gguf/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf`
   - Size: ~5GB
   - Note: Not found in `~/ai_mods`

2. **Governance**: `granite-3.0-8b-instruct-Q4_K_M.gguf`
   - Target: `/models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf`
   - Size: ~5GB
   - Note: File in `~/ai_mods` was 0 bytes and has been removed

### Models Found in `~/ai_mods`
- Vocabulary files (ggml-vocab-*.gguf) - these are vocabularies, not full models
- Llama-2-7b-chat variants - not the required models
- **No matching models found for required lanes**

## Deployment Steps Remaining

1. **Download Models**:
   ```bash
   cd /home/nexus/Argos_Chatgpt
   export MODELS_DIR=/models
   python3 backend/scripts/download_models.py
   ```
   Note: Requires Hugging Face token if models are gated. Set `HF_TOKEN` environment variable.

2. **Verify Model Locations**:
   - Ensure `/models/vllm/{orchestrator,coder,fast_rag}/bf16/` contain model files
   - Ensure `/models/gguf/` contains the GGUF files

3. **Database Migration**:
   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Environment Configuration**:
   - Review and update `ops/cortex.env` with production values
   - Ensure all required environment variables are set

5. **Storage Space**:
   - Ensure `/models` has at least 150GB+ free space for all models

## Verification

Run deployment checks:
```bash
cd /home/nexus/Argos_Chatgpt
ops/run_checks.sh
```

Or manually verify:
- Artifacts are accessible: `ls -lh /home/nexus/amd-ai/artifacts/bin/llama-cli`
- Wheels are present: `ls -lh /home/nexus/amd-ai/artifacts/vllm_docker_rocm/*.whl`
- Models are downloaded: `ls -lh /models/vllm/*/bf16/` and `ls -lh /models/gguf/*.gguf`
