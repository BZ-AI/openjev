import pytest

from openjev import Choice, Noul, Score


def test_noul_requires_instructions():
    with pytest.raises(ValueError):
        Noul(instructions="")


def test_choice_requires_two_labels():
    with pytest.raises(ValueError):
        Choice(instructions="pick", criteria={"one": "only"})


def test_score_requires_two_levels():
    with pytest.raises(ValueError):
        Score(instructions="rate", criteria=["only"])

