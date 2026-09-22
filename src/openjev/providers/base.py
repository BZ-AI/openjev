from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ProviderResult:
    data: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    raw: Any = None
    debug: dict[str, Any] = field(default_factory=dict)


class DecisionProvider(Protocol):
    def decide(
        self,
        payload: dict[str, Any],
        schema: dict[str, Any],
        *,
        repair_hint: str | None = None,
    ) -> ProviderResult:
        ...
