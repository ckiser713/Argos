# Model Lanes Quick Reference

## Overview

Cortex uses **Model Lanes** to route different types of requests to specialized models optimized for specific tasks. This document provides a quick reference for developers.

## Lane Mapping

| Lane | Role | Model | Backend | Port | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ORCHESTRATOR** | "The Brain" | Qwen3-30B-Thinking-256k | vLLM (ROCm) | 8000 | LangGraph Project Manager, Roadmap Generation, Agent Planning |
| **CODER** | "Code Judge" | Qwen3-Coder-30B-1M | vLLM / TGI | 8000 | Repo Analysis, Refactoring Suggestions, Gap Analysis |
| **SUPER-READER** | "Doc Atlas" | Nemotron-8B-UltraLong-4M | llama.cpp (GGUF) | 8080 | Deep Ingest, "Seismic" Log Analysis, Full Monorepo Audits |
| **FAST-RAG** | "Retrieval" | MegaBeam-Mistral-7B-512k | vLLM / llama.cpp | 8000 | RAG Synthesis, Chat Q&A, Knowledge Nexus Queries |
| **GOVERNANCE** | "Compliance" | Granite 4.x Long-Context | llama.cpp | 8080 | Spec Verification, PRD Safety Checks |

## Usage in Code

### Basic Usage

```python
from app.services.llm_service import generate_text, ModelLane

# Use ORCHESTRATOR for planning tasks
response = generate_text(
    prompt="Create a roadmap for building a trading bot",
    project_id="proj-123",
    lane=ModelLane.ORCHESTRATOR,
    max_tokens=2000,
    json_mode=True,
)

# Use CODER for code analysis
response = generate_text(
    prompt="Analyze this code and suggest refactoring",
    project_id="proj-123",
    lane=ModelLane.CODER,
    temperature=0.2,
    max_tokens=1500,
)

# Use SUPER_READER for large document analysis
response = generate_text(
    prompt="Analyze this entire codebase",
    project_id="proj-123",
    lane=ModelLane.SUPER_READER,
    max_tokens=4000,
)

# Use FAST_RAG for RAG queries
response = generate_text(
    prompt="What did we discuss about API design?",
    project_id="proj-123",
    lane=ModelLane.FAST_RAG,
    temperature=0.7,
    max_tokens=1000,
)
```

### Service-Specific Guidelines

#### IngestService
- **Default:** No LLM calls (indexing only)
- **Deep Ingest (>50MB files):** Use `ModelLane.SUPER_READER` if adding LLM analysis

#### RepoService
- **Code Analysis:** Use `ModelLane.CODER`
- **Structure Analysis:** Use `ModelLane.CODER` for LLM-based analysis

#### RAGService
- **All RAG queries:** Use `ModelLane.FAST_RAG`
- **Query refinement:** Use `ModelLane.FAST_RAG`

#### GapAnalysisService
- **Gap notes generation:** Use `ModelLane.CODER`
- **Code-related analysis:** Use `ModelLane.CODER`

#### ProjectManagerGraph
- **Supervisor Agent:** Use `ModelLane.ORCHESTRATOR`
- **Planning tasks:** Use `ModelLane.ORCHESTRATOR`

#### RoadmapService
- **Roadmap generation:** Use `ModelLane.ORCHESTRATOR` (already implemented)

## Configuration

### Environment Variables

```bash
# Default / Orchestrator
ARGOS_LLM_BASE_URL=http://localhost:8000/v1
ARGOS_LLM_MODEL=Qwen3-30B-Thinking
ARGOS_LLM_DEFAULT_LANE=orchestrator

# Super-Reader (llama.cpp)
ARGOS_LANE_SUPER_READER_URL=http://localhost:8080/v1
ARGOS_LANE_SUPER_READER_MODEL=Nemotron-8B-UltraLong-4M
ARGOS_LANE_SUPER_READER_MODEL_PATH=/models/nemotron-4m.gguf
ARGOS_LANE_SUPER_READER_BACKEND=llama_cpp

# Coder (vLLM)
ARGOS_LANE_CODER_URL=http://localhost:8000/v1
ARGOS_LANE_CODER_MODEL=Qwen3-Coder-30B-1M

# Fast-RAG (vLLM)
ARGOS_LANE_FAST_RAG_URL=http://localhost:8000/v1
ARGOS_LANE_FAST_RAG_MODEL=MegaBeam-Mistral-7B-512k

# Governance (llama.cpp)
ARGOS_LANE_GOVERNANCE_URL=http://localhost:8080/v1
ARGOS_LANE_GOVERNANCE_MODEL=Granite-4.x-Long-Context
ARGOS_LANE_GOVERNANCE_MODEL_PATH=/models/granite-4m.gguf
ARGOS_LANE_GOVERNANCE_BACKEND=llama_cpp
```

## Fallback Behavior

If a lane is not configured, the system will:

1. **Check for lane-specific config** (`ARGOS_LANE_{LANE}_URL` and `ARGOS_LANE_{LANE}_MODEL`)
2. **Fall back to default lane** (`ARGOS_LLM_DEFAULT_LANE`, usually `orchestrator`)
3. **Use default config** (`ARGOS_LLM_BASE_URL` and `ARGOS_LLM_MODEL`)

This ensures the system always has a working configuration, even if specialized lanes aren't set up.

## Error Handling

### Missing Configuration

If a lane is requested but not configured:
- System logs a warning
- Falls back to default lane
- Request proceeds normally

### Service Unavailable

If a lane's endpoint is down:
- System logs an error
- Falls back to default lane
- Request may fail if default is also unavailable

### OOM (Out of Memory)

If a model runs out of memory:
- System logs an error
- Falls back to default lane (if different)
- Consider using burst mode (pause other services)

## Performance Considerations

### Latency Expectations

- **ORCHESTRATOR / CODER / FAST_RAG:** 30-50 tokens/sec (interactive)
- **SUPER_READER:** 2-5 tokens/sec (deep analysis, acceptable)
- **GOVERNANCE:** 10-20 tokens/sec (compliance checks)

### Memory Usage

- **vLLM Services (Port 8000):** ~48GB RAM
- **llama.cpp Services (Port 8080):** ~64GB RAM
- **Total:** ~112GB (leaving 16GB for OS)

### When to Use Each Lane

- **ORCHESTRATOR:** Planning, decision-making, complex reasoning
- **CODER:** Code analysis, refactoring, gap analysis
- **SUPER_READER:** Large documents (>1M tokens), monorepo analysis
- **FAST_RAG:** Quick knowledge queries, chat responses
- **GOVERNANCE:** Safety checks, compliance verification

## Testing

### Test Lane Configuration

```python
from app.services.llm_service import resolve_lane_config, ModelLane

# Check if a lane is configured
base_url, model_name, backend = resolve_lane_config(ModelLane.CODER)
print(f"CODER lane: {base_url} / {model_name} / {backend}")
```

### Test Lane Routing

```python
from app.services.llm_service import generate_text, ModelLane

# Test each lane
for lane in ModelLane:
    try:
        response = generate_text(
            prompt="Test",
            project_id="test-proj",
            lane=lane,
            max_tokens=10,
        )
        print(f"{lane.value}: OK")
    except Exception as e:
        print(f"{lane.value}: FAILED - {e}")
```

## Troubleshooting

### Issue: Wrong Lane Being Used

**Check:**
1. Is the lane parameter being passed correctly?
2. Is the lane configuration correct in environment variables?
3. Check logs for fallback warnings

### Issue: Slow Performance

**Check:**
1. Is the correct lane being used? (SUPER_READER is intentionally slower)
2. Is the model server running and healthy?
3. Check memory usage (may need burst mode)

### Issue: Configuration Not Working

**Check:**
1. Environment variables are set correctly
2. Settings are loaded (restart backend if needed)
3. Check `resolve_lane_config()` output in logs

## Related Documentation

- **Implementation Plan:** `docs/specs/IMPLEMENTATION_PLAN_MODEL_LANES.md`
- **Hardware Optimization:** `docs/specs/04-runtime-and-ops-strix-optimization.md`
- **Docker Compose:** `ops/docker-compose.strix.yml`

