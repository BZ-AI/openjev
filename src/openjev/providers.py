from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable
from urllib import request as urllib_request


class MockProvider:
    def __init__(
        self,
        responses: dict[str, Any] | list[dict[str, Any]] | Callable[[dict[str, Any]], dict[str, Any]],
        *,
        max_retries: int = 0,
    ):
        self.responses = responses
        self.max_retries = max_retries
        self.calls = 0
        self.malformed: list[dict[str, Any]] = []

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        if callable(self.responses):
            response = self.responses(request)
        elif isinstance(self.responses, list):
            if not self.responses:
                raise RuntimeError("mock response queue is empty")
            index = min(self.calls, len(self.responses) - 1)
            response = self.responses[index]
        else:
            response = self.responses
        self.calls += 1
        return deepcopy(response)

    def on_malformed(
        self,
        *,
        error: Exception,
        raw_response: dict[str, Any],
        attempt: int,
    ) -> None:
        self.malformed.append(
            {"attempt": attempt, "error": str(error), "raw_response": deepcopy(raw_response)}
        )


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
        max_retries: int = 1,
    ):
        if not model:
            raise ValueError("model is required")
        if not api_key:
            raise ValueError("api_key is required")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only one JSON object that exactly matches the supplied "
                        "response schema. Values represent calibrated probabilities."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(request, sort_keys=True, separators=(",", ":")),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib_request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib_request.urlopen(http_request, timeout=self.timeout) as response:
            decoded = json.loads(response.read().decode("utf-8"))
        content = decoded["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("OpenAI-compatible response content must be a JSON string")
        return json.loads(content)

