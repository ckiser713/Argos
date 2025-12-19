# Model Download Status

## ✅ Successfully Downloaded

### Embedding Models
- `all-MiniLM-L6-v2` - General purpose embedding model (384d)
- `jinaai/jina-embeddings-v2-base-code` - Code-specific embedding model (768d)
- `microsoft/codebert-base` - Code-specific embedding model fallback (768d)

These are cached in the Hugging Face cache directory.

## ⚠️ Requires Manual Action

The following models require accepting licenses on Hugging Face and a valid token:

### vLLM Models (for `/models/vllm/`)
1. **Orchestrator**: `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B`
   - Target: `/models/vllm/orchestrator/bf16/`
   - Action: Visit https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B and accept license

2. **Coder**: `Qwen/Qwen2.5-Coder-32B-Instruct`
   - Target: `/models/vllm/coder/bf16/`
   - Action: Visit https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct and accept license

3. **Fast RAG**: `meta-llama/Llama-3.2-11B-Vision-Instruct`
   - Target: `/models/vllm/fast_rag/bf16/`
   - Action: Visit https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct and accept license

### GGUF Models (for `/models/gguf/`)
1. **Super Reader**: `Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf`
   - Source: `Mungert/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-GGUF`
   - Target: `/models/gguf/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf`
   - Action: Visit https://huggingface.co/Mungert/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-GGUF and accept license

2. **Governance**: `granite-3.0-8b-instruct-Q4_K_M.gguf`
   - Source: `bartowski/granite-3.0-8b-instruct-GGUF`
   - Target: `/models/gguf/granite-3.0-8b-instruct-Q4_K_M.gguf`
   - Action: Visit https://huggingface.co/bartowski/granite-3.0-8b-instruct-GGUF and accept license

## Steps to Complete Downloads

1. **Accept Model Licenses**:
   - Visit each model page listed above
   - Click "Agree and access repository"
   - Repeat for all 5 models

2. **Verify Token**:
   ```bash
   export HF_TOKEN=your_token_here
   poetry run huggingface-cli whoami
   ```

3. **Re-run Download Script**:
   ```bash
   cd /home/nexus/Argos_Chatgpt/backend
   export MODELS_DIR=/models
   poetry run python scripts/download_models.py
   ```

## Alternative: Manual Download

If automated download continues to fail, you can manually download models using:

```bash
# For vLLM models
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Qwen-32B --local-dir /models/vllm/orchestrator/bf16
huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct --local-dir /models/vllm/coder/bf16
huggingface-cli download meta-llama/Llama-3.2-11B-Vision-Instruct --local-dir /models/vllm/fast_rag/bf16

# For GGUF models
huggingface-cli download Mungert/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-GGUF --local-dir /models/gguf --include "*.gguf"
huggingface-cli download bartowski/granite-3.0-8b-instruct-GGUF --local-dir /models/gguf --include "*.gguf"
```

## Current Status

- ✅ Embedding models: Downloaded and cached
- ⚠️ vLLM models: Waiting for license acceptance
- ⚠️ GGUF models: Waiting for license acceptance
- ✅ Model directories: Created and ready (`/models/vllm/` and `/models/gguf/`)
