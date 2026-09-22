from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audit import HashChainAuditLog
from .engine import OpenJev
from .types import Choice, Noul, Score


@dataclass(frozen=True)
class AuditDecision:
    allowed: bool
    reason: str
    blockers: list[str]
    semantic: dict[str, Any] | None


class GoalLoopAuditor:
    def __init__(
        self,
        jev: OpenJev,
        *,
        audit_log: HashChainAuditLog | None = None,
        missing_threshold: float = 0.60,
        evidence_gap_threshold: float = 0.55,
        completion_safe_threshold: float = 0.85,
        risk_threshold: float = 3.0,
    ):
        self.jev = jev
        self.audit_log = audit_log
        self.missing_threshold = missing_threshold
        self.evidence_gap_threshold = evidence_gap_threshold
        self.completion_safe_threshold = completion_safe_threshold
        self.risk_threshold = risk_threshold

    @staticmethod
    def deterministic_blockers(ledger: list[dict[str, Any]]) -> list[str]:
        blockers: list[str] = []
        for index, item in enumerate(ledger):
            required = bool(item.get("required", True))
            if not required:
                continue
            status = str(item.get("status", "")).upper()
            evidence = item.get("evidence")
            validation_required = bool(item.get("validation_required", False))
            validation_run = bool(item.get("validation_run", False))
            name = item.get("id") or item.get("name") or f"item-{index + 1}"

            if status in {"TODO", "IN_PROGRESS", ""}:
                blockers.append(f"{name}: required item is {status or 'UNSET'}")
            elif status == "DONE" and not evidence:
                blockers.append(f"{name}: DONE without evidence")
            elif status == "BLOCKED" and not evidence:
                blockers.append(f"{name}: BLOCKED without evidence")
            if validation_required and not validation_run:
                blockers.append(f"{name}: mandated validation not run")
        return blockers

    def evaluate_completion(
        self,
        *,
        ledger: list[dict[str, Any]],
        state: dict[str, Any],
    ) -> AuditDecision:
        blockers = self.deterministic_blockers(ledger)
        if blockers:
            self._log("hard_gate_blocked", {"blockers": blockers}, decision=False)
            return AuditDecision(False, "hard_gate", blockers, None)

        self._log("decision_requested", {"kind": "completion_candidate"})
        result = self.jev.evaluate(
            state={"ledger": ledger, **state},
            questions={
                "missing_requirement": Noul(
                    instructions="Is a material user requirement likely missing from the ledger?"
                ),
                "evidence_gap": Noul(
                    instructions="Is the current completion evidence semantically insufficient?"
                ),
                "completion_semantically_safe": Noul(
                    instructions="Is it semantically safe to allow the final deterministic exit gate?"
                ),
                "next_action": Choice(
                    instructions="Choose the safest next workflow action.",
                    criteria={
                        "continue": "Continue an unresolved requirement.",
                        "repair": "Repair implementation or evidence.",
                        "escalate": "Escalate to a human or stronger model.",
                        "complete": "Proceed to the final deterministic exit gate.",
                    },
                ),
                "premature_completion_risk": Score(
                    instructions="How risky is it to declare completion now?",
                    criteria=[
                        "Very low risk",
                        "Low risk",
                        "Moderate risk",
                        "High risk",
                        "Very high risk",
                    ],
                ),
            },
        )
        answers = result.answers
        missing = answers["missing_requirement"]
        evidence_gap = answers["evidence_gap"]
        completion_safe = answers["completion_semantically_safe"]
        next_action = answers["next_action"]
        risk = answers["premature_completion_risk"]

        semantic = {
            "missing_requirement": missing.probability,
            "evidence_gap": evidence_gap.probability,
            "completion_semantically_safe": completion_safe.probability,
            "next_action": next_action.label,
            "premature_completion_risk": risk.expected_score,
        }

        denied_reasons: list[str] = []
        if missing.probability >= self.missing_threshold:
            denied_reasons.append("semantic_missing_requirement")
            self._log(
                "semantic_missing_requirement",
                semantic,
                probability=missing.probability,
                threshold=self.missing_threshold,
                decision=True,
            )
        if evidence_gap.probability >= self.evidence_gap_threshold:
            denied_reasons.append("semantic_evidence_gap")
            self._log(
                "semantic_evidence_gap",
                semantic,
                probability=evidence_gap.probability,
                threshold=self.evidence_gap_threshold,
                decision=True,
            )
        if completion_safe.probability < self.completion_safe_threshold:
            denied_reasons.append("completion_not_safe")
        if next_action.label != "complete":
            denied_reasons.append(f"next_action={next_action.label}")
        if risk.expected_score >= self.risk_threshold:
            denied_reasons.append("premature_completion_risk")

        allowed = not denied_reasons
        self._log("decision_returned", semantic, decision=allowed)
        self._log(
            "completion_candidate_allowed" if allowed else "completion_candidate_denied",
            {"reasons": denied_reasons, **semantic},
            decision=allowed,
        )
        return AuditDecision(
            allowed=allowed,
            reason="semantic_gate_allowed" if allowed else "semantic_gate_denied",
            blockers=denied_reasons,
            semantic=semantic,
        )

    def _log(
        self,
        event_type: str,
        payload: Any,
        *,
        probability: float | None = None,
        threshold: float | None = None,
        decision: bool | None = None,
    ) -> None:
        if self.audit_log is not None:
            self.audit_log.append(
                event_type,
                payload,
                probability=probability,
                threshold=threshold,
                decision=decision,
            )

