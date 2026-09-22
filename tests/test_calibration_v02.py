import pytest

from openjev.calibration import (
    expected_calibration_error,
    fit_temperature_grid,
    temperature_scale_distribution,
    temperature_scale_probability,
)


def test_temperature_scaling_softens_overconfident_distribution():
    scaled = temperature_scale_distribution({"a": 0.9, "b": 0.1}, 2.0)
    assert 0.5 < scaled["a"] < 0.9
    assert sum(scaled.values()) == pytest.approx(1.0)

    binary = temperature_scale_probability(0.9, 2.0)
    assert 0.5 < binary < 0.9


def test_ece_and_temperature_fit_are_dependency_free():
    assert expected_calibration_error([0.9, 0.8], [True, True]) == pytest.approx(0.15)
    temperature = fit_temperature_grid(
        [{"a": 0.99, "b": 0.01}, {"a": 0.99, "b": 0.01}],
        ["a", "b"],
        candidates=(1.0, 2.0, 3.0),
    )
    assert temperature == 3.0
