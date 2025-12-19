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

from backend.app.services.model_registry import get_model_registry

# Initialize logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to load HF_TOKEN from .env files (prioritize .env over environment)
# Get project root (parent of backend directory)
project_root = Path(__file__).parent.parent.parent
env_files = [
    project_root / ".env",  # Project root .env
    project_root / "backend" / ".env",  # Backend .env
    Path("/etc/llama/llama.env"),  # System llama env
    Path("/var/lib/llama/.env"),
    Path("/var/lib/llama/llama.env"),
    Path.home() / ".env",
]

env_token_loaded = False
for env_file in env_files:
    if env_file.exists():
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("HF_TOKEN=") and not line.startswith("#"):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if token:
                            os.environ["HF_TOKEN"] = token
                            logger.info(f"Loaded HF_TOKEN from {env_file}")
                            env_token_loaded = True
                            break
            if env_token_loaded:
                break
        except (PermissionError, IOError) as e:
            logger.debug(f"Could not read {env_file}: {e}")
            continue

# If no token found in .env files and environment doesn't have one, warn user
if not os.getenv("HF_TOKEN"):
    logger.warning("No HF_TOKEN found in environment or .env files!")
    logger.warning("Please set HF_TOKEN in your .env file or environment variable.")
    logger.warning("Get a token from: https://huggingface.co/settings/tokens")


def get_models_dir():
    """Get the base directory for storing models."""
    return Path(os.getenv("MODELS_DIR", Path.cwd() / "models"))


def hf_download(repo_id, target_dir, revision=None, filename=None):
    """Wrapper for Hugging Face download functions with resumable downloads."""
    base_args = {
        "repo_id": repo_id,
        "local_dir": str(target_dir),
        "local_dir_use_symlinks": False,
        "token": os.getenv("HF_TOKEN"),
        "revision": revision,
        "resume_download": True,  # Enable resumable downloads
    }
    if filename:
        # hf_hub_download doesn't support max_workers
        hf_hub_download(filename=filename, **base_args)
    else:
        # snapshot_download supports max_workers for parallel downloads
        snapshot_download(**base_args, max_workers=4)


def download_vllm_models(base_dir: Path, skip: bool):
    """Download models for the vLLM engine using HuggingFace CLI (hf) for better reliability."""
    if skip:
        logger.info("Skipping vLLM models.")
        return
    logger.info("--- Downloading vLLM Models ---")
    vllm_dir = base_dir / "vllm"

    registry = get_model_registry()
    for lane, config in registry.vllm.items():
        logger.info(f"Processing lane: {lane} ({config.model_name})")
        for fmt, repo in config.repos.items():
            revision = None
            target_dir = vllm_dir / lane / fmt
            logger.info(f"  Downloading format: {fmt.upper()} from {repo}")

            # Check if model is actually complete (has safetensors or bin files)
            if target_dir.exists():
                has_model_files = any(
                    f.suffix in [".safetensors", ".bin"] for f in target_dir.rglob("*")
                )
                if has_model_files:
                    logger.info(f"  ✓ Already exists at {target_dir}, skipping.")
                    continue
                else:
                    logger.info(f"  ⚠ Incomplete download detected at {target_dir}, re-downloading...")
                    # Remove incomplete directory
                    import shutil
                    shutil.rmtree(target_dir, ignore_errors=True)
            
            # Use huggingface-cli for more reliable large file downloads
            try:
                import subprocess
                target_dir.mkdir(parents=True, exist_ok=True)
                cmd = [
                    "huggingface-cli",
                    "download",
                    repo,
                    "--local-dir", str(target_dir),
                    "--local-dir-use-symlinks", "False",
                ]
                if revision:
                    cmd.extend(["--revision", revision])

                # Set up environment with HF_TOKEN
                env = os.environ.copy()
                if os.getenv("HF_TOKEN"):
                    env["HF_TOKEN"] = os.getenv("HF_TOKEN")

                logger.info(f"  Running: {' '.join(cmd[:3])}...")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout per model
                    env=env,  # Pass environment explicitly
                )
                if result.returncode == 0:
                    logger.info(f"  ✓ Successfully downloaded to {target_dir}")
                else:
                    raise Exception(f"hf download failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"  ✗ Download timeout for {repo}")
            except FileNotFoundError:
                # Fallback to Python API if hf not available
                logger.info("  hf not found, using Python API...")
                try:
                    hf_download(repo, target_dir, revision=revision)
                    logger.info(f"  ✓ Successfully downloaded to {target_dir}")
                except Exception as e:
                    logger.warning(f"  ✗ Failed to download {repo} (format: {fmt}): {e}")
                    if fmt == "fp8":
                        logger.info("    FP8 variant may not be available. This can be expected.")
                    else:
                        logger.error(f"    Critical download failure for base model: {repo}")
            except Exception as e:
                logger.warning(f"  ✗ Failed to download {repo} (format: {fmt}): {e}")
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

    registry = get_model_registry()
    for lane, config in registry.gguf.items():
        logger.info(f"Processing lane: {lane} ({config.model_name})")
        repo = config.repo
        filename = config.filename
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
    registry = get_model_registry()
    models_to_download = (
        {"general_purpose": registry.embedding.get("general_purpose", "")}
        if is_minimal
        else registry.embedding
    )

    for label, repo in models_to_download.items():
        if not repo:
            continue
        logger.info(f"Processing model: {repo} ({label})")
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
