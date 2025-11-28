#!/usr/bin/env python3
"""
Script to download and cache Hugging Face models used by Cortex.
This ensures models are available locally before runtime.
"""

import logging
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_embedding_model():
    """Download the sentence transformer models used for embeddings."""
    minimal_mode = os.getenv(
        "CORTEX_DOWNLOAD_EMBEDDINGS_MINIMAL", "").lower() in ("true", "1", "yes")

    if minimal_mode:
        # Only download the essential general-purpose model
        models = [
            ("all-MiniLM-L6-v2", "General purpose (384d) - essential"),
        ]
        logger.info("Minimal mode: downloading only essential embedding model")
    else:
        # Primary models in order of preference
        models = [
            ("all-MiniLM-L6-v2", "General purpose (384d) - always needed"),
            ("jinaai/jina-embeddings-v2-base-code",
             "Code-specific (768d) - for code search"),
            ("microsoft/codebert-base", "Code-specific (768d) - code search fallback"),
        ]

    success_count = 0
    for model_name, description in models:
        logger.info(
            f"Downloading embedding model: {model_name} - {description}")

        try:
            # This will download and cache the model
            model = SentenceTransformer(model_name)
            # Force loading by encoding a test string
            test_embedding = model.encode("test")
            logger.info(f"Successfully downloaded and cached {model_name}")
            success_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to download embedding model {model_name}: {e}")

    return success_count > 0


def download_gguf_model(model_repo: str, local_dir: str = None):
    """Download a GGUF model from Hugging Face."""
    if not local_dir:
        local_dir = Path.home() / "cortex_models" / model_repo.replace("/", "_")

    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading GGUF model from {model_repo} to {local_dir}")

    try:
        # Download the entire repo (will include GGUF files)
        snapshot_download(
            repo_id=model_repo,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
            allow_patterns=["*.gguf", "*.bin"]  # Only download model files
        )
        logger.info(f"Successfully downloaded model to {local_dir}")
        return str(local_dir)
    except Exception as e:
        logger.error(f"Failed to download model from {model_repo}: {e}")
        return None


def download_lane_gguf_models(models_base_dir: str = None):
    """
    Download GGUF models for specific lanes.

    Args:
        models_base_dir: Base directory for models (default: ~/cortex_models or ./models)
    """
    if models_base_dir is None:
        # Check for environment variable or use default
        models_base_dir = os.getenv(
            "CORTEX_MODELS_DIR", os.path.join(os.getcwd(), "models", "gguf"))

    models_base_dir = Path(models_base_dir)
    models_base_dir.mkdir(parents=True, exist_ok=True)

    lane_models = {
        "super_reader": {
            "repo": "nvidia/Nemotron-8B-Instruct",
            "filename": "nemotron-8b-instruct.Q4_K_M.gguf",  # Adjust based on actual file
            "env_var": "CORTEX_DOWNLOAD_SUPER_READER",
            "description": "Super Reader lane model (Nemotron UltraLong 4M)"
        },
        "governance": {
            "repo": "ibm-granite/granite-8b-instruct",
            "filename": "granite-8b-instruct.Q4_K_M.gguf",  # Adjust based on actual file
            "env_var": "CORTEX_DOWNLOAD_GOVERNANCE",
            "description": "Governance lane model (Granite Long Context)"
        }
    }

    downloaded_paths = {}

    for lane, config in lane_models.items():
        if os.getenv(config["env_var"], "").lower() in ("true", "1", "yes"):
            logger.info(
                f"Downloading {config['description']} ({lane}) from {config['repo']}")

            # Try to download specific GGUF file
            try:
                from huggingface_hub import hf_hub_download

                local_file = models_base_dir / config["filename"]

                if local_file.exists():
                    logger.info(
                        f"Model already exists at {local_file}, skipping download")
                    downloaded_paths[lane] = str(local_file)
                else:
                    logger.info(
                        f"Downloading {config['filename']} to {models_base_dir}")
                    downloaded_file = hf_hub_download(
                        repo_id=config["repo"],
                        filename=config["filename"],
                        local_dir=str(models_base_dir),
                        local_dir_use_symlinks=False,
                        token=os.getenv("HF_TOKEN"),
                    )
                    downloaded_paths[lane] = downloaded_file
                    logger.info(
                        f"Successfully downloaded to {downloaded_file}")

                # Print environment variable for user
                env_var = f"CORTEX_LANE_{lane.upper()}_MODEL_PATH"
                logger.info(
                    f"Set {env_var}={downloaded_paths[lane]} for {lane} lane")
                print(f"export {env_var}='{downloaded_paths[lane]}'")

            except Exception as e:
                logger.warning(
                    f"Failed to download {config['filename']}, trying full repo download: {e}")
                # Fallback to full repo download
                path = download_gguf_model(
                    config["repo"], str(models_base_dir / lane))
                if path:
                    downloaded_paths[lane] = path

    return downloaded_paths


def download_vllm_models(models_base_dir: str = None):
    """
    Download vLLM-compatible models for ORCHESTRATOR, CODER, and FAST_RAG lanes.

    Args:
        models_base_dir: Base directory for models
    """
    if models_base_dir is None:
        models_base_dir = os.getenv(
            "CORTEX_MODELS_DIR", os.path.join(os.getcwd(), "models", "vllm"))

    models_base_dir = Path(models_base_dir)
    models_base_dir.mkdir(parents=True, exist_ok=True)

    vllm_models = {
        "orchestrator": {
            "repo": "Qwen/Qwen2.5-32B-Instruct",  # Adjust to actual Qwen3-30B-Thinking model
            "description": "ORCHESTRATOR Lane - Qwen Thinking Model"
        },
        "coder": {
            # Adjust to actual Qwen3-Coder-30B model
            "repo": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "description": "CODER Lane - Qwen Coder Model"
        },
        "fast_rag": {
            # Adjust to actual MegaBeam-Mistral model
            "repo": "mistralai/Mistral-7B-Instruct-v0.2",
            "description": "FAST_RAG Lane - Mistral Model"
        }
    }

    downloaded_paths = {}

    for lane, config in vllm_models.items():
        if os.getenv(f"CORTEX_DOWNLOAD_{lane.upper()}", "").lower() in ("true", "1", "yes"):
            logger.info(f"Downloading {config['description']} ({lane})")
            local_dir = models_base_dir / lane
            path = download_gguf_model(config["repo"], str(local_dir))
            if path:
                downloaded_paths[lane] = path
                logger.info(f"Downloaded {lane} model to {path}")

    return downloaded_paths


def main():
    """Main function to download all required models."""
    logger.info("Starting model download process...")
    logger.info("Models will be stored outside containers for persistent reuse")

    # Get models directory from environment or use default
    models_base_dir = os.getenv(
        "CORTEX_MODELS_DIR", os.path.join(os.getcwd(), "models"))
    logger.info(f"Models base directory: {models_base_dir}")

    # Download embedding models
    embedding_success = download_embedding_model()

    # Download vLLM models (if requested)
    vllm_paths = {}
    if os.getenv("CORTEX_DOWNLOAD_VLLM", "").lower() in ("true", "1", "yes"):
        vllm_paths = download_vllm_models(
            os.path.join(models_base_dir, "vllm"))

    # Download lane-specific GGUF models
    gguf_base_dir = os.path.join(models_base_dir, "gguf")
    lane_paths = download_lane_gguf_models(gguf_base_dir)

    # Optionally download a default GGUF model if specified
    gguf_repo = os.getenv("CORTEX_DEFAULT_GGUF_REPO")
    if gguf_repo:
        gguf_path = download_gguf_model(gguf_repo, gguf_base_dir)
        if gguf_path:
            logger.info(
                f"Set CORTEX_LLAMA_CPP_MODEL_PATH to {gguf_path} for the downloaded model")
    else:
        logger.info(
            "No default GGUF model repo specified. Set CORTEX_DEFAULT_GGUF_REPO to download a default model.")

    # Summary
    logger.info("=" * 60)
    if embedding_success:
        logger.info("✓ Embedding model downloads completed successfully!")
    else:
        logger.warning("⚠ Some embedding model downloads failed.")

    if vllm_paths:
        logger.info(
            f"✓ Downloaded {len(vllm_paths)} vLLM models: {list(vllm_paths.keys())}")

    if lane_paths:
        logger.info(
            f"✓ Downloaded {len(lane_paths)} GGUF lane models: {list(lane_paths.keys())}")
        logger.info("Lane models stored outside Docker for persistent reuse")
    else:
        logger.info("No lane models were requested for download")
        logger.info(
            "Set CORTEX_DOWNLOAD_SUPER_READER=true and CORTEX_DOWNLOAD_GOVERNANCE=true to download")

    logger.info("=" * 60)
    logger.info(f"All models stored in: {models_base_dir}")
    logger.info("Update docker-compose volumes to mount this directory")

    success = embedding_success or bool(lane_paths) or bool(vllm_paths)
    if success:
        logger.info("Model download process completed!")
        return 0
    else:
        logger.error("No models were successfully downloaded.")
        logger.info("Set environment variables to enable downloads:")
        logger.info("  CORTEX_DOWNLOAD_SUPER_READER=true")
        logger.info("  CORTEX_DOWNLOAD_GOVERNANCE=true")
        logger.info("  CORTEX_DOWNLOAD_VLLM=true")
        return 1


if __name__ == "__main__":
    sys.exit(main())
