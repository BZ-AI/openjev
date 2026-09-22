from openjev import OpenJev
from openjev.goal_loop import GoalLoopAuditor
from openjev.providers import MockProvider


provider = MockProvider(
    {
        "missing_requirement": {"probability": 0.10},
        "evidence_gap": {"probability": 0.08},
        "completion_semantically_safe": {"probability": 0.93},
        "next_action": {
            "label": "complete",
            "probabilities": {
                "continue": 0.02,
                "repair": 0.02,
                "escalate": 0.01,
                "complete": 0.95,
            },
        },
        "premature_completion_risk": {
            "probabilities": {"0": 0.70, "1": 0.20, "2": 0.07, "3": 0.02, "4": 0.01}
        },
    }
)
auditor = GoalLoopAuditor(OpenJev(provider))
decision = auditor.evaluate_completion(
    ledger=[
        {
            "id": "implementation",
            "required": True,
            "status": "DONE",
            "evidence": "tests passed",
            "validation_required": True,
            "validation_run": True,
        }
    ],
    state={"task": "Ship the example safely"},
)
print(decision)

