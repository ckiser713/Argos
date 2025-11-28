"""
llama.cpp service for local inference using ROCm-optimized binaries.

This service provides an interface to llama.cpp inference engine,
allowing the backend to use local GGUF models without requiring
a separate API server.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class LlamaCppService:
    """Service for running llama.cpp inference locally."""

    def __init__(
        self,
        binary_path: Optional[str] = None,
        model_path: Optional[str] = None,
        n_ctx: Optional[int] = None,
        n_threads: Optional[int] = None,
        n_gpu_layers: Optional[int] = None,
        use_mmap: bool = True,
        use_mlock: bool = False,
    ):
        """
        Initialize llama.cpp service.

        Args:
            binary_path: Path to llama-cpp binary (defaults to config)
            model_path: Path to GGUF model file (defaults to config)
            n_ctx: Context window size (defaults to config, can be up to 4M for ultra-long context)
            n_threads: Number of CPU threads (defaults to config)
            n_gpu_layers: Number of layers to offload to GPU (99 = all layers, for ROCm)
            use_mmap: Use memory mapping for model loading (faster, less RAM)
            use_mlock: Lock model in memory (prevents swapping, uses more RAM)
        """
        self.binary_path = Path(binary_path or settings.llama_cpp_binary_path)
        self.model_path = model_path or settings.llama_cpp_model_path
        self.n_ctx = n_ctx or settings.llama_cpp_n_ctx
        self.n_threads = n_threads or settings.llama_cpp_n_threads
        # For ultra-long context (4M tokens), offload all layers to GPU
        self.n_gpu_layers = n_gpu_layers if n_gpu_layers is not None else getattr(settings, "llama_cpp_n_gpu_layers", 99)
        self.use_mmap = use_mmap
        self.use_mlock = use_mlock

        if not self.binary_path.exists():
            raise FileNotFoundError(
                f"llama.cpp binary not found at: {self.binary_path}\n"
                f"Please ensure ROCm binaries are installed or set CORTEX_LLAMA_CPP_BINARY"
            )

        if not self.model_path:
            raise ValueError(
                "llama.cpp model path not configured.\n"
                "Please set CORTEX_LLAMA_CPP_MODEL_PATH to a GGUF model file"
            )

        if not Path(self.model_path).exists():
            raise FileNotFoundError(
                f"llama.cpp model not found at: {self.model_path}\n"
                f"Please ensure the GGUF model file exists"
            )

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 512,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text using llama.cpp.

        Args:
            prompt: Input prompt text
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stop: List of stop sequences
            **kwargs: Additional llama.cpp arguments

        Returns:
            Generated text
        """
        logger.info(
            "llama_cpp_service.generate.start",
            extra={
                "model": self.model_path,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "prompt_length": len(prompt),
            },
        )

        # Build command
        cmd = [
            str(self.binary_path),
            "-m",
            self.model_path,
            "-p",
            prompt,
            "--temp",
            str(temperature),
            "--n-predict",
            str(max_tokens),
            "-c",
            str(self.n_ctx),  # Context window size (supports up to 4M for ultra-long context)
            "--threads",
            str(self.n_threads),
            "--no-display-prompt",  # Don't echo the prompt in output
        ]
        
        # GPU offloading for ROCm (offload all layers for ultra-long context)
        if self.n_gpu_layers > 0:
            cmd.extend(["-ngl", str(self.n_gpu_layers)])
        
        # Memory mapping options
        if self.use_mmap:
            cmd.append("--mmap")
        if self.use_mlock:
            cmd.append("--mlock")
        
        # KV cache quantization for ultra-long context (4M tokens)
        # Use q8_0 quantization to fit 4M tokens in ~58GB
        if self.n_ctx >= 1000000:  # 1M+ tokens
            cmd.extend(["--cache-type-k", "q8_0"])

        # Add stop sequences if provided
        if stop:
            for stop_seq in stop:
                cmd.extend(["--stop", stop_seq])

        # Add any additional kwargs as command-line arguments
        # Format: --key value or --flag (for boolean flags)
        for key, value in kwargs.items():
            key_normalized = key.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key_normalized}")
            else:
                cmd.extend([f"--{key_normalized}", str(value)])

        try:
            # Run llama.cpp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max_tokens * 2,  # Rough timeout estimate
                check=False,  # Don't raise on non-zero exit
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.error(
                    "llama_cpp_service.generate.error",
                    extra={
                        "returncode": result.returncode,
                        "error": error_msg,
                        "cmd": " ".join(cmd[:5]),  # Log first part of command
                    },
                )
                raise RuntimeError(f"llama.cpp failed: {error_msg}")

            # Extract generated text (llama.cpp outputs the full prompt + completion)
            # We need to remove the prompt from the output
            output = result.stdout.strip()
            
            # Simple heuristic: if prompt is in output, remove it
            if prompt in output:
                # Find where prompt ends and generation begins
                prompt_end = output.find(prompt) + len(prompt)
                generated = output[prompt_end:].strip()
            else:
                # If prompt not found, assume entire output is generation
                generated = output

            logger.info(
                "llama_cpp_service.generate.success",
                extra={
                    "generated_length": len(generated),
                    "tokens_approx": len(generated.split()),
                },
            )

            return generated

        except subprocess.TimeoutExpired:
            logger.error("llama_cpp_service.generate.timeout", extra={"max_tokens": max_tokens})
            raise TimeoutError(f"llama.cpp generation timed out after {max_tokens * 2}s")
        except Exception as e:
            logger.exception("llama_cpp_service.generate.exception", extra={"error": str(e)})
            raise

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> str:
        """
        Generate chat completion from messages (OpenAI-compatible format).

        Args:
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments

        Returns:
            Generated text
        """
        # Convert messages to prompt format
        # Simple format: concatenate messages with role prefixes
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")

        prompt = "".join(prompt_parts) + "Assistant:"

        return self.generate(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=["User:", "System:"],  # Stop on role changes
            **kwargs,
        )


# Global service instances (lazy initialization)
_llama_cpp_services: dict[str, LlamaCppService] = {}


def get_llama_cpp_service(model_path: Optional[str] = None) -> LlamaCppService:
    """Get or create llama.cpp service instance for the given model path."""
    # Use model_path as key, fallback to default if None
    key = model_path or "default"
    
    if key not in _llama_cpp_services:
        _llama_cpp_services[key] = LlamaCppService(model_path=model_path)
    
    return _llama_cpp_services[key]

