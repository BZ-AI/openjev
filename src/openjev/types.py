from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True)
class Noul:
    instructions: str

    def __post_init__(self) -> None:
        _require_text(self.instructions, "instructions")

    def to_spec(self) -> dict[str, Any]:
        return {"kind": "noul", "instructions": self.instructions}


@dataclass(frozen=True)
class Choice:
    instructions: str
    criteria: dict[str, str]

    def __post_init__(self) -> None:
        _require_text(self.instructions, "instructions")
        if not isinstance(self.criteria, dict) or len(self.criteria) < 2:
            raise ValueError("criteria must contain at least two labels")
        for label, description in self.criteria.items():
            _require_text(label, "choice label")
            _require_text(description, f"description for {label!r}")

    def to_spec(self) -> dict[str, Any]:
        return {
            "kind": "choice",
            "instructions": self.instructions,
            "criteria": dict(self.criteria),
        }


@dataclass(frozen=True)
class Score:
    instructions: str
    criteria: list[str]

    def __post_init__(self) -> None:
        _require_text(self.instructions, "instructions")
        if not isinstance(self.criteria, list) or len(self.criteria) < 2:
            raise ValueError("criteria must contain at least two ordered levels")
        for index, description in enumerate(self.criteria):
            _require_text(description, f"score criterion {index}")

    def to_spec(self) -> dict[str, Any]:
        return {
            "kind": "score",
            "instructions": self.instructions,
            "criteria": list(self.criteria),
        }


Question = Noul | Choice | Score


@dataclass(frozen=True)
class NoulAnswer:
    probability: float
    decision: bool
    confidence: float


@dataclass(frozen=True)
class ChoiceAnswer:
    label: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreAnswer:
    probabilities: dict[str, float]
    expected_score: float
    confidence: float


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer


@dataclass(frozen=True)
class EvaluationResult:
    answers: dict[str, Answer]
    request: dict[str, Any]
    raw_response: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

    def model_dump_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.model_dump(), indent=indent, sort_keys=True)

