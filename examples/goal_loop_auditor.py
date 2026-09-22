from openjev import OpenJev
from openjev.goal_loop import GoalLoopAuditor, GoalLoopState, LedgerItem
from openjev.providers import MockProvider

# Offline demo: the provider is deterministic so the architecture can be tested
# without any hosted model.
provider = MockProvider(
    {
        "answers": {
            "missing_requirement": 0.08,
            "evidence_gap": 0.12,
            "completion_semantically_safe": 0.93,
            "next_action": {
                "CONTINUE": 0.01,
                "REPAIR": 0.01,
                "REVALIDATE": 0.02,
                "ESCALATE": 0.01,
                "COMPLETE_CANDIDATE": 0.95,
            },
            "premature_completion_risk": {
                "0": 0.72,
                "1": 0.20,
                "2": 0.06,
                "3": 0.015,
                "4": 0.005,
            },
        }
    }
)

engine = OpenJev(provider)
auditor = GoalLoopAuditor(engine)

state = GoalLoopState(
    project_goal="Ship the requested feature with evidence-backed acceptance.",
    definition_of_done=[
        "All required ledger items are complete.",
        "Required validations passed.",
        "No evidence-free DONE claims.",
    ],
    ledger=[
        LedgerItem(
            id="R1",
            requirement="Implement feature",
            priority="P0",
            status="DONE",
            evidence="tests/test_feature.py passed",
        ),
        LedgerItem(
            id="R2",
            requirement="Run regression checks",
            priority="P0",
            status="DONE",
            evidence="pytest: 24 passed",
        ),
    ],
)

print(auditor.audit(state).model_dump_json(indent=2))
