from __future__ import annotations

import importlib
import time
from typing import Any

from .base import ProviderResult


class LayaProvider:
    """Optional local Laya/Laya-MLX adapter.

    The dependency is imported lazily so OpenJev stays lightweight. Upstream Laya
    code and weights are not vendored into this repository.
    """

    def __init__(
        self,
        *,
        package: str = "laya",
        use_router: bool = True,
        checkpoint: str | None = None,
        task: str | None = None,
        lang: str | None = None,
        preload: bool = False,
        backend: Any | None = None,
    ):
        if package not in {"laya", "laya_mlx"}:
            raise ValueError("package must be 'laya' or 'laya_mlx'")
        self.package = package
        self.use_router = use_router
        self.checkpoint = checkpoint
        self.task = task
        self.lang = lang
        self.preload = preload
        self._backend = backend

    def _load_backend(self):
        if self._backend is not None:
            return self._backend
        try:
            module = importlib.import_module(self.package)
        except ImportError as exc:
            extra = "laya-mlx" if self.package == "laya_mlx" else "laya"
            raise RuntimeError(
                f"{self.package} is not installed. Install the optional backend first "
                f"(for example: pip install {extra})."
            ) from exc

        if self.use_router:
            self._backend = module.Router(preload=self.preload)
        else:
            checkpoint = self.checkpoint or "convaiinnovations/laya"
            self._backend = module.load(checkpoint)
        return self._backend

    def decide(self, payload, schema, *, repair_hint=None) -> ProviderResult:
        del schema, repair_hint  # Laya returns typed answers directly; no repair loop is needed.
        backend = self._load_backend()
        questions = {
            qid: {key: value for key, value in question.items() if value is not None}
            for qid, question in payload["questions"].items()
        }

        kwargs: dict[str, Any] = {}
        if self.use_router:
            if self.checkpoint is not None:
                kwargs["model"] = self.checkpoint
            if self.task is not None:
                kwargs["task"] = self.task
            if self.lang is not None:
                kwargs["lang"] = self.lang

        started = time.perf_counter()
        result = backend.predict(payload["state"], questions, **kwargs)
        wall_latency_ms = (time.perf_counter() - started) * 1000

        raw_answers = result["answers"]
        answers: dict[str, Any] = {}
        native_confidence: dict[str, float] = {}

        for qid, question in questions.items():
            answer = raw_answers[qid]
            qtype = question["type"]

            if qtype == "noul":
                probability = answer.get("noul", answer.get("probability"))
                if probability is None:
                    raise ValueError(f"Laya response for {qid!r} did not contain 'noul'.")
                probability = float(probability)
                answers[qid] = probability
                native_confidence[qid] = float(
                    answer.get("confidence", max(probability, 1.0 - probability))
                )
                continue

            probabilities = answer.get("probabilities")
            if not isinstance(probabilities, dict):
                raise TypeError(f"Laya response for {qid!r} did not contain probabilities.")
            answers[qid] = {str(key): float(value) for key, value in probabilities.items()}
            if answer.get("confidence") is not None:
                native_confidence[qid] = float(answer["confidence"])

        usage = result.get("usage") or {}
        latency_ms = result.get("latency_ms")
        if latency_ms is None:
            latency_ms = usage.get("latency_ms")
        if latency_ms is None:
            latency_ms = wall_latency_ms

        return ProviderResult(
            data={"answers": answers},
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=float(latency_ms),
            raw=result,
            debug={
                "backend": self.package,
                "native_confidence": native_confidence,
                "routing": result.get("routing"),
                "wall_latency_ms": wall_latency_ms,
            },
        )
