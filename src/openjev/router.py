from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .calibration import temperature_scale_distribution, temperature_scale_probability
from .engine import OpenJev
from .models import Choice, DecisionResponse, NoulAnswer, Question


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GateOutcome(_StrictModel):
    name: str
    passed: bool
    reason: str | None = None


class RouteTrace(_StrictModel):
    route: Literal["blocked", "fast", "strong"]
    selected_provider: str | None = None
    escalated: bool = False
    fast_confidences: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    gates: list[GateOutcome] = Field(default_factory=list)


class AdaptiveResult(_StrictModel):
    response: DecisionResponse | None = None
    fast_response: DecisionResponse | None = None
    trace: RouteTrace


@dataclass(frozen=True)
class DeterministicGate:
    """A code-owned invariant that runs before any model call."""

    name: str
    predicate: Callable[[Any, Mapping[str, Question]], bool]
    failure_reason: str

    def evaluate(self, state: Any, questions: Mapping[str, Question]) -> GateOutcome:
        passed = bool(self.predicate(state, questions))
        return GateOutcome(
            name=self.name,
            passed=passed,
            reason=None if passed else self.failure_reason,
        )


@dataclass(frozen=True)
class RoutingPolicy:
    """Confidence/escalation policy for a local-first decision cascade."""

    confidence_threshold: float = 0.60
    max_fast_choice_options: int = 20
    max_normalization_error: float = 0.05
    question_thresholds: Mapping[str, float] = field(default_factory=dict)
    temperatures: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in [0,1]")
        if self.max_fast_choice_options < 2:
            raise ValueError("max_fast_choice_options must be >= 2")
        if self.max_normalization_error < 0:
            raise ValueError("max_normalization_error must be >= 0")
        for qid, threshold in self.question_thresholds.items():
            if not 0.0 <= float(threshold) <= 1.0:
                raise ValueError(f"threshold for {qid!r} must be in [0,1]")
        for qid, temperature in self.temperatures.items():
            if float(temperature) <= 0:
                raise ValueError(f"temperature for {qid!r} must be > 0")


class AdaptiveDecisionRuntime:
    """Run deterministic gates, then fast local inference, then escalate when needed.

    The strong engine is optional. Without one, low-confidence results are returned
    from the fast engine with an explicit reason in the route trace.
    """

    def __init__(
        self,
        fast: OpenJev,
        strong: OpenJev | None = None,
        *,
        policy: RoutingPolicy | None = None,
        gates: Sequence[DeterministicGate] = (),
        fast_name: str | None = None,
        strong_name: str | None = None,
    ):
        self.fast = fast
        self.strong = strong
        self.policy = policy or RoutingPolicy()
        self.gates = tuple(gates)
        self.fast_name = fast_name or type(fast.provider).__name__
        self.strong_name = (
            strong_name
            or (type(strong.provider).__name__ if strong is not None else None)
        )

    def evaluate(
        self,
        *,
        state: Any,
        questions: Mapping[str, Question],
    ) -> AdaptiveResult:
        if not questions:
            raise ValueError("At least one question is required.")

        gate_outcomes = [gate.evaluate(state, questions) for gate in self.gates]
        failed = [outcome for outcome in gate_outcomes if not outcome.passed]
        if failed:
            return AdaptiveResult(
                trace=RouteTrace(
                    route="blocked",
                    reasons=[outcome.reason or outcome.name for outcome in failed],
                    gates=gate_outcomes,
                )
            )

        preflight_reasons = self._preflight_escalation_reasons(questions)
        if preflight_reasons and self.strong is not None:
            response = self.strong.evaluate(state=state, questions=questions)
            return AdaptiveResult(
                response=response,
                trace=RouteTrace(
                    route="strong",
                    selected_provider=self.strong_name,
                    escalated=True,
                    reasons=preflight_reasons,
                    gates=gate_outcomes,
                ),
            )

        fast_response = self.fast.evaluate(state=state, questions=questions)
        confidences = self._confidences(fast_response)
        reasons = list(preflight_reasons)
        reasons.extend(self._postflight_escalation_reasons(fast_response, confidences))

        if reasons and self.strong is not None:
            response = self.strong.evaluate(state=state, questions=questions)
            return AdaptiveResult(
                response=response,
                fast_response=fast_response,
                trace=RouteTrace(
                    route="strong",
                    selected_provider=self.strong_name,
                    escalated=True,
                    fast_confidences=confidences,
                    reasons=reasons,
                    gates=gate_outcomes,
                ),
            )

        if reasons:
            reasons.append("no strong provider configured; returning fast result")

        return AdaptiveResult(
            response=fast_response,
            trace=RouteTrace(
                route="fast",
                selected_provider=self.fast_name,
                escalated=False,
                fast_confidences=confidences,
                reasons=reasons,
                gates=gate_outcomes,
            ),
        )

    def _preflight_escalation_reasons(
        self,
        questions: Mapping[str, Question],
    ) -> list[str]:
        reasons = []
        for qid, question in questions.items():
            if isinstance(question, Choice) and len(question.criteria) > self.policy.max_fast_choice_options:
                reasons.append(
                    f"{qid}: {len(question.criteria)} options exceeds fast-provider limit "
                    f"{self.policy.max_fast_choice_options}"
                )
        return reasons

    def _confidences(self, response: DecisionResponse) -> dict[str, float]:
        confidences: dict[str, float] = {}
        for qid, answer in response.answers.items():
            temperature = float(self.policy.temperatures.get(qid, 1.0))
            if temperature == 1.0:
                confidences[qid] = float(answer.confidence)
            elif isinstance(answer, NoulAnswer):
                probability = temperature_scale_probability(answer.probability, temperature)
                confidences[qid] = max(probability, 1.0 - probability)
            else:
                distribution = temperature_scale_distribution(answer.probabilities, temperature)
                confidences[qid] = max(distribution.values())
        return confidences

    def _postflight_escalation_reasons(
        self,
        response: DecisionResponse,
        confidences: Mapping[str, float],
    ) -> list[str]:
        reasons: list[str] = []
        for qid, confidence in confidences.items():
            threshold = float(
                self.policy.question_thresholds.get(qid, self.policy.confidence_threshold)
            )
            if confidence < threshold:
                reasons.append(
                    f"{qid}: calibrated confidence {confidence:.3f} < threshold {threshold:.3f}"
                )

        diagnostics = response.debug.get("probability_diagnostics") or {}
        for qid, item in diagnostics.items():
            error = float((item or {}).get("normalization_error", 0.0))
            if error > self.policy.max_normalization_error:
                reasons.append(
                    f"{qid}: provider probability normalization error {error:.3f} exceeds "
                    f"{self.policy.max_normalization_error:.3f}"
                )
        return reasons
