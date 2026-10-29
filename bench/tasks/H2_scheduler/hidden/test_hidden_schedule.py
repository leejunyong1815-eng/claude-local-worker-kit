import pytest
from schedule import schedule, CycleError

DEPS = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"], "e": [], "f": ["e", "d"], "g": ["c"]}
DUR = {"a": 3, "b": 2, "c": 4, "d": 1, "e": 5, "f": 2, "g": 1}


def test_diamond_with_two_workers():
    assert schedule(DEPS, DUR, 2) == [
        ("a", 0, 3, 0), ("e", 0, 5, 1), ("b", 3, 5, 0), ("c", 5, 9, 0), ("d", 9, 10, 0), ("g", 9, 10, 1),
        ("f", 10, 12, 0),
    ]


def test_three_workers():
    assert schedule(DEPS, DUR, 3) == [
        ("a", 0, 3, 0), ("e", 0, 5, 1), ("b", 3, 5, 0), ("c", 3, 7, 2), ("d", 7, 8, 0), ("g", 7, 8, 1),
        ("f", 8, 10, 0),
    ]


def test_cycle_reported_from_smallest_name():
    with pytest.raises(CycleError) as e:
        schedule({"x": ["y"], "y": ["z"], "z": ["x"], "m": ["x"]}, {"x": 1, "y": 1, "z": 1, "m": 1}, 2)
    assert e.value.cycle == ["x", "y", "z", "x"]


def test_self_loop():
    with pytest.raises(CycleError) as e:
        schedule({"a": ["a"]}, {"a": 1}, 1)
    assert e.value.cycle == ["a", "a"]


@pytest.mark.parametrize("deps,dur,w", [({"a": []}, {"a": 0}, 1), ({"a": []}, {}, 1), ({"a": []}, {"a": 1}, 0)])
def test_invalid_inputs(deps, dur, w):
    with pytest.raises(ValueError):
        schedule(deps, dur, w)


def test_empty():
    assert schedule({}, {}, 2) == []
