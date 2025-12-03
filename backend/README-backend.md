# Cortex Backend Skeleton (FastAPI)

This is a minimal FastAPI backend skeleton for **Project Cortex**.  
It exposes typed HTTP APIs for core domains (system, context, workflows, ingest, agents, ideas, knowledge) using
Pydantic models and in-memory stub implementations.

## 1. Requirements

- Python **3.11+**
	- Recommended: run `tools/ensure_python311_poetry.sh` to set Poetry's virtualenv to Python 3.11 and install dependencies.
- Recommended: virtual environment (e.g. `venv` or `uv`)
- **ROCm 7.1.0** (for AMD GPU inference - optional but recommended)

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install "fastapi[standard]" uvicorn pydantic pydantic-settings
```

Note: If you use `pyenv` you can set the local Python version to 3.11.14 with:

```bash
pyenv install 3.11.14
pyenv local 3.11.14
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

### Download Models

Cortex uses multiple Hugging Face models for different purposes:

**Embedding Models (Vector Search):**
- `all-MiniLM-L6-v2` (384d) - General purpose embeddings, always needed
- `jinaai/jina-embeddings-v2-base-code` (768d) - Code-specific embeddings  
- `microsoft/codebert-base` (768d) - Alternative code embeddings

**Why multiple models?** The system uses a fallback chain for robustness:
1. Try code-specific model first (better semantic understanding)
2. Fall back to alternative code model
3. Final fallback to general-purpose model

**Lane Models (GGUF for llama.cpp):**
- SUPER_READER: Long-context model for document analysis
- GOVERNANCE: Compliance checking model

To pre-download models:

```bash
# Download all embedding models (recommended for full functionality)
python scripts/download_models.py

# Download only essential models (saves ~2GB disk space)
export CORTEX_DOWNLOAD_EMBEDDINGS_MINIMAL=true
python scripts/download_models.py

# Download specific lane models
export CORTEX_DOWNLOAD_SUPER_READER=true
export CORTEX_DOWNLOAD_GOVERNANCE=true
python scripts/download_models.py
```

Models are cached in `~/.cache/huggingface/` and `~/cortex_models/` for reuse.

### Model Lanes & Routing

Cortex supports **Model Lanes** for routing requests to specialized models based on intent:

| Lane | Purpose | Backend | Configuration |
| :--- | :--- | :--- | :--- |
| **ORCHESTRATOR** | Planning, agent coordination | vLLM | `CORTEX_LANE_ORCHESTRATOR_*` |
| **CODER** | Code analysis, refactoring | vLLM | `CORTEX_LANE_CODER_*` |
| **SUPER_READER** | Long-context reading | llama.cpp | `CORTEX_LANE_SUPER_READER_*` |
| **FAST_RAG** | Retrieval & Q&A | vLLM/llama.cpp | `CORTEX_LANE_FAST_RAG_*` |
| **GOVERNANCE** | Compliance checking | llama.cpp | `CORTEX_LANE_GOVERNANCE_*` |

#### Configuration

Set lane-specific URLs and models:

```bash
# Orchestrator (default lane)
export CORTEX_LLM_BASE_URL="http://localhost:8000/v1"
export CORTEX_LLM_MODEL="Qwen3-30B-Thinking"

# Super-Reader (llama.cpp for long context)
export CORTEX_LANE_SUPER_READER_URL="http://localhost:8080/v1"
export CORTEX_LANE_SUPER_READER_MODEL="Nemotron-8B-UltraLong-4M"

# Coder (vLLM for code tasks)
export CORTEX_LANE_CODER_MODEL="Qwen3-Coder-30B-1M"
```

#### Usage in Code

```python
from app.services.llm_service import generate_text

# The system now automatically routes based on the prompt content.
# The 'lane' parameter is no longer needed.
response = generate_text("Plan this project", project_id="proj-123")

# Example of a complex prompt that might be routed to a powerful model
response = generate_text(
    "Analyze this code and suggest refactorings to improve performance.", 
    project_id="proj-123"
)
```

The system automatically routes to the appropriate backend with fallback to the default lane if specialized models are unavailable.

#### Option C: PyTorch Wheels (Required for sentence-transformers)

**IMPORTANT**: `sentence-transformers` (used for embeddings in `QdrantService`) requires PyTorch. You must install ROCm-enabled PyTorch wheels from `~/rocm/py311-tor290/wheels/`.

```bash
# Install ROCm-enabled PyTorch wheels (required for sentence-transformers)
pip install --no-index --find-links ~/rocm/py311-tor290/wheels/torch2.9 torch torchvision torchaudio
pip install --no-index --find-links ~/rocm/py311-tor290/wheels/common triton tokenizers

# Verify installation
python3.11 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'ROCm: {torch.version.hip}')"
```

**Available ROCm wheels** (see `~/rocm/py311-tor290/README.md` for details):
- `torch-2.9.1a0+gitd38164a` - ROCm 7.1.1, HIP-enabled, gfx1151
- `torchvision-0.25.0a0+617079d` - ROCm-enabled
- `torchaudio-2.9.1+a224ab2` - ROCm-enabled
- `triton-3.5.0+gitc3c476f3` - ROCm backend
- `tokenizers-0.22.3.dev0` - Universal (works with ROCm)

**Optional ROCm wheels** (if needed):
- `onnxruntime_rocm-1.24.0` - ROCm variant (not CPU generic)
- `ctranslate2-4.6.1` - ROCm-enabled inference
- `bitsandbytes-0.48.0.dev0` - ROCm quantization (gfx1151 support)

**Note**: 
- Do NOT install PyTorch from PyPI or CUDA indexes - use ROCm wheels only
- All wheels are GPU-enabled with zero CPU-only builds, optimized for AMD Ryzen AI Max+ 395
- The main inference engine (vLLM) runs in Docker and doesn't need these wheels, but `sentence-transformers` does

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
