#!/usr/bin/env python3
"""
Script to verify all required AI models are downloaded for Cortex.
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_models_dir():
    """Get the base directory for storing models."""
    return Path(os.getenv("MODELS_DIR", Path.cwd() / "models"))


def verify_vllm_models(base_dir: Path) -> dict:
    """Verify vLLM models are downloaded."""
    results = {"found": [], "missing": []}
    vllm_dir = base_dir / "vllm"
    
    logger.info("--- Verifying vLLM Models ---")
    registry = get_model_registry()
    for lane, config in registry.vllm.items():
        logger.info(f"Checking lane: {lane} ({config.model_name})")
        lane_found = False
        
        for fmt in config.repos.keys():
            target_dir = vllm_dir / lane / fmt
            
            # Check if directory exists and has content
            if target_dir.exists() and any(target_dir.iterdir()):
                # Check for key files (config.json, model files)
                has_config = (target_dir / "config.json").exists()
                has_model_files = any(
                    f.suffix in [".safetensors", ".bin", ".pt", ".pth"]
                    for f in target_dir.rglob("*")
                    if f.is_file()
                )
                
                if has_config or has_model_files:
                    logger.info(f"  ✓ {fmt.upper()} format found at {target_dir}")
                    results["found"].append(f"{lane}/{fmt}")
                    lane_found = True
                else:
                    logger.warning(f"  ⚠ {fmt.upper()} directory exists but appears incomplete")
            else:
                logger.debug(f"  - {fmt.upper()} format not found at {target_dir}")
        
        if not lane_found:
            logger.warning(f"  ✗ No formats found for {lane}")
            results["missing"].append(lane)
    
    return results


def verify_gguf_models(base_dir: Path) -> dict:
    """Verify GGUF models are downloaded."""
    results = {"found": [], "missing": []}
    gguf_dir = base_dir / "gguf"
    
    logger.info("--- Verifying GGUF Models ---")
    registry = get_model_registry()
    for lane, config in registry.gguf.items():
        logger.info(f"Checking lane: {lane} ({config.model_name})")
        filename = config.filename
        target_file = gguf_dir / filename
        
        if target_file.exists() and target_file.stat().st_size > 0:
            size_mb = target_file.stat().st_size / (1024 * 1024)
            logger.info(f"  ✓ Found {filename} ({size_mb:.1f} MB)")
            results["found"].append(lane)
        else:
            logger.warning(f"  ✗ Missing {filename}")
            results["missing"].append(lane)
    
    return results


def verify_embedding_models() -> dict:
    """Verify embedding models are cached."""
    results = {"found": [], "missing": []}
    
    logger.info("--- Verifying Embedding Models ---")
    
    is_minimal = os.getenv("MINIMAL_EMBEDDINGS", "false").lower() == "true"
    registry = get_model_registry()
    models_to_check = (
        {"general_purpose": registry.embedding.get("general_purpose", "")}
        if is_minimal
        else registry.embedding
    )
    
    for label, repo in models_to_check.items():
        if not repo:
            continue
        logger.info(f"Checking model: {repo} ({label})")
        try:
            # Try to load the model (this will use cache if available)
            model = SentenceTransformer(repo)
            logger.info(f"  ✓ {repo} is available")
            results["found"].append(repo)
        except Exception as e:
            logger.warning(f"  ✗ {repo} not found or failed to load: {e}")
            results["missing"].append(repo)
    
    return results


def main():
    """Main function to verify all models."""
    logger.info("=" * 50)
    logger.info("   Cortex Model Lanes - Model Verifier   ")
    logger.info("=" * 50)
    
    models_dir = get_models_dir()
    logger.info(f"Models directory: {models_dir}\n")
    
    if not models_dir.exists():
        logger.error(f"Models directory does not exist: {models_dir}")
        logger.info("Run: ./ops/download_all_models.sh")
        sys.exit(1)
    
    # Verify each category
    vllm_results = verify_vllm_models(models_dir)
    print("")
    gguf_results = verify_gguf_models(models_dir)
    print("")
    embedding_results = verify_embedding_models()
    print("")
    
    # Summary
    logger.info("=" * 50)
    logger.info("           Verification Summary           ")
    logger.info("=" * 50)
    
    total_found = len(vllm_results["found"]) + len(gguf_results["found"]) + len(embedding_results["found"])
    total_missing = len(vllm_results["missing"]) + len(gguf_results["missing"]) + len(embedding_results["missing"])
    
    logger.info(f"vLLM Models: {len(vllm_results['found'])} found, {len(vllm_results['missing'])} missing")
    if vllm_results["found"]:
        for item in vllm_results["found"]:
            logger.info(f"  ✓ {item}")
    if vllm_results["missing"]:
        for item in vllm_results["missing"]:
            logger.warning(f"  ✗ {item}")
    
    logger.info(f"GGUF Models: {len(gguf_results['found'])} found, {len(gguf_results['missing'])} missing")
    if gguf_results["found"]:
        for item in gguf_results["found"]:
            logger.info(f"  ✓ {item}")
    if gguf_results["missing"]:
        for item in gguf_results["missing"]:
            logger.warning(f"  ✗ {item}")
    
    logger.info(f"Embedding Models: {len(embedding_results['found'])} found, {len(embedding_results['missing'])} missing")
    if embedding_results["found"]:
        for item in embedding_results["found"]:
            logger.info(f"  ✓ {item}")
    if embedding_results["missing"]:
        for item in embedding_results["missing"]:
            logger.warning(f"  ✗ {item}")
    
    print("")
    if total_missing == 0:
        logger.info("✅ All required models are downloaded!")
        sys.exit(0)
    else:
        logger.warning(f"⚠️  {total_missing} model(s) are missing.")
        logger.info("Run: ./ops/download_all_models.sh to download missing models")
        sys.exit(1)


if __name__ == "__main__":
    main()
