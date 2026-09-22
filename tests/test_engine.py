import pytest

from openjev import Choice, Noul, OpenJev, Score
from openjev.providers import MockProvider


def test_typed_decisions_and_normalization():
    provider = MockProvider(
        {
            "answers": {
                "yes": 0.8,
                "route": {"a": 0.6, "b": 0.2},
                "risk": {"0": 0.2, "1": 0.2, "2": 0.4},
            }
        }
    )
    result = OpenJev(provider).evaluate(
        state={"x": 1},
        questions={
            "yes": Noul(instructions="yes?"),
            "route": Choice(instructions="route?", criteria={"a": None, "b": None}),
            "risk": Score(instructions="risk?", criteria=["low", "mid", "high"]),
        },
    )

    assert result.answers["yes"].value is True
    assert result.answers["route"].choice == "a"
    assert result.answers["route"].probabilities == pytest.approx({"a": 0.75, "b": 0.25})
    assert result.answers["risk"].score == pytest.approx(1.25)
    assert result.debug["probability_diagnostics"]["route"]["normalization_error"] == pytest.approx(0.2)


def test_malformed_output_retries():
    provider = MockProvider(
        [
            {"answers": {"wrong": 0.5}},
            {"answers": {"q": 0.9}},
        ]
    )
    result = OpenJev(provider, malformed_retries=1).evaluate(
        state="x",
        questions={"q": Noul(instructions="q")},
    )
    assert result.answers["q"].probability == 0.9
    assert result.usage.attempts == 2
    assert provider.calls[1]["repair_hint"]


def test_invalid_probability_fails_after_retry():
    provider = MockProvider({"answers": {"q": 1.5}})
    with pytest.raises(ValueError):
        OpenJev(provider, malformed_retries=0).evaluate(
            state="x",
            questions={"q": Noul(instructions="q")},
        )
