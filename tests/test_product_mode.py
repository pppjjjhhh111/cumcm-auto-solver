from pathlib import Path

import pytest

from main import build_llm_client, build_parser
from src.core.llm_client import DeepSeekLLMClient


def test_cli_deepseek_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    args = build_parser().parse_args(["--problem", "path/to/problem.pdf"])

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY is required"):
        build_llm_client(args, Path.cwd())


def test_cli_uses_deepseek_when_api_key_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    args = build_parser().parse_args(["--problem", "path/to/problem.pdf"])

    assert isinstance(build_llm_client(args, Path.cwd()), DeepSeekLLMClient)

