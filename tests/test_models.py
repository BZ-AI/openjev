import pytest
from pydantic import ValidationError

from openjev import Choice, Score


def test_choice_needs_two_labels():
    with pytest.raises(ValidationError):
        Choice(instructions="x", criteria={"only": None})


def test_score_needs_two_levels():
    with pytest.raises(ValidationError):
        Score(instructions="x", criteria=["only"])
