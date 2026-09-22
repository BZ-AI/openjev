import pytest

from openjev import Choice, Noul, OpenJev, Score
from openjev.providers import MockProvider


def test_engine_normalizes_and_calculates_answers():
    provider = MockProvider(
        {
            "yes": {"probability": 0.8},
            "pick": {"probabilities": {"a": 2, "b": 1}},
            "risk": {"probabilities": {"0": 1, "1": 1, "2": 2}},
        }
    )
    result = OpenJev(provider).evaluate(
        state={"x": 1},
        questions={
            "yes": Noul("is x present?"),
            "pick": Choice("pick", {"a": "A", "b": "B"}),
            "risk": Score("risk", ["low", "mid", "high"]),
        },
    )

    assert result.answers["yes"].decision is True
    assert result.answers["pick"].label == "a"
    assert result.answers["pick"].probabilities["a"] == pytest.approx(2 / 3)
    assert result.answers["risk"].expected_score == pytest.approx(1.25)


def test_engine_rejects_extra_response_keys():
    provider = MockProvider({"q": {"probability": 0.5}, "extra": {}})
    with pytest.raises(ValueError):
        OpenJev(provider).evaluate(state={}, questions={"q": Noul("q")})


def test_engine_retries_malformed_output():
    provider = MockProvider(
        [
            {"q": {"probability": 2}},
            {"q": {"probability": 0.7}},
        ],
        max_retries=1,
    )
    result = OpenJev(provider).evaluate(state={}, questions={"q": Noul("q")})
    assert result.answers["q"].probability == 0.7
    assert provider.calls == 2
    assert len(provider.malformed) == 1

