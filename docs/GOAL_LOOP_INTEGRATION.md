# Goal Loop 1.1.0 / Auditor integration

This document describes the recommended integration between OpenJev and Goal Loop.

## Key architecture change

Do **not** turn Goal Loop into "ask an AI whether the AI is done."

Instead split completion control into two layers:

```text
Layer A — deterministic invariants
  required TODO exists?            -> cannot COMPLETE
  required IN_PROGRESS exists?     -> cannot COMPLETE
  DONE without evidence?           -> cannot COMPLETE
  BLOCKED without evidence?        -> cannot COMPLETE
  mandated validation not run?     -> cannot COMPLETE

Layer B — semantic judgments
  likely requirement omitted?
  evidence semantically sufficient?
  latest user request conflicts with ledger?
  which recovery branch is safest?
  how risky is premature completion?
```

Layer A always wins.

## What to add to Goal Loop 1.1.0

Recommended new events for the existing append-only Auditor ledger:

- `decision_requested`
- `decision_returned`
- `hard_gate_blocked`
- `semantic_missing_requirement`
- `semantic_evidence_gap`
- `completion_candidate_allowed`
- `completion_candidate_denied`
- `human_or_stronger_model_escalation`

Store raw state only when explicitly safe. By default store:

```json
{
  "event_type": "semantic_missing_requirement",
  "payload_sha256": "...",
  "probability": 0.73,
  "threshold": 0.60,
  "decision": true
}
```

## Suggested trigger flow

```text
complex task detected
  -> Goal Loop creates/loads ledger
  -> deterministic trigger check
  -> optional semantic trigger Noul
  -> execute / validate / repair
  -> on every completion candidate:
       deterministic hard gate
       + semantic audit
       + exit gate
```

## Suggested semantic questions

1. `missing_requirement: Noul`
2. `evidence_gap: Noul`
3. `completion_semantically_safe: Noul`
4. `next_action: Choice`
5. `premature_completion_risk: Score`

Do not use one giant "Is this done?" prompt.

## Threshold policy

Start conservative and measure against real labeled sessions.

Example initial policy:

- missing requirement >= 0.60 -> continue / reconcile ledger
- evidence gap >= 0.55 -> revalidate
- completion safe >= 0.85 AND next action is completion candidate -> allow final Exit Gate
- risk expected score >= 3.0/4 -> revalidate/escalate

These are bootstrap values, not universal truths.

## What this adds to the 1.1.0 Auditor direction

The existing 1.1.0 concept already records missed trigger/verification gaps and
privacy-hashed JSONL telemetry. OpenJev adds a reusable semantic decision seam:

```text
Goal Loop = workflow reliability policy
OpenJev   = typed probabilistic semantic judgment
```

This separation matters because the same OpenJev layer can later be used by other
agent frameworks without importing the entire Goal Loop policy.
