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
| **ORCHESTRATOR** | "The Brain" | **DeepSeek-R1-Distill-Qwen-32B** | 32k - 128k | vLLM (ROCm) | LangGraph Project Manager, Roadmap Generation, Agent Planning |
| **CODER** | "Code Judge" | **Qwen2.5-Coder-32B-Instruct** | 128k - 500k | vLLM (ROCm) | Repo Analysis, Refactoring Suggestions, Gap Analysis |
| **SUPER-READER** | "Doc Atlas" | **Nemotron-8B-UltraLong-4M** | 1M - 4M | llama.cpp (GGUF) | Deep Ingest, "Seismic" Log Analysis, Full Monorepo Audits |
| **FAST-RAG** | "Retrieval" | **Llama-3.2-11B-Vision-Instruct** | 16k - 128k | vLLM (ROCm) | RAG Synthesis, Chat Q&A, Knowledge Nexus Queries |
| **GOVERNANCE** | "Compliance" | **granite-3.0-8b-instruct** | 200k | llama.cpp | Spec Verification, PRD Safety Checks |

## Interfaces & Contracts

### Updated `LLMService` Interface
The `generate_text` signature in `backend/app/services/llm_service.py` must be updated:

```python
class ModelLane(StrEnum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    SUPER_READER = "super_reader"
    FAST_RAG = "fast_rag"
    GOVERNANCE = "governance"

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
```

Lane Resolution Logic
Check Config: Does `ARGOS_LANE_{LANE}_URL/MODEL/MODEL_PATH` exist?

Resolve Endpoint: If yes, use that specific base_url / model_name.

Fallback: If not configured, fall back to `config/model_registry.json` defaults, then to ORCHESTRATOR or SUPER_READER as needed.

Integration Points
1. AgentService & ProjectManagerGraph
Change: The Supervisor Agent (backend/app/graphs/project_manager_graph.py) must be configured to use ModelLane.ORCHESTRATOR.

Reasoning: Requires DeepSeek-R1-Distill-Qwen-32B's thinking capabilities to generate complex DAGs and plans.

2. IngestService
Change: When performing "Deep Ingest" (processing entire folders), the service requests ModelLane.SUPER_READER.

Reasoning: Nemotron-8B is the only model capable of maintaining coherence over 1M+ tokens for "Seismic" analysis.

3. RepoService
Change: Code analysis tasks request ModelLane.CODER.

Reasoning: General purpose models fail at specific refactoring syntax; Qwen2.5-Coder-32B-Instruct is required.

Config Parameters (New)
Bash

# Default / Orchestrator (vLLM Port 8000)
ARGOS_LLM_BASE_URL=http://localhost:8000/v1
ARGOS_LLM_MODEL=DeepSeek-R1-Distill-Qwen-32B

# Super-Reader (llama.cpp Port 8080 - optimized for KV Cache)
ARGOS_LANE_SUPER_READER_URL=http://localhost:8080/v1
ARGOS_LANE_SUPER_READER_MODEL=Nemotron-8B-UltraLong-4M

# Coder (vLLM Port 8000 - served alongside Orchestrator or via LoRA)
ARGOS_LANE_CODER_MODEL=Qwen2.5-Coder-32B-Instruct

# Fast RAG (vLLM Port 8000 - shared GPU switching)
ARGOS_LANE_FAST_RAG_MODEL=Llama-3.2-11B-Vision-Instruct

# Governance (llama.cpp Port 8081)
ARGOS_LANE_GOVERNANCE_MODEL=granite-3.0-8b-instruct
Risks & Mitigations
VRAM Contention: Running vLLM (Orchestrator) and llama.cpp (Reader) simultaneously on 128GB RAM requires strict memory partitioning. (See 04-runtime-and-ops-strix-optimization.md).

Latency: Switching lanes might incur model loading times if not using a model server that supports multi-model serving (like vLLM).
