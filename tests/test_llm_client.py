import pytest

from src.core.llm_client import DeepSeekLLMClient, MockLLMClient


def test_mock_llm_client_returns_structured_trace() -> None:
    result = MockLLMClient().complete_json("unit_test", {"x": 1})

    assert result["provider"] == "mock"
    assert result["status"] == "ok"
    assert result["payload_keys"] == ["x"]


def test_mock_llm_client_generate_json() -> None:
    result = MockLLMClient().generate_json("return json")

    assert result["provider"] == "mock"
    assert result["status"] == "ok"


def test_deepseek_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ValueError):
        DeepSeekLLMClient(api_key="")
