# OpenJev

**OpenJev is an independent, clean-room open-source project for typed probabilistic decisions.**

It is **not Jev**, does not contain TypeSafe AI's proprietary model, weights, sampler,
training code, or private implementation, and is not affiliated with or endorsed by TypeSafe AI.

The goal is to make this programming shape open and portable:

```text
application state
    + typed questions
    -> probabilities / typed decisions
    -> deterministic code policy
```

OpenJev v0.2 is an adaptive decision runtime: deterministic rules first, a fast
local typed-decision model second, and a stronger fallback only when the route needs it.
It provides:

- `Noul`: yes/no probability.
- `Choice`: one label from a fixed set + probability distribution + confidence.
- `Score`: ordered rubric + probability distribution + expected score + confidence.
- strict request validation;
- response schema generation;
- probability normalization;
- malformed-output retry hooks;
- provider-independent engine;
- optional Laya and Laya-MLX local providers (loaded lazily; weights are not vendored);
- a System One-compatible HTTP/Jev provider for remote or local compatible servers;
- deterministic pre-model gates;
- confidence-, calibration-, and option-count-aware local-first escalation;
- reproducible accuracy / ECE / Brier / latency benchmarks and cascade sweeps;
- tamper-evident privacy-hashed JSONL audit events;
- a Goal Loop / Auditor integration showing how deterministic hard gates and
  probabilistic semantic judgments can be composed safely.

## Why this exists

Most agent workflows do not need free-form generation for every decision.
Many steps are better represented as narrow judgments:

- Should this complex task trigger supervision?
- Is a requirement likely missing from the ledger?
- Does the evidence actually support a `DONE` claim?
- Which recovery branch should run next?
- How risky is it to allow completion?

OpenJev keeps the workflow in code and uses a model only for the fuzzy semantic parts.

## Quick start

```bash
python -m pip install -e .
python examples/goal_loop_auditor.py
```

To use an OpenAI-compatible backend:

```python
from openjev import OpenJev, Choice, Noul, Score
from openjev.providers import OpenAICompatibleProvider

provider = OpenAICompatibleProvider(
    model="your-model",
    api_key="...",
    base_url="http://localhost:8000/v1",
)

jev = OpenJev(provider)

result = jev.evaluate(
    state={"task": "A long-running multi-file agent task", "tests_failed": 2},
    questions={
        "needs_supervision": Noul(
            instructions="This task should run under a persistent goal/validation supervisor."
        ),
        "next_action": Choice(
            instructions="Choose the safest next workflow action.",
            criteria={
                "continue": "Proceed with the next unresolved requirement.",
                "repair": "Repair a failed implementation or validation.",
                "escalate": "A human or stronger reasoning model is needed.",
            },
        ),
        "risk": Score(
            instructions="How risky would it be to declare the task complete now?",
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

print(result.model_dump_json(indent=2))
```

## Adaptive local-first runtime

Install the optional local backend:

```bash
python -m pip install -e '.[laya]'
```

Then compose a fast local engine with an optional strong fallback:

```python
from openjev import AdaptiveDecisionRuntime, OpenJev, RoutingPolicy
from openjev.providers import JevProvider, LayaProvider

runtime = AdaptiveDecisionRuntime(
    OpenJev(LayaProvider()),
    OpenJev(JevProvider()),  # only if you intentionally configure the hosted/API fallback
    policy=RoutingPolicy(confidence_threshold=0.60, max_fast_choice_options=20),
)
```

See `docs/ADAPTIVE_RUNTIME.md` for gates, per-question thresholds and temperature calibration.

## Reproduce the comparisons

The MIT-licensed 40-case Chinese support benchmark discussed in the independent
Laya/Jev cascade evaluation is included with attribution:

```bash
openjev-bench benchmarks/yibie_support_40.json --fast laya
```

Add `--strong jev` only when you explicitly want to make hosted Jev calls. The second
500-example multi-domain benchmark is supported through a converter instead of copying
source texts whose datasets restrict redistribution. See `docs/BENCHMARKS.md`.

## Goal Loop integration

See:

- `src/openjev/goal_loop.py`
- `examples/goal_loop_auditor.py`
- `docs/GOAL_LOOP_INTEGRATION.md`

The core rule is deliberate:

> Hard completion facts stay deterministic. Semantic ambiguity may use a probabilistic model.

For example, if a mandatory ledger item is `TODO`, no model is allowed to override
that and declare completion.

## Project status

`0.2.0` is an adaptive runtime, **not a new trained foundation model**.
The current focus is making open/hosted decision models useful in real agents: route the
right cases locally, escalate uncertainty, measure calibration, and keep hard facts in code.
A first-party trained model is deferred until real workload evidence says it is needed.

## Compatibility position

OpenJev uses broadly similar public concepts (`state`, typed questions, probabilities)
because those are useful programming primitives. Its public Python API and wire format
are independently implemented and intentionally not advertised as a drop-in replacement
for TypeSafe's hosted service.

## License

MIT. See `LICENSE`.

Third-party acknowledgements and the clean-room boundary are documented in
`THIRD_PARTY_NOTICES.md`.
