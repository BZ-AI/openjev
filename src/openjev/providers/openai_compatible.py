from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .base import ProviderResult

_SYSTEM_PROMPT = """You are a decision engine inside software.
Return only JSON that matches the provided schema.
Do not write explanations or prose.
For Choice and Score questions, provide a probability for every allowed label.
Use uncertainty honestly. Do not invent labels."""


class OpenAICompatibleProvider:
    """
    Minimal OpenAI-compatible Chat Completions provider.

    Designed for hosted APIs, vLLM, SGLang, LM Studio, and other endpoints that
    implement `/chat/completions`. Set `strict_json_schema=False` for servers that
    do not support the `json_schema` response format.
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
        strict_json_schema: bool = True,
        extra_body: dict[str, Any] | None = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.strict_json_schema = strict_json_schema
        self.extra_body = extra_body or {}
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def decide(self, payload, schema, *, repair_hint=None) -> ProviderResult:
        user_payload = dict(payload)
        if repair_hint:
            user_payload["repair_hint"] = repair_hint

        body: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }

        if self.strict_json_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "openjev_decision",
                    "strict": True,
                    "schema": schema,
                },
            }
        else:
            body["response_format"] = {"type": "json_object"}

        body.update(self.extra_body)

        started = time.perf_counter()
        response = self._client.post(f"{self.base_url}/chat/completions", json=body)
        response.raise_for_status()
        latency_ms = (time.perf_counter() - started) * 1000

        raw = response.json()
        text = raw["choices"][0]["message"]["content"]
        data = json.loads(text)

        usage = raw.get("usage") or {}
        return ProviderResult(
            data=data,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            raw=raw,
            debug={"finish_reason": raw["choices"][0].get("finish_reason")},
        )
