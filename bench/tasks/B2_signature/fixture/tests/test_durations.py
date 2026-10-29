import pytest
from durations import parse_duration


def test_hours_minutes():
    assert parse_duration("1h30m") == 5400


def test_seconds():
    assert parse_duration("45s") == 45


def test_days():
    assert parse_duration("2d") == 2 * 86400


def test_all_units_with_spaces():
    assert parse_duration("1d 2h 3m 4s") == 86400 + 7200 + 180 + 4


def test_zero():
    assert parse_duration("0") == 0


def test_unknown_unit():
    with pytest.raises(ValueError):
        parse_duration("3w")
