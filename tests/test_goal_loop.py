from openjev import OpenJev
from openjev.goal_loop import GoalLoopAuditor, GoalLoopState, LedgerItem
from openjev.providers import MockProvider


def semantic_ok_provider():
    return MockProvider(
        {
            "answers": {
                "missing_requirement": 0.05,
                "evidence_gap": 0.05,
                "completion_semantically_safe": 0.95,
                "next_action": {
                    "CONTINUE": 0.01,
                    "REPAIR": 0.01,
                    "REVALIDATE": 0.01,
                    "ESCALATE": 0.01,
                    "COMPLETE_CANDIDATE": 0.96,
                },
                "premature_completion_risk": {
                    "0": 0.9,
                    "1": 0.07,
                    "2": 0.02,
                    "3": 0.005,
                    "4": 0.005,
                },
            }
        }
    )


def test_required_todo_cannot_be_overridden_by_model():
    auditor = GoalLoopAuditor(OpenJev(semantic_ok_provider()))
    state = GoalLoopState(
        project_goal="ship",
        definition_of_done=["done"],
        ledger=[
            LedgerItem(
                id="R1",
                requirement="hard item",
                priority="P0",
                status="TODO",
                required=True,
            )
        ],
    )
    decision = auditor.audit(state)
    assert decision.hard_gate_passed is False
    assert decision.final_action == "CONTINUE"


def test_done_without_evidence_forces_revalidation():
    auditor = GoalLoopAuditor(OpenJev(semantic_ok_provider()))
    state = GoalLoopState(
        project_goal="ship",
        definition_of_done=["done"],
        ledger=[
            LedgerItem(
                id="R1",
                requirement="implemented",
                priority="P0",
                status="DONE",
                evidence=None,
            )
        ],
    )
    decision = auditor.audit(state)
    assert decision.hard_gate_passed is False
    assert decision.final_action == "REVALIDATE"


def test_completion_candidate_allowed_only_after_hard_and_semantic_gates():
    auditor = GoalLoopAuditor(OpenJev(semantic_ok_provider()))
    state = GoalLoopState(
        project_goal="ship",
        definition_of_done=["done"],
        ledger=[
            LedgerItem(
                id="R1",
                requirement="implemented",
                priority="P0",
                status="DONE",
                evidence="pytest passed",
            )
        ],
    )
    decision = auditor.audit(state)
    assert decision.hard_gate_passed is True
    assert decision.final_action == "COMPLETE_CANDIDATE"
