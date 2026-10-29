import pytest
from schedule import schedule, CycleError


def test_chain_one_worker():
    deps = {"a": [], "b": ["a"], "c": ["b"]}
    dur = {"a": 2, "b": 1, "c": 3}
    assert schedule(deps, dur, 1) == [("a", 0, 2, 0), ("b", 2, 3, 0), ("c", 3, 6, 0)]


def test_parallel_two_workers_alphabetical():
    deps = {"a": [], "b": [], "c": []}
    dur = {"a": 2, "b": 2, "c": 1}
    assert schedule(deps, dur, 2) == [("a", 0, 2, 0), ("b", 0, 2, 1), ("c", 2, 3, 0)]


def test_cycle_detected():
    with pytest.raises(CycleError) as e:
        schedule({"a": ["b"], "b": ["a"]}, {"a": 1, "b": 1}, 1)
    assert e.value.cycle == ["a", "b", "a"]


def test_unknown_dependency():
    with pytest.raises(ValueError):
        schedule({"a": ["zzz"]}, {"a": 1}, 1)
