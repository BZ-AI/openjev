# Adaptive Decision Runtime

OpenJev v0.2 is a local-first decision runtime, not another model checkpoint.

The execution order is:

```text
deterministic gates
      ↓
fast typed-decision provider (for example Laya)
      ↓
confidence / calibration / option-count checks
      ├─ acceptable → use fast answer
      └─ uncertain  → escalate to a stronger provider
```

## Why this shape

Independent Laya/Jev measurements show the useful part is not "always use the fastest
model". Fast local models can be excellent on clear, narrow cases and still be
confidently wrong on ambiguous inputs. A single global threshold is also not a universal
truth.

OpenJev therefore keeps routing policy in ordinary code:

- deterministic facts are checked before model inference;
- high-cardinality `Choice` requests may skip the fast backend;
- each question may have its own confidence threshold;
- optional temperature values can make a route more or less conservative;
- probability-normalization anomalies can trigger escalation;
- if no strong backend is configured, the low-confidence result is returned with an
  explicit route reason rather than silently pretending it was safe.

## Laya backend

Laya is optional and is never imported unless selected.

```bash
pip install -e ".[laya]"
```

```python
from openjev import Choice, OpenJev
from openjev.providers import LayaProvider

engine = OpenJev(LayaProvider())
result = engine.evaluate(
    state={"message": "I was charged twice; please refund it."},
    questions={
        "department": Choice(
            instructions="Which team should handle this?",
            criteria={
                "billing": "payments, invoices, refunds",
                "technical": "bugs, outages, errors",
                "sales": "pricing and purchasing",
            },
        )
    },
)
```

On Apple Silicon, the MLX port can be selected without changing OpenJev's decision API:

```bash
pip install -e ".[laya-mlx]"
```

```python
engine = OpenJev(LayaProvider(package="laya_mlx"))
```

The upstream model packages and weights remain governed by their own licenses.

## Strong fallback

`JevProvider` speaks the public System One-style HTTP shape. With the hosted TypeSafe
endpoint it uses `TYPESAFE_API_KEY`. With a custom `base_url`, the same adapter can
also target compatible local/open servers.

```python
from openjev import AdaptiveDecisionRuntime, OpenJev, RoutingPolicy
from openjev.providers import JevProvider, LayaProvider

runtime = AdaptiveDecisionRuntime(
    OpenJev(LayaProvider()),
    OpenJev(JevProvider()),
    policy=RoutingPolicy(
        confidence_threshold=0.60,
        max_fast_choice_options=20,
        question_thresholds={"destructive_action": 0.90},
        temperatures={"intent": 1.25},
    ),
)
```

No remote fallback is called unless you configure one.

## Deterministic gates

Use a gate when the answer is a fact that code already knows.

```python
from openjev import DeterministicGate

gate = DeterministicGate(
    name="tests-must-pass",
    predicate=lambda state, questions: state.get("tests") == "PASS",
    failure_reason="required tests have not passed",
)
```

A failed gate returns a `blocked` route without calling either model.

## Calibration

`openjev.calibration` includes dependency-free helpers for:

- ECE;
- binary and multiclass Brier score;
- temperature scaling;
- a small held-out temperature grid fit.

Calibration must be fitted on representative held-out data. Do not take a temperature
or confidence threshold from a public benchmark and assume it transfers to your traffic.
