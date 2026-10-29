import pytest
from durations import parse_duration


def test_any_order():
    assert parse_duration("30m1h") == 5400


def test_surrounding_whitespace():
    assert parse_duration("  10m ") == 600


@pytest.mark.parametrize("bad", ["", "1.5h", "1h2h", "15", "h", "1h x"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)


def test_returns_int():
    assert isinstance(parse_duration("1m"), int)
