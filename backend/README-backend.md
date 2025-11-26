# Cortex Backend Skeleton (FastAPI)

This is a minimal FastAPI backend skeleton for **Project Cortex**.  
It exposes typed HTTP APIs for core domains (system, context, workflows, ingest, agents, ideas, knowledge) using
Pydantic models and in-memory stub implementations.

## 1. Requirements

- Python **3.11+**
- Recommended: virtual environment (e.g. `venv` or `uv`)
- **ROCm 7.1.0** (for AMD GPU inference - optional but recommended)

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install "fastapi[standard]" uvicorn pydantic pydantic-settings
```

If you later add database, model runtimes, or other infra, extend pip deps here.

### ROCm Integration (Optional)

Cortex supports ROCm-optimized inference engines for AMD GPUs. The ROCm artifacts are located at `~/rocm/py311-tor290/`.

#### Option A: vLLM Docker Image (Recommended - Primary Inference Engine)

The pre-built vLLM Docker image provides the main inference engine:

```bash
# Load pre-built ROCm vLLM image
./ops/load_rocm_image.sh

# Update ops/docker-compose.yml to use the pre-built image:
#   inference-engine:
#     image: vllm-rocm-strix:latest
#     # Comment out 'build:' section

# Start inference engine
docker-compose -f ops/docker-compose.yml up -d inference-engine
```

The inference engine will be available at `http://localhost:11434/v1` (OpenAI-compatible API).

#### Option B: llama.cpp Local Binary (Alternative Backend)

For local inference without Docker, use the llama.cpp binaries:

```bash
# Set environment variables
export CORTEX_LLM_BACKEND=llama_cpp
export CORTEX_LLAMA_CPP_BINARY=~/rocm/py311-tor290/bin/llama-cpp
export CORTEX_LLAMA_CPP_MODEL_PATH=/path/to/your/model.gguf

# Run backend (it will use llama.cpp instead of API)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Note**: You need GGUF model files. Download compatible models from HuggingFace or convert your own.

#### Option C: PyTorch Wheels (For Custom PyTorch Tools Only)

If you need custom PyTorch-based tools (not required for standard inference):

```bash
# Install ROCm-enabled PyTorch wheels
./backend/scripts/install_rocm_wheels.sh

# Verify installation
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'ROCm: {torch.version.hip}')"
```

**Note**: The main inference engine (vLLM) runs in Docker and doesn't need these wheels. Only install if you're building custom PyTorch tools.

For more details, see `ROCM_INTEGRATION_MAP.md` in the project root.

## 2. Run the server
From the project root (where the `app/` package lives):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at:

- Interactive docs (Swagger): http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 3. High-level structure
- `app/config.py` – application settings via `pydantic-settings`.
- `app/domain/models.py` – Pydantic domain models (context, workflows, ingest, agents, ideas, knowledge, system).
- `app/services/*.py` – in-memory service layers; later you can swap these for DB/model-backed implementations.
- `app/api/routes/*.py` – FastAPI routers grouped by resource.
- `app/main.py` – FastAPI app factory and router wiring.

## 4. Next steps
- Align these models and routes with `docs/api-contract.md` and `src/domain/types.ts` once those are finalized.
- Replace in-memory services with real persistence (PostgreSQL, etc.).
- Connect runtime orchestration (LangGraph / n8n / PyTorch / vLLM / llama.cpp) behind the existing service interfaces.
