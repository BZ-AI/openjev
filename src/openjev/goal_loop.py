from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .engine import OpenJev
from .models import Choice, Noul, Score
from .router import AdaptiveDecisionRuntime, AdaptiveResult


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LedgerItem(_StrictModel):
    id: str
    requirement: str
    priority: Literal["P0", "P1", "P2", "Optional"]
    status: Literal[
        "TODO",
        "IN_PROGRESS",
        "DONE",
        "BLOCKED",
        "NOT_APPLICABLE",
        "SUPERSEDED",
    ]
    evidence: str | None = None
    required: bool = True


class GoalLoopState(_StrictModel):
    project_goal: str
    definition_of_done: list[str]
    ledger: list[LedgerItem]
    latest_user_request: str | None = None
    latest_validation: str | None = None
    candidate_completion_claim: str | None = None
    extra_context: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class GoalLoopPolicy:
    missing_requirement_threshold: float = 0.60
    evidence_gap_threshold: float = 0.55
    completion_semantic_threshold: float = 0.85
    high_risk_score: float = 3.0


class GoalLoopDecision(_StrictModel):
    hard_gate_passed: bool
    final_action: Literal["CONTINUE", "REPAIR", "REVALIDATE", "ESCALATE", "COMPLETE_CANDIDATE"]
    reasons: list[str]
    semantic: dict[str, Any] = Field(default_factory=dict)


class GoalLoopAuditor:
    """
    Decision layer for Goal Loop.

    Deterministic facts are enforced in code. The model is used only where the
    state requires semantic judgment.
    """

    def __init__(
        self,
        engine: OpenJev | AdaptiveDecisionRuntime,
        policy: GoalLoopPolicy | None = None,
    ):
        self.engine = engine
        self.policy = policy or GoalLoopPolicy()

    def audit(self, state: GoalLoopState) -> GoalLoopDecision:
        hard_reasons = self._hard_gate_reasons(state)
        if hard_reasons:
            return GoalLoopDecision(
                hard_gate_passed=False,
                final_action=self._deterministic_action_for_hard_failure(state),
                reasons=hard_reasons,
                semantic={"skipped": "deterministic hard gate failed before model inference"},
            )

        semantic_result = self.engine.evaluate(
            state=state.model_dump(mode="json"),
            questions={
                "missing_requirement": Noul(
                    instructions=(
                        "Based on the project goal, latest user request, definition of done, "
                        "and ledger, at least one mandatory user requirement is likely missing "
                        "from the ledger."
                    ),
                    criteria={
                        "true": "A required user intent or deliverable is absent from the ledger.",
                        "false": "The ledger appears to cover the mandatory requirements.",
                    },
                ),
                "evidence_gap": Noul(
                    instructions=(
                        "At least one ledger item marked DONE appears to lack evidence that "
                        "substantively proves its requirement."
                    ),
                ),
                "completion_semantically_safe": Noul(
                    instructions=(
                        "Ignoring no hard facts, the available semantic evidence supports "
                        "allowing this task to enter its final completion gate now."
                    ),
                ),
                "next_action": Choice(
                    instructions="Choose the safest next Goal Loop action.",
                    criteria={
                        "CONTINUE": "Continue an unresolved requirement or missing deliverable.",
                        "REPAIR": "Repair an implementation or artifact that does not meet acceptance.",
                        "REVALIDATE": "Run validation again because evidence is missing/stale/insufficient.",
                        "ESCALATE": "A genuine ambiguity or external boundary requires a human or stronger reasoning model.",
                        "COMPLETE_CANDIDATE": "All hard requirements appear satisfied and final completion checks may run.",
                    },
                ),
                "premature_completion_risk": Score(
                    instructions="Risk of falsely declaring COMPLETE at this moment.",
                    criteria=[
                        "Negligible",
                        "Low",
                        "Moderate",
                        "High",
                        "Very high",
                    ],
                ),
            },
        )

        route_trace = None
        if isinstance(semantic_result, AdaptiveResult):
            route_trace = semantic_result.trace.model_dump(mode="json")
            semantic = semantic_result.response
            if semantic is None:
                return GoalLoopDecision(
                    hard_gate_passed=True,
                    final_action="ESCALATE",
                    reasons=["adaptive semantic runtime returned no decision response"],
                    semantic={"routing": route_trace},
                )
        else:
            semantic = semantic_result

        answers = semantic.answers
        missing = answers["missing_requirement"]
        evidence_gap = answers["evidence_gap"]
        safe = answers["completion_semantically_safe"]
        next_action = answers["next_action"]
        risk = answers["premature_completion_risk"]

        reasons = list(hard_reasons)
        if missing.probability >= self.policy.missing_requirement_threshold:
            reasons.append(
                f"semantic missing-requirement probability={missing.probability:.3f}"
            )
        if evidence_gap.probability >= self.policy.evidence_gap_threshold:
            reasons.append(f"semantic evidence-gap probability={evidence_gap.probability:.3f}")

        hard_gate_passed = True

        if missing.probability >= self.policy.missing_requirement_threshold:
            action = "CONTINUE"
        elif evidence_gap.probability >= self.policy.evidence_gap_threshold:
            action = "REVALIDATE"
        elif risk.score >= self.policy.high_risk_score:
            action = "REVALIDATE"
            reasons.append(f"premature-completion risk score={risk.score:.3f}")
        elif (
            safe.probability >= self.policy.completion_semantic_threshold
            and next_action.choice == "COMPLETE_CANDIDATE"
        ):
            action = "COMPLETE_CANDIDATE"
        else:
            action = next_action.choice
            if action == "COMPLETE_CANDIDATE":
                action = "REVALIDATE"
                reasons.append(
                    "model suggested completion but semantic completion threshold was not met"
                )

        semantic_payload = semantic.model_dump(mode="json")
        if route_trace is not None:
            semantic_payload["routing"] = route_trace

        return GoalLoopDecision(
            hard_gate_passed=hard_gate_passed,
            final_action=action,
            reasons=reasons,
            semantic=semantic_payload,
        )

    @staticmethod
    def _hard_gate_reasons(state: GoalLoopState) -> list[str]:
        reasons: list[str] = []
        for item in state.ledger:
            if not item.required:
                continue
            if item.status in {"TODO", "IN_PROGRESS"}:
                reasons.append(f"{item.id}: required item is {item.status}")
            elif item.status == "DONE" and not item.evidence:
                reasons.append(f"{item.id}: DONE without evidence")
            elif item.status == "BLOCKED" and not item.evidence:
                reasons.append(f"{item.id}: BLOCKED without evidence")
        if not state.definition_of_done:
            reasons.append("definition_of_done is empty")
        return reasons

    @staticmethod
    def _deterministic_action_for_hard_failure(state: GoalLoopState):
        if any(item.required and item.status == "DONE" and not item.evidence for item in state.ledger):
            return "REVALIDATE"
        if any(item.required and item.status == "BLOCKED" and not item.evidence for item in state.ledger):
            return "ESCALATE"
        return "CONTINUE"
