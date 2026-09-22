from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .base import ProviderResult


class JevProvider:
    """Adapter for TypeSafe-compatible `POST /v1/systemone` endpoints.

    This is an interoperability adapter only. OpenJev is independent from TypeSafe AI.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "jev-latest",
        base_url: str = "https://api.typesafe.ai",
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if client is None:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            self._client = httpx.Client(timeout=timeout, headers=headers)
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def decide(self, payload, schema, *, repair_hint=None) -> ProviderResult:
        del schema, repair_hint
        if not self.api_key and self.base_url == "https://api.typesafe.ai":
            raise RuntimeError("TYPESAFE_API_KEY (or api_key=...) is required for the hosted Jev API.")

        questions = {
            qid: {key: value for key, value in question.items() if value is not None}
            for qid, question in payload["questions"].items()
        }
        body = {
            "model": self.model,
            "state": payload["state"],
            "questions": questions,
        }

        started = time.perf_counter()
        response = self._client.post(f"{self.base_url}/v1/systemone", json=body)
        response.raise_for_status()
        wall_latency_ms = (time.perf_counter() - started) * 1000

        raw = response.json()
        raw_answers = raw["answers"]
        answers: dict[str, Any] = {}
        native_confidence: dict[str, float] = {}

        for qid, question in payload["questions"].items():
            answer = raw_answers[qid]
            qtype = question["type"]

            if qtype == "noul":
                probability = answer.get("noul", answer.get("probability"))
                if probability is None:
                    raise ValueError(f"Jev response for {qid!r} did not contain 'noul'.")
                probability = float(probability)
                answers[qid] = probability
                native_confidence[qid] = float(
                    answer.get("confidence", max(probability, 1.0 - probability))
                )
                continue

            probabilities = answer.get("probabilities")
            if not isinstance(probabilities, dict):
                raise TypeError(f"Jev response for {qid!r} did not contain probabilities.")
            answers[qid] = {str(key): float(value) for key, value in probabilities.items()}
            if answer.get("confidence") is not None:
                native_confidence[qid] = float(answer["confidence"])

        usage = raw.get("usage") or {}
        latency_ms = raw.get("latency_ms") or wall_latency_ms
        return ProviderResult(
            data={"answers": answers},
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            latency_ms=float(latency_ms),
            raw=raw,
            debug={
                "backend": "jev-compatible",
                "model": raw.get("model", self.model),
                "native_confidence": native_confidence,
                "wall_latency_ms": wall_latency_ms,
            },
        )


class SystemOneHTTPProvider(JevProvider):
    """Neutral alias for any compatible `/v1/systemone` HTTP server."""
