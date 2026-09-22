from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .calibration import (
    choice_confidence,
    normalize_distribution,
    score_confidence,
    score_expected_value,
)
from .models import (
    Choice,
    ChoiceAnswer,
    DecisionResponse,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    Usage,
)
from .providers.base import DecisionProvider
from .schema import output_schema, provider_payload


class OpenJev:
    def __init__(
        self,
        provider: DecisionProvider,
        *,
        malformed_retries: int = 2,
        noul_threshold: float = 0.5,
    ):
        if malformed_retries < 0:
            raise ValueError("malformed_retries must be >= 0")
        if not 0.0 <= noul_threshold <= 1.0:
            raise ValueError("noul_threshold must be in [0,1]")
        self.provider = provider
        self.malformed_retries = malformed_retries
        self.noul_threshold = noul_threshold

    def evaluate(
        self,
        *,
        state: Any,
        questions: Mapping[str, Question],
    ) -> DecisionResponse:
        if not questions:
            raise ValueError("At least one question is required.")
        if len(set(questions)) != len(questions):
            raise ValueError("Question IDs must be unique.")

        schema = output_schema(questions)
        payload = provider_payload(state, questions)

        attempts = []
        repair_hint = None

        for attempt in range(self.malformed_retries + 1):
            result = self.provider.decide(payload, schema, repair_hint=repair_hint)
            attempts.append(result)
            try:
                answers, debug = self._decode(questions, result.data)
                return DecisionResponse(
                    answers=answers,
                    usage=Usage(
                        input_tokens=_sum_optional(a.input_tokens for a in attempts),
                        output_tokens=_sum_optional(a.output_tokens for a in attempts),
                        latency_ms=sum((a.latency_ms or 0.0) for a in attempts),
                        attempts=len(attempts),
                    ),
                    debug={
                        "probability_diagnostics": debug,
                        "provider_debug": [a.debug for a in attempts],
                    },
                )
            except (KeyError, TypeError, ValueError) as exc:
                repair_hint = (
                    f"Previous output was invalid: {type(exc).__name__}: {exc}. "
                    "Return a complete JSON object matching the schema exactly."
                )
                if attempt >= self.malformed_retries:
                    raise ValueError(
                        f"Provider output remained invalid after {len(attempts)} attempts: {exc}"
                    ) from exc

        raise AssertionError("unreachable")

    def _decode(self, questions: Mapping[str, Question], raw: dict[str, Any]):
        raw_answers = raw["answers"]
        if set(raw_answers) != set(questions):
            missing = sorted(set(questions) - set(raw_answers))
            extra = sorted(set(raw_answers) - set(questions))
            raise ValueError(f"Answer keys mismatch; missing={missing}, extra={extra}")

        decoded = {}
        diagnostics = {}

        for qid, q in questions.items():
            value = raw_answers[qid]

            if isinstance(q, Noul):
                probability = float(value)
                if not 0.0 <= probability <= 1.0:
                    raise ValueError(f"Noul probability for {qid!r} must be in [0,1].")
                decoded[qid] = NoulAnswer(
                    probability=probability,
                    value=probability >= self.noul_threshold,
                )
                diagnostics[qid] = {"normalization_error": 0.0}
                continue

            if not isinstance(value, dict):
                raise TypeError(f"{qid!r} requires a probability mapping.")

            if isinstance(q, Choice):
                expected_labels = list(q.criteria)
                if set(value) != set(expected_labels):
                    raise ValueError(f"{qid!r} labels must be exactly {expected_labels!r}.")
                probs, error = normalize_distribution({label: value[label] for label in expected_labels})
                selected = max(expected_labels, key=probs.__getitem__)
                decoded[qid] = ChoiceAnswer(
                    choice=selected,
                    probabilities=probs,
                    confidence=choice_confidence(probs),
                )
                diagnostics[qid] = {"normalization_error": error}
                continue

            if isinstance(q, Score):
                expected_labels = [str(i) for i in range(len(q.criteria))]
                if set(value) != set(expected_labels):
                    raise ValueError(f"{qid!r} score labels must be exactly {expected_labels!r}.")
                probs, error = normalize_distribution({label: value[label] for label in expected_labels})
                decoded[qid] = ScoreAnswer(
                    score=score_expected_value(probs),
                    probabilities=probs,
                    confidence=score_confidence(probs),
                )
                diagnostics[qid] = {"normalization_error": error}
                continue

            raise TypeError(f"Unsupported question type: {type(q)!r}")

        return decoded, diagnostics


def _sum_optional(values):
    values = list(values)
    return None if any(v is None for v in values) else sum(values)
