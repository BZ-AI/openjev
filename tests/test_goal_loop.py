from openjev import OpenJev
from openjev.goal_loop import GoalLoopAuditor
from openjev.providers import MockProvider


def _safe_provider():
    return MockProvider(
        {
            "missing_requirement": {"probability": 0.1},
            "evidence_gap": {"probability": 0.1},
            "completion_semantically_safe": {"probability": 0.95},
            "next_action": {
                "label": "complete",
                "probabilities": {
                    "continue": 0.01,
                    "repair": 0.01,
                    "escalate": 0.01,
                    "complete": 0.97,
                },
            },
            "premature_completion_risk": {
                "probabilities": {"0": 0.8, "1": 0.1, "2": 0.05, "3": 0.03, "4": 0.02}
            },
        }
    )


def test_hard_gate_wins_without_calling_model():
    provider = _safe_provider()
    auditor = GoalLoopAuditor(OpenJev(provider))
    decision = auditor.evaluate_completion(
        ledger=[{"id": "required", "required": True, "status": "TODO"}],
        state={},
    )
    assert decision.allowed is False
    assert decision.reason == "hard_gate"
    assert provider.calls == 0


def test_safe_semantic_gate_allows_candidate():
    auditor = GoalLoopAuditor(OpenJev(_safe_provider()))
    decision = auditor.evaluate_completion(
        ledger=[
            {
                "id": "required",
                "required": True,
                "status": "DONE",
                "evidence": "pytest passed",
                "validation_required": True,
                "validation_run": True,
            }
        ],
        state={},
    )
    assert decision.allowed is True

