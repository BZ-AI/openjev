from pathlib import Path

import pytest

from openjev import OpenJev
from openjev.benchmark import BenchmarkCase, cascade_sweep, evaluate_cases, load_cases
from openjev.providers import MockProvider


def _cases():
    question = {
        "type": "choice",
        "instructions": "route",
        "criteria": {"a": "A", "b": "B"},
    }
    return [
        BenchmarkCase(
            id="clear",
            state="clear",
            question=question,
            label="a",
            tier="clear",
            domain="support",
            language="en",
        ),
        BenchmarkCase(
            id="ambiguous",
            state="ambiguous",
            question=question,
            label="b",
            tier="ambiguous",
            domain="support",
            language="en",
        ),
    ]


def test_loads_vendored_yibie_support_format():
    root = Path(__file__).resolve().parents[1]
    cases = load_cases(root / "benchmarks" / "yibie_support_40.json")
    assert len(cases) == 40
    assert sum(case.tier == "clear" for case in cases) == 20
    assert sum(case.tier == "ambiguous" for case in cases) == 10
    assert sum(case.tier == "boundary" for case in cases) == 10
    assert all(case.language == "zh" for case in cases)


def test_benchmark_metrics_and_cascade_sweep():
    fast = OpenJev(
        MockProvider(
            [
                {"answers": {"q": {"a": 0.95, "b": 0.05}}},
                {"answers": {"q": {"a": 0.55, "b": 0.45}}},
            ]
        )
    )
    strong = OpenJev(
        MockProvider(
            [
                {"answers": {"q": {"a": 0.9, "b": 0.1}}},
                {"answers": {"q": {"a": 0.1, "b": 0.9}}},
            ]
        )
    )

    fast_report = evaluate_cases(fast, _cases(), provider_name="fast")
    strong_report = evaluate_cases(strong, _cases(), provider_name="strong")

    assert fast_report.summary.accuracy == pytest.approx(0.5)
    assert strong_report.summary.accuracy == pytest.approx(1.0)
    assert fast_report.by_tier["clear"].accuracy == pytest.approx(1.0)

    sweep = cascade_sweep(fast_report, strong_report, [0.5, 0.89])
    assert sweep[0].escalation_rate == pytest.approx(0.5)
    assert sweep[0].accuracy == pytest.approx(1.0)
    assert sweep[1].escalation_rate == pytest.approx(0.5)
    assert sweep[1].accuracy == pytest.approx(1.0)
