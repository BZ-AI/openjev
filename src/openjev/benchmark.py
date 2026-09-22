from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .calibration import (
    brier_score_binary,
    expected_calibration_error,
    multiclass_brier_score,
)
from .engine import OpenJev
from .models import Choice, ChoiceAnswer, Noul, NoulAnswer, Question, Score, ScoreAnswer


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BenchmarkCase(_StrictModel):
    id: str
    state: Any
    question_id: str = "q"
    question: dict[str, Any]
    label: Any
    tier: str | None = None
    domain: str | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)


class CaseResult(_StrictModel):
    id: str
    provider: str
    primitive: str
    prediction: Any
    label: Any
    confidence: float
    correct: bool
    latency_ms: float
    brier: float
    expected_score: float | None = None
    tier: str | None = None
    domain: str | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    probabilities: dict[str, float] = Field(default_factory=dict)


class MetricSummary(_StrictModel):
    n: int
    accuracy: float
    ece: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    brier: float
    score_mae: float | None = None


class ProviderBenchmark(_StrictModel):
    provider: str
    summary: MetricSummary
    by_tier: dict[str, MetricSummary] = Field(default_factory=dict)
    by_domain: dict[str, MetricSummary] = Field(default_factory=dict)
    by_language: dict[str, MetricSummary] = Field(default_factory=dict)
    by_primitive: dict[str, MetricSummary] = Field(default_factory=dict)
    cases: list[CaseResult]


class CascadePoint(_StrictModel):
    threshold: float
    n: int
    escalation_rate: float
    accuracy: float
    ece: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    source = Path(path)
    text = source.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if text.startswith("["):
        rows = json.loads(text)
        return [BenchmarkCase.model_validate(row) for row in rows]

    if text.startswith("{"):
        payload = json.loads(text)
        if "criteria" in payload and "cases" in payload:
            return _load_support_cascade_cases(payload)
        return [BenchmarkCase.model_validate(payload)]

    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [BenchmarkCase.model_validate(row) for row in rows]


def _load_support_cascade_cases(payload: dict[str, Any]) -> list[BenchmarkCase]:
    """Load the compact support-cascade format used by yibie/laya-jev-lab."""
    criteria = payload["criteria"]
    question = {
        "type": "choice",
        "instructions": "这条客服消息主要属于哪个类别？",
        "criteria": criteria,
    }
    tier_map = {"清晰": "clear", "模糊": "ambiguous", "边界": "boundary"}
    cases = []
    for index, row in enumerate(payload["cases"], start=1):
        if len(row) != 3:
            raise ValueError("support cascade case rows must be [text, label, tier]")
        text, label, tier = row
        cases.append(
            BenchmarkCase(
                id=f"support-{index:02d}",
                state=text,
                question_id="intent",
                question=question,
                label=label,
                tier=tier_map.get(str(tier), str(tier)),
                domain="support",
                language="zh",
                tags=["third-party-benchmark"],
            )
        )
    return cases


def question_from_spec(spec: dict[str, Any]) -> Question:
    qtype = spec.get("type")
    if qtype == "choice":
        return Choice(**spec)
    if qtype == "noul":
        return Noul(**spec)
    if qtype == "score":
        return Score(**spec)
    raise ValueError(f"unknown benchmark question type {qtype!r}")


def evaluate_cases(
    engine: OpenJev,
    cases: list[BenchmarkCase],
    *,
    provider_name: str,
) -> ProviderBenchmark:
    if not cases:
        raise ValueError("benchmark requires at least one case")

    results: list[CaseResult] = []
    for case in cases:
        question = question_from_spec(case.question)
        response = engine.evaluate(
            state=case.state,
            questions={case.question_id: question},
        )
        answer = response.answers[case.question_id]
        result = _case_result(case, answer, response.usage.latency_ms or 0.0, provider_name)
        results.append(result)

    return ProviderBenchmark(
        provider=provider_name,
        summary=summarize(results),
        by_tier=_group_summaries(results, "tier"),
        by_domain=_group_summaries(results, "domain"),
        by_language=_group_summaries(results, "language"),
        by_primitive=_group_summaries(results, "primitive"),
        cases=results,
    )


def cascade_sweep(
    fast: ProviderBenchmark,
    strong: ProviderBenchmark,
    thresholds: list[float],
) -> list[CascadePoint]:
    fast_by_id = {row.id: row for row in fast.cases}
    strong_by_id = {row.id: row for row in strong.cases}
    if set(fast_by_id) != set(strong_by_id):
        raise ValueError("fast and strong benchmarks must contain the same case ids")

    points: list[CascadePoint] = []
    for threshold in thresholds:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("cascade thresholds must be in [0,1]")

        selected: list[CaseResult] = []
        latencies: list[float] = []
        escalations = 0
        for case_id, fast_row in fast_by_id.items():
            strong_row = strong_by_id[case_id]
            if fast_row.confidence >= threshold:
                selected.append(fast_row)
                latencies.append(fast_row.latency_ms)
            else:
                escalations += 1
                selected.append(strong_row)
                latencies.append(fast_row.latency_ms + strong_row.latency_ms)

        correctness = [row.correct for row in selected]
        confidences = [row.confidence for row in selected]
        ordered_latencies = sorted(latencies)
        points.append(
            CascadePoint(
                threshold=threshold,
                n=len(selected),
                escalation_rate=escalations / len(selected),
                accuracy=sum(correctness) / len(selected),
                ece=expected_calibration_error(confidences, correctness),
                mean_latency_ms=sum(latencies) / len(latencies),
                p50_latency_ms=_percentile(ordered_latencies, 0.50),
                p95_latency_ms=_percentile(ordered_latencies, 0.95),
            )
        )
    return points


def summarize(rows: list[CaseResult]) -> MetricSummary:
    if not rows:
        raise ValueError("cannot summarize an empty result set")
    latencies = sorted(row.latency_ms for row in rows)
    score_rows = [row for row in rows if row.expected_score is not None]
    score_mae = None
    if score_rows:
        score_mae = sum(
            abs(float(row.expected_score) - float(row.label))
            for row in score_rows
        ) / len(score_rows)

    return MetricSummary(
        n=len(rows),
        accuracy=sum(row.correct for row in rows) / len(rows),
        ece=expected_calibration_error(
            [row.confidence for row in rows],
            [row.correct for row in rows],
        ),
        mean_latency_ms=sum(latencies) / len(latencies),
        p50_latency_ms=_percentile(latencies, 0.50),
        p95_latency_ms=_percentile(latencies, 0.95),
        brier=sum(row.brier for row in rows) / len(rows),
        score_mae=score_mae,
    )


def _case_result(
    case: BenchmarkCase,
    answer: NoulAnswer | ChoiceAnswer | ScoreAnswer,
    latency_ms: float,
    provider_name: str,
) -> CaseResult:
    if isinstance(answer, NoulAnswer):
        label = _coerce_bool(case.label)
        probabilities = {
            "false": 1.0 - answer.probability,
            "true": answer.probability,
        }
        prediction = answer.value
        confidence = answer.confidence
        brier = brier_score_binary(answer.probability, label)
        expected_score = None
        primitive = "noul"
    elif isinstance(answer, ChoiceAnswer):
        label = str(case.label)
        probabilities = dict(answer.probabilities)
        prediction = answer.choice
        confidence = answer.confidence
        brier = multiclass_brier_score(probabilities, label)
        expected_score = None
        primitive = "choice"
    elif isinstance(answer, ScoreAnswer):
        label = int(case.label)
        probabilities = dict(answer.probabilities)
        prediction = int(max(probabilities, key=probabilities.get))
        confidence = answer.confidence
        brier = multiclass_brier_score(probabilities, str(label))
        expected_score = answer.score
        primitive = "score"
    else:
        raise TypeError(f"unsupported benchmark answer {type(answer)!r}")

    return CaseResult(
        id=case.id,
        provider=provider_name,
        primitive=primitive,
        prediction=prediction,
        label=label,
        confidence=confidence,
        correct=prediction == label,
        latency_ms=float(latency_ms),
        brier=brier,
        expected_score=expected_score,
        tier=case.tier,
        domain=case.domain,
        language=case.language,
        tags=list(case.tags),
        probabilities=probabilities,
    )


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise ValueError(f"noul benchmark label must be boolean, got {value!r}")


def _group_summaries(rows: list[CaseResult], field_name: str) -> dict[str, MetricSummary]:
    groups: dict[str, list[CaseResult]] = defaultdict(list)
    for row in rows:
        value = getattr(row, field_name)
        if value is not None:
            groups[str(value)].append(row)
    return {name: summarize(items) for name, items in sorted(groups.items())}


def _percentile(ordered_values: list[float], q: float) -> float:
    if not ordered_values:
        return 0.0
    if len(ordered_values) == 1:
        return ordered_values[0]
    index = round((len(ordered_values) - 1) * q)
    return ordered_values[max(0, min(index, len(ordered_values) - 1))]


def render_summary_table(report: ProviderBenchmark) -> str:
    summary = report.summary
    return (
        f"{report.provider}: n={summary.n} "
        f"accuracy={summary.accuracy:.3f} ece={summary.ece:.3f} "
        f"brier={summary.brier:.3f} p50={summary.p50_latency_ms:.1f}ms "
        f"p95={summary.p95_latency_ms:.1f}ms"
    )


def median_confidence(report: ProviderBenchmark) -> float:
    return statistics.median(row.confidence for row in report.cases)
