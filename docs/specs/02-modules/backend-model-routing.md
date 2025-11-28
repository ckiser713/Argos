# Module: Backend Model Routing & Lanes

## Overview
This module extends the `LLMService` to support **Model Lanes**, transitioning Cortex from a single-model system to a multi-model orchestration engine. It maps specific "Intents" (Planning, Coding, Deep Reading) to the specialized models defined in the [Argos/NexusJR Catalog](../../argos_nexus_jr_long_context_model_catalog.md).

## Responsibilities
- **Request Routing:** Route `generate_text` calls to the appropriate backend (vLLM, llama.cpp, or remote) based on the requested `ModelLane`.
- **Lane Configuration:** Maintain a registry of available models and their hardware mapping (e.g., "The Brain" vs "The Super-Reader").
- **Fallback Logic:** Gracefully degrade to the "Workhorse" lane if a specialized model is offline or OOM.

## Model Lanes (The "Argos" Mapping)

Based on the Strix Halo hardware profile (128GB RAM), the routing table is defined as follows:

| Lane | Role | Recommended Model | Typical Context | Backend | Usage in Cortex |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ORCHESTRATOR** | "The Brain" | **Qwen3-30B-Thinking-256k** | 32k - 128k | vLLM (ROCm) | LangGraph Project Manager, Roadmap Generation, Agent Planning |
| **CODER** | "Code Judge" | **Qwen3-Coder-30B-1M** | 128k - 500k | vLLM / TGI | Repo Analysis, Refactoring Suggestions, Gap Analysis |
| **SUPER-READER** | "Doc Atlas" | **Nemotron-8B-UltraLong-4M** | 1M - 4M | llama.cpp (GGUF) | Deep Ingest, "Seismic" Log Analysis, Full Monorepo Audits |
| **FAST-RAG** | "Retrieval" | **MegaBeam-Mistral-7B-512k** | 16k - 128k | vLLM / llama.cpp | RAG Synthesis, Chat Q&A, Knowledge Nexus Queries |
| **GOVERNANCE** | "Compliance" | **Granite 4.x Long-Context** | 200k | llama.cpp | Spec Verification, PRD Safety Checks |

## Interfaces & Contracts

### Updated `LLMService` Interface
The `generate_text` signature in `backend/app/services/llm_service.py` must be updated:

```python
class ModelLane(StrEnum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    SUPER_READER = "super_reader"
    FAST_RAG = "fast_rag"

def generate_text(
    prompt: str,
    project_id: str,
    lane: ModelLane = ModelLane.ORCHESTRATOR,  # New Parameter
    *,
    temperature: float | None = None,
    max_tokens: int = 1000,
    json_mode: bool = False
) -> str:
    ...
Lane Resolution Logic
Check Config: Does CORTEX_MODEL_LANE_{LANE_NAME} exist?

Resolve Endpoint: If yes, use that specific base_url / model_name.

Fallback: If not configured, default to CORTEX_LLM_DEFAULT_LANE (usually ORCHESTRATOR or FAST_RAG).

Integration Points
1. AgentService & ProjectManagerGraph
Change: The Supervisor Agent (backend/app/graphs/project_manager_graph.py) must be configured to use ModelLane.ORCHESTRATOR.

Reasoning: Requires "Thinking" capabilities (Qwen3-Thinking) to generate complex DAGs and plans.

2. IngestService
Change: When performing "Deep Ingest" (processing entire folders), the service requests ModelLane.SUPER_READER.

Reasoning: Nemotron-8B is the only model capable of maintaining coherence over 1M+ tokens for "Seismic" analysis.

3. RepoService
Change: Code analysis tasks request ModelLane.CODER.

Reasoning: General purpose models fail at specific refactoring syntax; Qwen-Coder is required.

Config Parameters (New)
Bash

# Default / Orchestrator (vLLM Port 8000)
CORTEX_LLM_BASE_URL=http://localhost:8000/v1
CORTEX_LLM_MODEL=Qwen3-30B-Thinking

# Super-Reader (llama.cpp Port 8080 - optimized for KV Cache)
CORTEX_LANE_SUPER_READER_URL=http://localhost:8080/v1
CORTEX_LANE_SUPER_READER_MODEL=Nemotron-8B-UltraLong-4M

# Coder (vLLM Port 8000 - served alongside Orchestrator or via LoRA)
CORTEX_LANE_CODER_MODEL=Qwen3-Coder-30B-1M
Risks & Mitigations
VRAM Contention: Running vLLM (Orchestrator) and llama.cpp (Reader) simultaneously on 128GB RAM requires strict memory partitioning. (See 04-runtime-and-ops-strix-optimization.md).

Latency: Switching lanes might incur model loading times if not using a model server that supports multi-model serving (like vLLM).