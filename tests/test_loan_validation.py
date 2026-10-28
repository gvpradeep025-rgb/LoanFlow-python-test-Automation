"""Legacy loan eligibility tests backed by the shared LoanFlow validation engine."""

import pytest

from loanflow import validators


def is_eligible_age(age: int) -> bool:
    """Delegate to the shared fictional eligibility rule."""
    return validators.is_eligible_age(age)


@pytest.mark.parametrize(
    "age, expected",
    [
        (25, True),
        (17, False),
        (21, True),
        (18, False),
        (16, False),
    ],
)
def test_is_eligible_age(age: int, expected: bool) -> None:
    assert is_eligible_age(age) is expected
