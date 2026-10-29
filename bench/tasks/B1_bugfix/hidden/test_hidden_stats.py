import pytest
from stats import median


def test_median_empty_raises():
    with pytest.raises(ValueError):
        median([])


def test_median_does_not_modify_input():
    xs = [3, 1, 2]
    median(xs)
    assert xs == [3, 1, 2]


def test_median_floats_even():
    assert median([1.5, 0.5]) == 1.0
