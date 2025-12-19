from app.config import get_settings
from app.domain.model_lanes import ModelLane
from app.services.llm_service import resolve_lane_config


def _clear_lane_env(monkeypatch) -> None:
    keys = [
        "ARGOS_LANE_CODER_MODEL",
        "ARGOS_LANE_CODER_MODEL_PATH",
        "ARGOS_LANE_CODER_BACKEND",
        "ARGOS_LANE_CODER_URL",
        "CORTEX_LANE_CODER_MODEL",
        "CORTEX_LANE_CODER_MODEL_PATH",
        "CORTEX_LANE_CODER_BACKEND",
        "CORTEX_LANE_CODER_URL",
        "ARGOS_LANE_FAST_RAG_MODEL",
        "ARGOS_LANE_FAST_RAG_MODEL_PATH",
        "ARGOS_LANE_FAST_RAG_BACKEND",
        "ARGOS_LANE_FAST_RAG_URL",
        "CORTEX_LANE_FAST_RAG_MODEL",
        "CORTEX_LANE_FAST_RAG_MODEL_PATH",
        "CORTEX_LANE_FAST_RAG_BACKEND",
        "CORTEX_LANE_FAST_RAG_URL",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_resolve_lane_config_defaults(monkeypatch):
    _clear_lane_env(monkeypatch)
    get_settings.cache_clear()

    base_url, model_name, backend, model_path = resolve_lane_config(ModelLane.CODER)

    assert base_url.endswith("/v1")
    assert model_name == "Qwen2.5-Coder-32B-Instruct"
    assert backend == "vllm"
    assert model_path == "/models/vllm/coder/bf16"


def test_cortex_env_aliasing_for_lane_settings(monkeypatch):
    _clear_lane_env(monkeypatch)
    monkeypatch.setenv("CORTEX_LANE_FAST_RAG_URL", "http://example.com/v1")
    monkeypatch.setenv("CORTEX_LANE_FAST_RAG_MODEL", "Test-Fast-Rag")
    monkeypatch.setenv("CORTEX_LANE_FAST_RAG_MODEL_PATH", "/tmp/models/fast_rag/bf16")
    monkeypatch.setenv("CORTEX_LANE_FAST_RAG_BACKEND", "vllm")
    get_settings.cache_clear()

    base_url, model_name, backend, model_path = resolve_lane_config(ModelLane.FAST_RAG)

    assert base_url == "http://example.com/v1"
    assert model_name == "Test-Fast-Rag"
    assert backend == "vllm"
    assert model_path == "/tmp/models/fast_rag/bf16"
