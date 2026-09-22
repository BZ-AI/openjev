from __future__ import annotations

from typing import Any

from .schema import response_schema
from .types import (
    Choice,
    ChoiceAnswer,
    EvaluationResult,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
)


class OpenJev:
    def __init__(self, provider: Any):
        if provider is None or not hasattr(provider, "evaluate"):
            raise TypeError("provider must expose evaluate(request)")
        self.provider = provider

    def evaluate(
        self,
        *,
        state: dict[str, Any],
        questions: dict[str, Question],
    ) -> EvaluationResult:
        if not isinstance(state, dict):
            raise TypeError("state must be a dict")
        if not isinstance(questions, dict) or not questions:
            raise ValueError("questions must be a non-empty dict")
        for name, question in questions.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("question names must be non-empty strings")
            if not isinstance(question, (Noul, Choice, Score)):
                raise TypeError(f"unsupported question {name!r}")

        request = {
            "state": state,
            "questions": {name: question.to_spec() for name, question in questions.items()},
            "response_schema": response_schema(questions),
        }
        attempts = max(1, int(getattr(self.provider, "max_retries", 0)) + 1)
        last_error: Exception | None = None

        for attempt in range(attempts):
            raw = self.provider.evaluate(request)
            try:
                answers = self._parse_response(raw, questions)
                return EvaluationResult(answers=answers, request=request, raw_response=raw)
            except (TypeError, ValueError, KeyError) as exc:
                last_error = exc
                callback = getattr(self.provider, "on_malformed", None)
                if callable(callback):
                    callback(error=exc, raw_response=raw, attempt=attempt + 1)
                if attempt + 1 >= attempts:
                    break

        assert last_error is not None
        raise ValueError(f"provider returned invalid structured output: {last_error}") from last_error

    @staticmethod
    def _normalize(
        values: dict[str, Any],
        expected_labels: list[str],
    ) -> dict[str, float]:
        if not isinstance(values, dict):
            raise TypeError("probabilities must be an object")
        if set(values) != set(expected_labels):
            raise ValueError(
                f"probability labels must match exactly: expected {expected_labels}, got {list(values)}"
            )
        converted: dict[str, float] = {}
        for label in expected_labels:
            value = float(values[label])
            if value < 0:
                raise ValueError("probabilities cannot be negative")
            converted[label] = value
        total = sum(converted.values())
        if total <= 0:
            raise ValueError("probabilities must sum to a positive value")
        return {label: value / total for label, value in converted.items()}

    @classmethod
    def _parse_response(
        cls,
        raw: dict[str, Any],
        questions: dict[str, Question],
    ) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise TypeError("provider response must be an object")
        if set(raw) != set(questions):
            raise ValueError("provider response keys must match question keys exactly")

        answers: dict[str, Any] = {}
        for name, question in questions.items():
            item = raw[name]
            if not isinstance(item, dict):
                raise TypeError(f"answer {name!r} must be an object")

            if isinstance(question, Noul):
                if set(item) != {"probability"}:
                    raise ValueError(f"Noul answer {name!r} must contain only probability")
                probability = float(item["probability"])
                if not 0 <= probability <= 1:
                    raise ValueError("Noul probability must be between 0 and 1")
                answers[name] = NoulAnswer(
                    probability=probability,
                    decision=probability >= 0.5,
                    confidence=max(probability, 1 - probability),
                )
                continue

            if isinstance(question, Choice):
                if not set(item).issubset({"label", "probabilities"}) or "probabilities" not in item:
                    raise ValueError(f"Choice answer {name!r} has invalid fields")
                probabilities = cls._normalize(item["probabilities"], list(question.criteria))
                inferred = max(probabilities, key=probabilities.get)
                label = item.get("label", inferred)
                if label not in question.criteria:
                    raise ValueError(f"unknown choice label {label!r}")
                answers[name] = ChoiceAnswer(
                    label=label,
                    probabilities=probabilities,
                    confidence=probabilities[label],
                )
                continue

            if isinstance(question, Score):
                if set(item) != {"probabilities"}:
                    raise ValueError(f"Score answer {name!r} must contain only probabilities")
                labels = [str(index) for index in range(len(question.criteria))]
                probabilities = cls._normalize(item["probabilities"], labels)
                expected_score = sum(int(label) * probability for label, probability in probabilities.items())
                answers[name] = ScoreAnswer(
                    probabilities=probabilities,
                    expected_score=expected_score,
                    confidence=max(probabilities.values()),
                )

        return answers

