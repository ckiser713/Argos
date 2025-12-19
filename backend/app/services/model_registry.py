from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class VLLMLaneConfig:
    repos: Dict[str, str]
    default_format: str
    default_path: str
    model_name: str


@dataclass(frozen=True)
class GGUFLaneConfig:
    repo: str
    filename: str
    default_path: str
    model_name: str


@dataclass(frozen=True)
class ModelRegistry:
    vllm: Dict[str, VLLMLaneConfig]
    gguf: Dict[str, GGUFLaneConfig]
    embedding: Dict[str, str]


def _registry_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "model_registry.json"


def _lane_key(lane: object) -> str:
    if hasattr(lane, "value"):
        lane = getattr(lane, "value")
    return str(lane).lower()


def _parse_registry(raw: dict) -> ModelRegistry:
    vllm = {
        lane_key: VLLMLaneConfig(
            repos=data["repos"],
            default_format=data["default_format"],
            default_path=data["default_path"],
            model_name=data["model_name"],
        )
        for lane_key, data in raw.get("vllm", {}).items()
    }
    gguf = {
        lane_key: GGUFLaneConfig(
            repo=data["repo"],
            filename=data["filename"],
            default_path=data["default_path"],
            model_name=data["model_name"],
        )
        for lane_key, data in raw.get("gguf", {}).items()
    }
    embedding = dict(raw.get("embedding", {}))
    return ModelRegistry(vllm=vllm, gguf=gguf, embedding=embedding)


@lru_cache(maxsize=1)
def get_model_registry() -> ModelRegistry:
    registry_path = _registry_path()
    if not registry_path.exists():
        raise FileNotFoundError(f"Model registry not found at {registry_path}")
    with registry_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return _parse_registry(raw)


def get_lane_model_name(lane: object) -> str:
    lane_name = _lane_key(lane)
    registry = get_model_registry()
    if lane_name in registry.vllm:
        return registry.vllm[lane_name].model_name
    if lane_name in registry.gguf:
        return registry.gguf[lane_name].model_name
    raise KeyError(f"Unknown lane '{lane_name}' in model registry")


def get_lane_default_path(lane: object) -> str:
    lane_name = _lane_key(lane)
    registry = get_model_registry()
    if lane_name in registry.vllm:
        return registry.vllm[lane_name].default_path
    if lane_name in registry.gguf:
        return registry.gguf[lane_name].default_path
    raise KeyError(f"Unknown lane '{lane_name}' in model registry")


def get_lane_backend(lane: object) -> str:
    lane_name = _lane_key(lane)
    registry = get_model_registry()
    if lane_name in registry.vllm:
        return "vllm"
    if lane_name in registry.gguf:
        return "llama_cpp"
    raise KeyError(f"Unknown lane '{lane_name}' in model registry")


def get_vllm_repo(lane: object, fmt: str | None = None) -> str:
    lane_name = _lane_key(lane)
    registry = get_model_registry()
    if lane_name not in registry.vllm:
        raise KeyError(f"Lane '{lane_name}' is not a vLLM lane")
    lane_config = registry.vllm[lane_name]
    format_key = (fmt or lane_config.default_format).lower()
    if format_key not in lane_config.repos:
        raise KeyError(f"Format '{format_key}' not found for lane '{lane_name}'")
    return lane_config.repos[format_key]


def get_gguf_repo_and_filename(lane: object) -> Tuple[str, str]:
    lane_name = _lane_key(lane)
    registry = get_model_registry()
    if lane_name not in registry.gguf:
        raise KeyError(f"Lane '{lane_name}' is not a GGUF lane")
    lane_config = registry.gguf[lane_name]
    return lane_config.repo, lane_config.filename


__all__ = [
    "ModelRegistry",
    "get_model_registry",
    "get_lane_model_name",
    "get_lane_default_path",
    "get_lane_backend",
    "get_vllm_repo",
    "get_gguf_repo_and_filename",
]
