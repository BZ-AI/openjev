from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from .base import ProviderResult


class MockProvider:
    """Deterministic provider for tests, demos, and offline development."""

    def __init__(self, responses: dict[str, Any] | Iterable[dict[str, Any]]):
        if isinstance(responses, dict):
            self._responses = [responses]
        else:
            self._responses = list(responses)
        if not self._responses:
            raise ValueError("MockProvider needs at least one response.")
        self.calls: list[dict[str, Any]] = []

    def decide(self, payload, schema, *, repair_hint=None) -> ProviderResult:
        index = min(len(self.calls), len(self._responses) - 1)
        self.calls.append(
            {"payload": deepcopy(payload), "schema": deepcopy(schema), "repair_hint": repair_hint}
        )
        return ProviderResult(data=deepcopy(self._responses[index]), latency_ms=0.0)
