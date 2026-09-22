from openjev import (
    AdaptiveDecisionRuntime,
    Choice,
    DeterministicGate,
    OpenJev,
    RoutingPolicy,
)
from openjev.providers import MockProvider


def _choice(prob_a, prob_b):
    return {"answers": {"q": {"a": prob_a, "b": prob_b}}}


def test_deterministic_gate_blocks_before_any_model_call():
    fast_provider = MockProvider(_choice(0.9, 0.1))
    runtime = AdaptiveDecisionRuntime(
        OpenJev(fast_provider),
        gates=[
            DeterministicGate(
                name="must-have-state",
                predicate=lambda state, questions: bool(state.get("ready")),
                failure_reason="state is not ready",
            )
        ],
    )

    result = runtime.evaluate(
        state={"ready": False},
        questions={"q": Choice(criteria={"a": "A", "b": "B"})},
    )

    assert result.trace.route == "blocked"
    assert result.response is None
    assert fast_provider.calls == []


def test_low_confidence_escalates_to_strong_provider():
    fast_provider = MockProvider(_choice(0.51, 0.49))
    strong_provider = MockProvider(_choice(0.05, 0.95))
    runtime = AdaptiveDecisionRuntime(
        OpenJev(fast_provider),
        OpenJev(strong_provider),
        policy=RoutingPolicy(confidence_threshold=0.60),
    )

    result = runtime.evaluate(
        state="ambiguous",
        questions={"q": Choice(criteria={"a": "A", "b": "B"})},
    )

    assert result.trace.route == "strong"
    assert result.trace.escalated is True
    assert result.response.answers["q"].choice == "b"
    assert result.fast_response.answers["q"].choice == "a"
    assert len(fast_provider.calls) == 1
    assert len(strong_provider.calls) == 1


def test_high_confidence_stays_local():
    fast_provider = MockProvider(_choice(0.95, 0.05))
    strong_provider = MockProvider(_choice(0.05, 0.95))
    runtime = AdaptiveDecisionRuntime(
        OpenJev(fast_provider),
        OpenJev(strong_provider),
        policy=RoutingPolicy(confidence_threshold=0.60),
    )

    result = runtime.evaluate(
        state="clear",
        questions={"q": Choice(criteria={"a": "A", "b": "B"})},
    )

    assert result.trace.route == "fast"
    assert result.response.answers["q"].choice == "a"
    assert strong_provider.calls == []


def test_high_cardinality_routes_directly_to_strong():
    labels = {f"label-{i}": f"criterion {i}" for i in range(21)}
    strong_distribution = {label: 0.0 for label in labels}
    strong_distribution["label-7"] = 1.0

    fast_provider = MockProvider({"answers": {"q": strong_distribution}})
    strong_provider = MockProvider({"answers": {"q": strong_distribution}})
    runtime = AdaptiveDecisionRuntime(
        OpenJev(fast_provider),
        OpenJev(strong_provider),
        policy=RoutingPolicy(max_fast_choice_options=20),
    )

    result = runtime.evaluate(
        state="many labels",
        questions={"q": Choice(criteria=labels)},
    )

    assert result.trace.route == "strong"
    assert result.response.answers["q"].choice == "label-7"
    assert fast_provider.calls == []
    assert len(strong_provider.calls) == 1


def test_temperature_can_make_routing_more_conservative():
    fast_provider = MockProvider(_choice(0.9, 0.1))
    strong_provider = MockProvider(_choice(0.2, 0.8))
    runtime = AdaptiveDecisionRuntime(
        OpenJev(fast_provider),
        OpenJev(strong_provider),
        policy=RoutingPolicy(
            confidence_threshold=0.80,
            temperatures={"q": 3.0},
        ),
    )

    result = runtime.evaluate(
        state="needs calibration",
        questions={"q": Choice(criteria={"a": "A", "b": "B"})},
    )

    assert result.trace.route == "strong"
    assert result.trace.fast_confidences["q"] < 0.80
