from __future__ import annotations

from collections.abc import Mapping

PROBABILITY_TOLERANCE = 1e-6


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
