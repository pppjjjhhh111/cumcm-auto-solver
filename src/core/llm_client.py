from __future__ import annotations

import json
import os
import time
from abc import ABC
from pathlib import Path
from typing import Any


class BaseLLMClient(ABC):
    """Provider-neutral LLM interface used by every agent."""

    provider = "base"

    def __init__(self, timeout_seconds: int = 60) -> None:
        self.timeout_seconds = timeout_seconds
        self.log_path: Path | None = None

    def set_log_path(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str) -> str:
        started = time.perf_counter()
        try:
            text, usage = self._generate_impl(prompt)
            self._log_call("generate", prompt, text, usage, time.perf_counter() - started, True)
            return text
        except Exception as exc:  # noqa: BLE001 - provider errors should be traceable.
            self._log_call("generate", prompt, f"{type(exc).__name__}: {exc}", {}, time.perf_counter() - started, False)
            raise

    def generate_json(self, prompt: str, schema_hint: dict[str, Any] | None = None) -> dict[str, Any]:
        last_error = ""
        for attempt in range(2):
            full_prompt = prompt
            if schema_hint:
                full_prompt += "\nReturn JSON matching this schema hint:\n" + json.dumps(schema_hint, ensure_ascii=False)
            if attempt:
                full_prompt += "\nThe previous response was invalid JSON. Return only valid JSON."
            started = time.perf_counter()
            try:
                text, usage = self._generate_impl(full_prompt)
                parsed = self._parse_json(text)
                self._log_call("generate_json", full_prompt, text, usage, time.perf_counter() - started, True)
                return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                self._log_call("generate_json", full_prompt, last_error, {}, time.perf_counter() - started, False)
        return {"status": "json_parse_failed", "error": last_error}

    def complete_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Backward-compatible structured call used by existing agents."""
        prompt = json.dumps({"task": task, "payload": payload}, ensure_ascii=False, default=str)
        response = self.generate_json(prompt)
        if isinstance(response, dict) and response.get("provider"):
            return response
        return {
            "provider": self.provider,
            "task": task,
            "status": response.get("status", "ok") if isinstance(response, dict) else "ok",
            "content": response,
        }

    def _generate_impl(self, prompt: str) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    def _log_call(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        usage: dict[str, Any],
        latency_seconds: float,
        success: bool,
    ) -> None:
        if self.log_path is None:
            return
        entry = {
            "agent_name": agent_name,
            "provider": self.provider,
            "prompt_summary": prompt[:500],
            "response_summary": response[:500],
            "token_usage": usage,
            "latency_seconds": round(latency_seconds, 4),
            "success_or_failure": "success" if success else "failure",
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


class MockLLMClient(BaseLLMClient):
    """Deterministic fallback that requires no API key."""

    provider = "mock"

    def complete_json(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        result = {
            "provider": "mock",
            "task": task,
            "status": "ok",
            "note": "Deterministic MockLLMClient response. Replace with a real LLMClient for production experiments.",
            "payload_keys": sorted(payload.keys()),
        }
        self._log_call(task, json.dumps(payload, ensure_ascii=False, default=str), json.dumps(result, ensure_ascii=False), {}, time.perf_counter() - started, True)
        return result

    def _generate_impl(self, prompt: str) -> tuple[str, dict[str, Any]]:
        payload = {
            "provider": "mock",
            "status": "ok",
            "summary": "Deterministic mock text generated for offline tests.",
            "prompt_preview": prompt[:200],
        }
        return json.dumps(payload, ensure_ascii=False), {}


class OpenAICompatibleLLMClient(BaseLLMClient):
    """OpenAI-compatible chat completions client."""

    provider = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        api_key_env: str = "OPENAI_API_KEY",
        model: str = "",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout_seconds: int = 60,
        strict: bool = False,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.api_key_env = api_key_env
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise ValueError(f"{api_key_env} is required for {self.provider}. Set it in the environment.")
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.strict = strict
        self.fallback_client = MockLLMClient()

    def _generate_impl(self, prompt: str) -> tuple[str, dict[str, Any]]:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, base_url=self.base_url or None, timeout=self.timeout_seconds)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Return valid JSON when JSON is requested. Do not include markdown fences."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content or "{}"
            usage = getattr(response, "usage", None)
            return content, {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            } if usage else {}
        except Exception:
            if self.strict:
                raise
            return self.fallback_client._generate_impl(prompt)


class LocalHTTPLLMClient(OpenAICompatibleLLMClient):
    provider = "local_http"

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key_env: str = "LOCAL_LLM_API_KEY",
        model: str = "",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout_seconds: int = 60,
        strict: bool = False,
    ) -> None:
        if not os.environ.get(api_key_env):
            os.environ[api_key_env] = "local-no-key"
        super().__init__(
            base_url=base_url,
            api_key_env=api_key_env,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            strict=strict,
        )


class DeepSeekLLMClient(OpenAICompatibleLLMClient):
    """DeepSeek adapter using the OpenAI-compatible API."""

    provider = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        strict: bool = False,
        timeout_seconds: int = 60,
    ) -> None:
        if api_key:
            os.environ["DEEPSEEK_API_KEY"] = api_key
        super().__init__(
            base_url=base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
            api_key_env="DEEPSEEK_API_KEY",
            model=model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-v4-flash",
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            strict=strict,
        )


class RealLLMClient(OpenAICompatibleLLMClient):
    """Generic real API adapter kept for older CLI compatibility."""

    provider = "real"

    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            base_url=os.environ.get("OPENAI_BASE_URL", ""),
            api_key_env="OPENAI_API_KEY",
            model=model or os.environ.get("OPENAI_MODEL", ""),
        )


LLMClient = BaseLLMClient
