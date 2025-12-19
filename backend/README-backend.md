# Cortex Backend Skeleton (FastAPI)

This is a minimal FastAPI backend skeleton for **Project Cortex**.
It exposes typed HTTP APIs for core domains (system, context, workflows, ingest, agents, ideas, knowledge) using
Pydantic models and in-memory stub implementations.

### Security

The FastAPI backend implements robust API authentication (e.g., JWT)
and granular authorization mechanisms.
This addresses critical security vulnerabilities related to unauthorized access.

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
export CORTEX_LLM_MODEL="DeepSeek-R1-Distill-Qwen-32B"

# Super-Reader (llama.cpp for long context)
export CORTEX_LANE_SUPER_READER_URL="http://localhost:8080/v1"
export CORTEX_LANE_SUPER_READER_MODEL="Nemotron-8B-UltraLong-4M"

# Coder (vLLM for code tasks)
export CORTEX_LANE_CODER_MODEL="Qwen2.5-Coder-32B-Instruct"
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

## Observability (logging, metrics, health, tracing)
- Logging: JSON-structured output with `timestamp`, `level`, `logger`, `message`, `request_id`, `trace_id`, `user`, `path`, `status_code`. Configure via `CORTEX_LOG_LEVEL` (default `INFO`) and `CORTEX_LOG_JSON` (default `true`). Payloads/bodies are not logged.
- Metrics: Prometheus at `/metrics` (proxied by Caddy). Includes HTTP request counts/latency, ingest job status counters/gauges, embedding/model call counts + error rates. Example scrape config:
  ```
  scrape_configs:
    - job_name: cortex-backend
      metrics_path: /metrics
      static_configs:
        - targets: ['localhost:8000']
  ```
- Health: `/healthz` liveness; `/readyz` readiness checks Postgres connectivity, Qdrant reachability, embedding availability, and model lane health endpoints. Existing `/api/system/ready` remains (auth-protected) and shares the same checks.
- Tracing: Enable OTLP tracing with `CORTEX_ENABLE_TRACING=true`, `CORTEX_OTEL_EXPORTER_ENDPOINT=http://otel-collector:4318/v1/traces`, optional `CORTEX_OTEL_SERVICE_NAME` and `CORTEX_OTEL_SAMPLE_RATIO` (0-1). FastAPI and `requests` are instrumented; trace IDs flow into logs.
- Dashboards/alerts to start with: HTTP latency (p95/p99) and error rate, readiness probe failures, ingest job failures by status, embedding/model error ratios, and Qdrant/model-lane availability.

## Authentication
- Default in-memory credentials have been removed. All users live in Postgres/SQLite tables (`auth_users`, `auth_refresh_tokens`, `auth_token_blacklist`).
- Required env vars:
  - `CORTEX_AUTH_SECRET` (32+ chars) – required for `strix`/`production`, autogenerated in `local` if missing.
  - `CORTEX_ACCESS_TOKEN_MINUTES` – short-lived access token lifetime (default 15).
  - `CORTEX_REFRESH_TOKEN_DAYS` – refresh token lifetime (default 7).
  - `CORTEX_SKIP_AUTH` – only respected in `local` (defaults to `true` locally, forced `false` elsewhere).
- Bootstrap an admin (only when no users exist):
  - Local route: `POST /api/auth/bootstrap-admin` with `{"username": "...", "password": "..."}`.
  - CLI: `python backend/scripts/bootstrap_admin.py --username alice --password 'S3cureP@ss'`
- Login: `POST /api/auth/token` (OAuth2 password flow) returns access + refresh tokens. Refresh via `POST /api/auth/token/refresh`. Logout/revoke via `POST /api/auth/logout`.
- Security notes: access tokens include a token version and are checked against a server-side blacklist; refresh tokens are stored hashed in `auth_refresh_tokens`. For future IdP/OIDC, plug an external issuer and map `sub`/roles to `auth_users` while keeping the existing token blacklist and refresh storage.

## Ingest pipeline (durable storage + queue)
- Uploads are written to object storage (S3/MinIO via `CORTEX_STORAGE_*`; local default `storage_uploads`) with checksum, size, and MIME validation.
- Ingest jobs are queued to Celery (Redis broker/result). Start a worker with:  
  `celery -A app.worker.celery_app worker -Q ingest --loglevel=info`
- Key env vars: `CORTEX_STORAGE_BUCKET`, `CORTEX_STORAGE_ENDPOINT_URL`, `CORTEX_STORAGE_ACCESS_KEY/SECRET_KEY`, `CORTEX_CELERY_BROKER_URL`, `CORTEX_CELERY_RESULT_BACKEND`, `CORTEX_TASKS_EAGER` (true locally for inline execution).

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
