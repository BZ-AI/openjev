from __future__ import annotations

import math
from collections.abc import Mapping

PROBABILITY_TOLERANCE = 1e-6

_EPSILON = 1e-12


def normalize_distribution(probabilities: Mapping[str, float]) -> tuple[dict[str, float], float]:
    if not probabilities:
        raise ValueError("Probability distribution cannot be empty.")

    clean: dict[str, float] = {}
    for label, value in probabilities.items():
        number = float(value)
        if number < 0.0 or number > 1.0:
            raise ValueError(f"Probability for {label!r} must be in [0, 1].")
        clean[str(label)] = number

    total = sum(clean.values())
    error = abs(total - 1.0)
    if error <= PROBABILITY_TOLERANCE:
        return clean, error

    if total == 0:
        uniform = 1.0 / len(clean)
        return {label: uniform for label in clean}, error

    return {label: value / total for label, value in clean.items()}, error


def choice_confidence(probabilities: Mapping[str, float]) -> float:
    probs, _ = normalize_distribution(probabilities)
    if len(probs) == 1:
        return 1.0
    peak = max(probs.values())
    uniform = 1.0 / len(probs)
    return max(0.0, min(1.0, (peak - uniform) / (1.0 - uniform)))


def temperature_scale_distribution(
    probabilities: Mapping[str, float],
    temperature: float,
) -> dict[str, float]:
    """Apply temperature scaling to an already-normalized categorical distribution."""
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    probs, _ = normalize_distribution(probabilities)
    powered = {
        label: max(value, _EPSILON) ** (1.0 / temperature)
        for label, value in probs.items()
    }
    scaled, _ = normalize_distribution(powered)
    return scaled


def temperature_scale_probability(probability: float, temperature: float) -> float:
    p = float(probability)
    if not 0.0 <= p <= 1.0:
        raise ValueError("probability must be in [0,1]")
    scaled = temperature_scale_distribution({"true": p, "false": 1.0 - p}, temperature)
    return scaled["true"]


def expected_calibration_error(
    confidences: list[float],
    correctness: list[bool],
    *,
    bins: int = 10,
) -> float:
    if len(confidences) != len(correctness):
        raise ValueError("confidences and correctness must have equal length")
    if not confidences:
        return 0.0
    if bins <= 0:
        raise ValueError("bins must be > 0")

    total = len(confidences)
    error = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        members = [
            i
            for i, confidence in enumerate(confidences)
            if (confidence > low or index == 0) and confidence <= high
        ]
        if not members:
            continue
        mean_confidence = sum(confidences[i] for i in members) / len(members)
        accuracy = sum(1.0 if correctness[i] else 0.0 for i in members) / len(members)
        error += len(members) / total * abs(mean_confidence - accuracy)
    return error


def brier_score_binary(probability: float, label: bool) -> float:
    target = 1.0 if label else 0.0
    return (float(probability) - target) ** 2


def multiclass_brier_score(probabilities: Mapping[str, float], label: str) -> float:
    probs, _ = normalize_distribution(probabilities)
    if label not in probs:
        raise ValueError(f"label {label!r} is not present in the distribution")
    return sum((probability - (1.0 if key == label else 0.0)) ** 2 for key, probability in probs.items())


def fit_temperature_grid(
    distributions: list[Mapping[str, float]],
    labels: list[str],
    *,
    candidates: tuple[float, ...] = (0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0),
) -> float:
    """Small dependency-free temperature fit using held-out negative log likelihood."""
    if len(distributions) != len(labels):
        raise ValueError("distributions and labels must have equal length")
    if not distributions:
        raise ValueError("at least one calibration example is required")

    best_temperature = 1.0
    best_loss = float("inf")
    for temperature in candidates:
        if temperature <= 0:
            continue
        loss = 0.0
        for distribution, label in zip(distributions, labels, strict=True):
            scaled = temperature_scale_distribution(distribution, temperature)
            if label not in scaled:
                raise ValueError(f"label {label!r} is not present in a calibration distribution")
            loss -= math.log(max(scaled[label], _EPSILON))
        if loss < best_loss:
            best_loss = loss
            best_temperature = temperature
    return best_temperature


def score_expected_value(probabilities: Mapping[str, float]) -> float:
    probs, _ = normalize_distribution(probabilities)
    total = 0.0
    for label, p in probs.items():
        total += int(label) * p
    return total


def score_confidence(probabilities: Mapping[str, float]) -> float:
    probs, _ = normalize_distribution(probabilities)
    ordered = [probs[str(i)] for i in range(len(probs))]
    if len(ordered) == 1:
        return 1.0

    mode = max(range(len(ordered)), key=ordered.__getitem__)
    observed_mad = sum(p * abs(i - mode) for i, p in enumerate(ordered))

    midpoint = (len(ordered) - 1) / 2
    uniform_mad = sum(abs(i - midpoint) for i in range(len(ordered))) / len(ordered)
    if uniform_mad == 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - observed_mad / uniform_mad))
