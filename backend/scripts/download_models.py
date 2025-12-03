#!/usr/bin/env python3
"""
Script to download and cache Hugging Face models for Cortex.
"""
import logging
import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download
from sentence_transformers import SentenceTransformer

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Model Configuration ---

# Defines all models required by the Cortex application
MODEL_CONFIG = {
    "vllm": {
        "orchestrator": {
            "description": "ORCHESTRATOR Lane - DeepSeek-R1 Reasoning Model",
            "formats": {
                "bf16": {"repo": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"},
                "fp8": {"repo": "neuralmagic/DeepSeek-R1-Distill-Qwen-32B-fp8"},
            },
        },
        "coder": {
            "description": "CODER Lane - Qwen Coder Model",
            "formats": {
                "bf16": {"repo": "Qwen/Qwen2.5-Coder-32B-Instruct"},
                "fp8": {"repo": "neuralmagic/Qwen2.5-Coder-32B-Instruct-fp8"},
            },
        },
        "fast_rag": {
            "description": "FAST_RAG Lane - Llama 3.2 Vision Model",
            "formats": {
                "bf16": {"repo": "meta-llama/Llama-3.2-11B-Vision-Instruct"}
            },
        },
    },
    "gguf": {
        "super_reader": {
            "description": "SUPER_READER Lane - Nemotron UltraLong 4M",
            "repo": "Mungert/Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-GGUF",
            "filename": "Llama-3.1-Nemotron-8B-UltraLong-4M-Instruct-q4_k_m.gguf",
        },
        "governance": {
            "description": "GOVERNANCE Lane - Granite 3.0 Instruct",
            "repo": "bartowski/granite-3.0-8b-instruct-GGUF",
            "filename": "granite-3.0-8b-instruct-Q4_K_M.gguf",
        },
    },
    "embedding": {
        "general_purpose": {
            "description": "General purpose embedding model (384d)",
            "repo": "all-MiniLM-L6-v2",
        },
        "code_search": {
            "description": "Code-specific embedding model (768d)",
            "repo": "jinaai/jina-embeddings-v2-base-code",
        },
        "code_search_fallback": {
            "description": "Code-specific embedding model fallback (768d)",
            "repo": "microsoft/codebert-base",
        },
    },
}


def get_models_dir():
    """Get the base directory for storing models."""
    return Path(os.getenv("MODELS_DIR", Path.cwd() / "models"))


def hf_download(repo_id, target_dir, revision=None, filename=None):
    """Wrapper for Hugging Face download functions."""
    common_args = {
        "repo_id": repo_id,
        "local_dir": str(target_dir),
        "local_dir_use_symlinks": False,
        "token": os.getenv("HF_TOKEN"),
        "revision": revision,
    }
    if filename:
        hf_hub_download(filename=filename, **common_args)
    else:
        snapshot_download(**common_args)


def download_vllm_models(base_dir: Path, skip: bool):
    """Download models for the vLLM engine."""
    if skip:
        logger.info("Skipping vLLM models.")
        return
    logger.info("--- Downloading vLLM Models ---")
    vllm_dir = base_dir / "vllm"

    for lane, config in MODEL_CONFIG["vllm"].items():
        logger.info(f"Processing lane: {lane} ({config['description']})")
        for fmt, fmt_config in config["formats"].items():
            repo = fmt_config["repo"]
            revision = fmt_config.get("revision")
            target_dir = vllm_dir / lane / fmt
            logger.info(f"  Downloading format: {fmt.upper()} from {repo}")

            if target_dir.exists() and any(target_dir.iterdir()):
                logger.info(f"  ✓ Already exists at {target_dir}, skipping.")
                continue
            try:
                hf_download(repo, target_dir, revision=revision)
                logger.info(f"  ✓ Successfully downloaded to {target_dir}")
            except Exception as e:
                logger.warning(
                    f"  ✗ Failed to download {repo} (format: {fmt}): {e}"
                )
                if fmt == "fp8":
                    logger.info("    FP8 variant may not be available. This can be expected.")
                else:
                    logger.error(f"    Critical download failure for base model: {repo}")

def download_gguf_models(base_dir: Path, skip: bool):
    """Download GGUF models."""
    if skip:
        logger.info("Skipping GGUF models.")
        return
    logger.info("--- Downloading GGUF Models ---")
    gguf_dir = base_dir / "gguf"
    gguf_dir.mkdir(parents=True, exist_ok=True)

    for lane, config in MODEL_CONFIG["gguf"].items():
        logger.info(f"Processing lane: {lane} ({config['description']})")
        repo = config["repo"]
        filename = config["filename"]
        target_file = gguf_dir / filename

        if target_file.exists():
            logger.info(f"  ✓ Already exists at {target_file}, skipping.")
            continue
        try:
            logger.info(f"  Downloading {filename} from {repo}")
            hf_download(repo, gguf_dir, filename=filename)
            logger.info(f"  ✓ Successfully downloaded to {target_file}")
        except Exception as e:
            logger.warning(f"  ✗ Failed to download {filename} from {repo}: {e}")

def download_embedding_models(base_dir: Path, skip: bool):
    """Download sentence transformer models."""
    if skip:
        logger.info("Skipping embedding models.")
        return
    logger.info("--- Downloading Embedding Models ---")
    # SentenceTransformers handles its own caching, so we don't need a specific dir
    
    is_minimal = os.getenv("MINIMAL_EMBEDDINGS", "false").lower() == "true"
    models_to_download = (
        [MODEL_CONFIG["embedding"]["general_purpose"]]
        if is_minimal
        else list(MODEL_CONFIG["embedding"].values())
    )

    for model_config in models_to_download:
        repo = model_config["repo"]
        logger.info(f"Processing model: {repo} ({model_config['description']})")
        try:
            # SentenceTransformer downloads and caches the model upon initialization
            SentenceTransformer(repo)
            logger.info(f"  ✓ Successfully downloaded and cached {repo}")
        except Exception as e:
            logger.warning(f"  ✗ Failed to download or cache {repo}: {e}")

def main():
    """Main function to orchestrate model downloads."""
    logger.info("========================================")
    logger.info("   Cortex Model Lanes - Model Manager   ")
    logger.info("========================================")

    models_dir = get_models_dir()
    logger.info(f"Target models directory: {models_dir}\n")

    # Check environment variables to skip categories
    skip_vllm = os.getenv("SKIP_VLLM", "false").lower() == "true"
    skip_gguf = os.getenv("SKIP_GGUF", "false").lower() == "true"
    skip_embeddings = os.getenv("SKIP_EMBEDDINGS", "false").lower() == "true"

    download_vllm_models(models_dir, skip_vllm)
    print("")
    download_gguf_models(models_dir, skip_gguf)
    print("")
    download_embedding_models(models_dir, skip_embeddings)
    print("")

    logger.info("========================================")
    logger.info("      Model Download Process Finished      ")
    logger.info("========================================")
    logger.info(f"All models are stored in or cached relative to: {models_dir}")


if __name__ == "__main__":
    main()