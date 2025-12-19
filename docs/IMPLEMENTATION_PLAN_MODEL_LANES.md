# Implementation Plan: Backend Model Routing & Lanes

## Overview

This document outlines the implementation plan for extending Cortex's `LLMService` to support **Model Lanes**, transitioning from a single-model system to a multi-model orchestration engine. The implementation maps specific "Intents" (Planning, Coding, Deep Reading) to specialized models defined in the Argos/NexusJR Catalog.

## Current State Analysis

### ✅ Already Implemented
1. **ModelLane Enum**: Defined in `backend/app/services/llm_service.py` with all required lanes:
   - `ORCHESTRATOR`, `CODER`, `SUPER_READER`, `FAST_RAG`, `GOVERNANCE`
2. **Lane Configuration**: Settings structure exists in `backend/app/config.py` with lane-specific URLs and models
3. **Basic Routing**: `resolve_lane_config()` function exists with fallback logic
4. **generate_text()**: Already accepts `lane` parameter (defaults to `ORCHESTRATOR`)
5. **roadmap_service.py**: Already uses `ModelLane.ORCHESTRATOR` explicitly

### ❌ Missing/Incomplete
1. **Service Integration**: Most services don't specify lanes when calling `generate_text()`
2. **Fallback Logic**: Needs improvement for graceful degradation
3. **Configuration**: Missing some lane-specific model paths for llama.cpp
4. **Deep Ingest Detection**: IngestService doesn't detect large files and route to SUPER_READER
5. **Documentation**: Hardware optimization spec doesn't exist
6. **Docker Compose**: No Strix Halo-specific deployment configuration

## Implementation Tasks

### Phase 1: Core Service Updates

#### Task 1.1: Enhance LLMService Lane Resolution
**File**: `backend/app/services/llm_service.py`

**Changes**:
- Improve `resolve_lane_config()` to handle missing configurations more gracefully
- Add health checking for lane endpoints (optional, can be added later)
- Enhance error messages to indicate which lane failed and why
- Add support for detecting OOM errors and triggering fallback

**Implementation Details**:
```python
def resolve_lane_config(lane: ModelLane) -> tuple[str, str, str]:
    """
    Resolve base_url, model_name, and backend for the given lane.
    
    Returns (base_url, model_name, backend)
    Raises ValueError if no configuration found and fallback fails
    """
    lane_name = lane.value.upper()
    
    # Check for lane-specific config
    base_url_attr = f"lane_{lane.value}_url"
    model_attr = f"lane_{lane.value}_model"
    
    base_url = getattr(settings, base_url_attr, "")
    model_name = getattr(settings, model_attr, "")
    
    if base_url and model_name:
        # Determine backend based on URL or explicit config
        backend_attr = f"lane_{lane.value}_backend"
        backend = getattr(settings, backend_attr, "")
        
        if not backend:
            # Auto-detect backend from URL
            if "8080" in base_url or lane == ModelLane.SUPER_READER:
                backend = "llama_cpp"
            else:
                backend = "openai"
        
        return base_url, model_name, backend
    
    # Fallback to default lane
    fallback_lane_name = settings.llm_default_lane
    try:
        fallback_lane = ModelLane(fallback_lane_name)
    except ValueError:
        fallback_lane = ModelLane.ORCHESTRATOR
    
    if fallback_lane == lane:
        # Already at fallback, use default config
        return settings.llm_base_url, settings.llm_model_name, settings.llm_backend
    
    # Recursive fallback
    logger.warning(
        f"Lane {lane.value} not configured, falling back to {fallback_lane.value}",
        extra={"lane": lane.value, "fallback": fallback_lane.value}
    )
    return resolve_lane_config(fallback_lane)
```

#### Task 1.2: Update IngestService for Deep Ingest
**File**: `backend/app/services/ingest_service.py`

**Changes**:
- Detect large file uploads (>50MB or >1M tokens estimated)
- Route "Deep Ingest" operations to `ModelLane.SUPER_READER`
- Add method `_should_use_deep_ingest()` to determine routing

**Implementation Details**:
```python
from app.services.llm_service import generate_text, ModelLane

def _should_use_deep_ingest(self, file_path: str) -> bool:
    """Determine if file requires deep ingest (SUPER_READER lane)."""
    import os
    if not os.path.exists(file_path):
        return False
    
    # Check file size (>50MB suggests large content)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 50:
        return True
    
    # Check if it's a repository (always use deep ingest for repos)
    if self._is_repository(file_path):
        return True
    
    return False

# In process_job method, add:
if self._should_use_deep_ingest(file_path):
    # Use SUPER_READER for deep analysis
    # This would be used if we add LLM-based analysis during ingest
    logger.info(f"Using SUPER_READER lane for deep ingest of {file_path}")
```

**Note**: Currently, `process_job` doesn't call `generate_text` directly. This change prepares for future LLM-based analysis during ingest. For now, we'll add the detection logic.

#### Task 1.3: Update RepoService for Code Analysis
**File**: `backend/app/services/repo_service.py`

**Changes**:
- Add method `analyze_code_with_llm()` that uses `ModelLane.CODER`
- Update `analyze_repo_structure()` to optionally use LLM analysis
- Ensure code analysis tasks route to CODER lane

**Implementation Details**:
```python
from app.services.llm_service import generate_text, ModelLane

def analyze_code_with_llm(self, project_id: str, code_content: str, file_path: str) -> dict:
    """
    Analyze code using the CODER lane LLM.
    
    Args:
        project_id: Project ID
        code_content: Code to analyze
        file_path: Path to the code file
        
    Returns:
        Dictionary with analysis results
    """
    prompt = f"""Analyze the following code file and provide:
1. Code quality assessment
2. Potential refactoring suggestions
3. Security concerns
4. Performance optimizations

File: {file_path}
Code:
```python
{code_content}
```"""
    
    response = generate_text(
        prompt=prompt,
        project_id=project_id,
        lane=ModelLane.CODER,
        temperature=0.2,
        max_tokens=2000,
        json_mode=True,
    )
    
    # Parse JSON response
    import json
    return json.loads(response)
```

#### Task 1.4: Update RAGService for Fast RAG
**File**: `backend/app/services/rag_service.py`

**Changes**:
- Update all `generate_text()` calls to use `ModelLane.FAST_RAG`
- Ensure RAG synthesis queries use the appropriate lane

**Implementation Details**:
```python
from app.services.llm_service import generate_text, ModelLane

# Update existing calls:
response = generate_text(
    prompt=prompt,
    project_id=project_id,
    lane=ModelLane.FAST_RAG,  # Add this parameter
    temperature=0.7,
    max_tokens=max_tokens,
)
```

#### Task 1.5: Update GapAnalysisService
**File**: `backend/app/services/gap_analysis_service.py`

**Changes**:
- Update `LLMCoderClient.generate_gap_notes()` to use `ModelLane.CODER`
- Ensure code-related analysis uses CODER lane

**Implementation Details**:
```python
# In LLMCoderClient class:
def generate_gap_notes(self, ticket, code_chunks, status):
    # ... existing code ...
    response = llm_service.generate_text(
        prompt=prompt,
        project_id=ticket.project_id,
        lane=ModelLane.CODER,  # Add this parameter
        temperature=0.2,
        max_tokens=1500,
    )
```

#### Task 1.6: Update ProjectManagerGraph
**File**: `backend/app/graphs/project_manager_graph.py`

**Changes**:
- Ensure the LangChain model initialization uses ORCHESTRATOR lane configuration
- Add explicit lane configuration in model initialization

**Implementation Details**:
```python
# Update model initialization to use ORCHESTRATOR lane config
settings = get_settings()

# Get orchestrator lane config
from app.services.llm_service import resolve_lane_config, ModelLane
base_url, model_name, backend = resolve_lane_config(ModelLane.ORCHESTRATOR)

try:
    llm = init_chat_model(
        model=model_name or settings.llm_model_name,
        model_provider="openai",
        api_key=settings.llm_api_key,
        base_url=base_url or settings.llm_base_url,
        temperature=0,
        streaming=True,
    )
    model = llm.bind_tools(tools)
except Exception:
    # Fallback logic...
```

### Phase 2: Configuration Enhancements

#### Task 2.1: Add Missing Lane Configuration
**File**: `backend/app/config.py`

**Changes**:
- Add missing `lane_super_reader_model_path` (already exists but verify)
- Add `lane_coder_model_path` for llama.cpp fallback
- Add `lane_governance_model_path` (already exists)
- Add backend selection per lane (optional)

**Implementation Details**:
```python
# Verify these exist (they should based on current code):
lane_super_reader_model_path: str = Field(default="", env="ARGOS_LANE_SUPER_READER_MODEL_PATH")
lane_coder_model_path: str = Field(default="", env="ARGOS_LANE_CODER_MODEL_PATH")
lane_governance_model_path: str = Field(default="", env="ARGOS_LANE_GOVERNANCE_MODEL_PATH")

# Optional: Add per-lane backend selection
lane_orchestrator_backend: str = Field(default="vllm", env="ARGOS_LANE_ORCHESTRATOR_BACKEND")
lane_coder_backend: str = Field(default="vllm", env="ARGOS_LANE_CODER_BACKEND")
lane_super_reader_backend: str = Field(default="llama_cpp", env="ARGOS_LANE_SUPER_READER_BACKEND")
lane_fast_rag_backend: str = Field(default="vllm", env="ARGOS_LANE_FAST_RAG_BACKEND")
lane_governance_backend: str = Field(default="llama_cpp", env="ARGOS_LANE_GOVERNANCE_BACKEND")
```

### Phase 3: Documentation

#### Task 3.1: Create Hardware Optimization Spec
**File**: `docs/specs/04-runtime-and-ops-strix-optimization.md`

**Content**: See specification provided in user requirements. This will document:
- Memory partitioning strategy (128GB RAM)
- Container strategy (vLLM vs llama.cpp)
- Memory map breakdown
- Docker Compose configuration
- Operational workflows

#### Task 3.2: Create Docker Compose Override
**File**: `ops/docker-compose.strix.yml`

**Content**: Docker Compose override file for Strix Halo deployment with:
- `inference-vllm` service (The Fast Lane)
- `inference-llamacpp` service (The Deep Lane)
- Memory constraints and device mappings
- Port configurations

### Phase 4: Error Handling & Resilience

#### Task 4.1: Add Lane Health Checking (Optional)
**File**: `backend/app/services/llm_service.py`

**Changes**:
- Add optional health check endpoint verification
- Cache health status to avoid per-request checks
- Implement circuit breaker pattern for failed lanes

**Note**: This is optional and can be added in a future iteration.

#### Task 4.2: Improve Error Messages
**File**: `backend/app/services/llm_service.py`

**Changes**:
- Add detailed error logging with lane information
- Include fallback chain in error messages
- Log configuration issues clearly

## Configuration Parameters Reference

### Environment Variables

```bash
# Default / Orchestrator (vLLM Port 8000)
ARGOS_LLM_BASE_URL=http://localhost:8000/v1
ARGOS_LLM_MODEL=DeepSeek-R1-Distill-Qwen-32B
ARGOS_LLM_DEFAULT_LANE=orchestrator

# Super-Reader (llama.cpp Port 8080)
ARGOS_LANE_SUPER_READER_URL=http://localhost:8080/v1
ARGOS_LANE_SUPER_READER_MODEL=Nemotron-8B-UltraLong-4M
ARGOS_LANE_SUPER_READER_MODEL_PATH=/models/nemotron-4m.gguf
ARGOS_LANE_SUPER_READER_BACKEND=llama_cpp

# Coder (vLLM Port 8000)
ARGOS_LANE_CODER_URL=http://localhost:8000/v1
ARGOS_LANE_CODER_MODEL=Qwen2.5-Coder-32B-Instruct

# Fast-RAG (vLLM Port 8000)
ARGOS_LANE_FAST_RAG_URL=http://localhost:8000/v1
ARGOS_LANE_FAST_RAG_MODEL=Llama-3.2-11B-Vision-Instruct

# Governance (llama.cpp Port 8080)
ARGOS_LANE_GOVERNANCE_URL=http://localhost:8080/v1
ARGOS_LANE_GOVERNANCE_MODEL=granite-3.0-8b-instruct
ARGOS_LANE_GOVERNANCE_MODEL_PATH=/models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf
ARGOS_LANE_GOVERNANCE_BACKEND=llama_cpp
```

## Testing Strategy

### Unit Tests
1. Test `resolve_lane_config()` with various configurations
2. Test fallback logic when lanes are missing
3. Test error handling for invalid configurations

### Integration Tests
1. Test service routing to correct lanes
2. Test fallback behavior when a lane is unavailable
3. Test IngestService deep ingest detection

### Manual Testing
1. Verify each service routes to correct lane
2. Test with missing lane configurations (fallback)
3. Test with Strix Halo hardware setup

## Risks & Mitigations

### Risk 1: VRAM Contention
**Mitigation**: 
- Strict memory partitioning (48GB vLLM, 64GB llama.cpp)
- Burst mode: pause vLLM when running 4M token ingest
- Monitor memory usage and implement OOM detection

### Risk 2: Latency from Model Switching
**Mitigation**:
- Use model servers (vLLM) that support multi-model serving
- Keep models loaded in memory
- Implement request queuing for lane switching

### Risk 3: Configuration Complexity
**Mitigation**:
- Provide clear documentation
- Sensible defaults (fallback to ORCHESTRATOR)
- Validation on startup with clear error messages

## Implementation Order

1. **Phase 1.1**: Enhance LLMService lane resolution (foundation)
2. **Phase 1.2-1.6**: Update all services to use appropriate lanes
3. **Phase 2.1**: Add missing configuration options
4. **Phase 3.1-3.2**: Create documentation and Docker Compose
5. **Phase 4**: Add error handling improvements

## Success Criteria

- ✅ All services route to appropriate lanes
- ✅ Fallback logic works when lanes are unavailable
- ✅ Configuration is clear and well-documented
- ✅ Hardware optimization spec exists
- ✅ Docker Compose override for Strix Halo exists
- ✅ Error messages are helpful and actionable
