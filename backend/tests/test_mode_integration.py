from __future__ import annotations

from typing import Any, List

import pytest

from app.domain.mode import ProjectExecutionSettings
from app.repos import mode_repo
from app.services import llm_service


class _DummyLLM:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.response_counter = 0

    def __call__(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        model: str,
        **extra: Any,
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "model": model,
                **extra,
            }
        )
        self.response_counter += 1
        return f"dummy-response-{self.response_counter}"


@pytest.fixture
def dummy_llm(monkeypatch: pytest.MonkeyPatch) -> _DummyLLM:
    dummy = _DummyLLM()

    def _call_underlying_llm(
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        model: str,
        **extra: Any,
    ) -> str:
        return dummy(prompt, temperature=temperature, max_tokens=max_tokens, model=model, **extra)

    monkeypatch.setattr(llm_service, "_call_underlying_llm", _call_underlying_llm)
    return dummy


@pytest.fixture(autouse=True)
def reset_mode_repo():
    # Clear the in-memory store before each test to ensure isolation
    mode_repo._PROJECT_SETTINGS_STORE = {}
    yield


def test_generate_text_normal_mode_single_pass(dummy_llm: _DummyLLM) -> None:
    project_id = "integration-normal"

    # Ensure project is in normal mode with 1 validation pass
    mode_repo.set_project_settings(
        ProjectExecutionSettings(
            project_id=project_id,
            mode="normal",
            llm_temperature=0.3,
            validation_passes=1,
            max_parallel_tools=8,
        )
    )

    result = llm_service.generate_text("hello", project_id=project_id, base_temperature=0.5)
    assert result.startswith("dummy-response")

    # Expect exactly one underlying LLM call.
    assert len(dummy_llm.calls) == 1
    call = dummy_llm.calls[0]
    assert call["temperature"] == 0.3  # project settings override base_temperature


def test_generate_text_paranoid_mode_checker_passes(dummy_llm: _DummyLLM) -> None:
    project_id = "integration-paranoid"

    mode_repo.set_project_settings(
        ProjectExecutionSettings(
            project_id=project_id,
            mode="paranoid",
            llm_temperature=0.2,
            validation_passes=2,
            max_parallel_tools=4,
        )
    )

    _ = llm_service.generate_text("hello", project_id=project_id, base_temperature=0.7)

    # Expect 1 primary pass + 2 checker passes.
    assert len(dummy_llm.calls) == 3

    primary_call = dummy_llm.calls[0]
    assert primary_call["temperature"] == 0.2

    checker_calls = dummy_llm.calls[1:]
    for call in checker_calls:
        # Checker uses min(temperature, 0.2)
        assert call["temperature"] <= 0.2
        assert "DRAFT ANSWER" in call["prompt"]
