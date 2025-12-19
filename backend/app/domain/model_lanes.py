from __future__ import annotations

from enum import Enum


class ModelLane(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    FAST_RAG = "fast_rag"
    SUPER_READER = "super_reader"
    GOVERNANCE = "governance"


_VLLM_LANES = {
    ModelLane.ORCHESTRATOR,
    ModelLane.CODER,
    ModelLane.FAST_RAG,
}

_LLAMA_LANES = {
    ModelLane.SUPER_READER,
    ModelLane.GOVERNANCE,
}


def is_vllm_lane(lane: ModelLane) -> bool:
    return lane in _VLLM_LANES


def is_llama_lane(lane: ModelLane) -> bool:
    return lane in _LLAMA_LANES

