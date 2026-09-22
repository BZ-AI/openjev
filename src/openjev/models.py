from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

JSONContent: TypeAlias = Any


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Noul(_StrictModel):
    type: Literal["noul"] = "noul"
    instructions: JSONContent | None = None
    criteria: dict[Literal["true", "false"], JSONContent | None] | None = None


class Choice(_StrictModel):
    type: Literal["choice"] = "choice"
    instructions: JSONContent | None = None
    criteria: Mapping[str, JSONContent | None]

    @field_validator("criteria")
    @classmethod
    def at_least_two_choices(cls, value: Mapping[str, JSONContent | None]):
        if len(value) < 2:
            raise ValueError("Choice requires at least two criteria.")
        return value


class Score(_StrictModel):
    type: Literal["score"] = "score"
    instructions: JSONContent | None = None
    criteria: Sequence[JSONContent]

    @field_validator("criteria")
    @classmethod
    def at_least_two_levels(cls, value: Sequence[JSONContent]):
        if len(value) < 2:
            raise ValueError("Score requires at least two ordered criteria.")
        return value


Question: TypeAlias = Noul | Choice | Score


class NoulAnswer(_StrictModel):
    type: Literal["noul"] = "noul"
    probability: float = Field(ge=0.0, le=1.0)
    value: bool
    confidence: float = Field(ge=0.0, le=1.0)


class ChoiceAnswer(_StrictModel):
    type: Literal["choice"] = "choice"
    choice: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)


class ScoreAnswer(_StrictModel):
    type: Literal["score"] = "score"
    score: float
    probabilities: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)


Answer: TypeAlias = NoulAnswer | ChoiceAnswer | ScoreAnswer


class Usage(_StrictModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None
    attempts: int = 1


class DecisionResponse(_StrictModel):
    answers: dict[str, Answer]
    usage: Usage = Field(default_factory=Usage)
    debug: dict[str, Any] = Field(default_factory=dict)
