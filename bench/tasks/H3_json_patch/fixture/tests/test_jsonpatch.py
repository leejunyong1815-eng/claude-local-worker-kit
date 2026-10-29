import pytest
from jsonpatch import apply_patch, PatchError


def test_add_replace_remove():
    doc = {"a": {"b": 1}, "arr": [1, 2]}
    out = apply_patch(doc, [
        {"op": "add", "path": "/a/c", "value": 2},
        {"op": "replace", "path": "/a/b", "value": 9},
        {"op": "remove", "path": "/arr/0"},
        {"op": "add", "path": "/arr/-", "value": 3},
    ])
    assert out == {"a": {"b": 9, "c": 2}, "arr": [2, 3]}
    assert doc == {"a": {"b": 1}, "arr": [1, 2]}      # input untouched


def test_move_copy_test():
    doc = {"x": [1, 2, 3], "y": {}}
    out = apply_patch(doc, [
        {"op": "move", "from": "/x/0", "path": "/y/first"},
        {"op": "copy", "from": "/x", "path": "/y/rest"},
        {"op": "test", "path": "/y/first", "value": 1},
    ])
    assert out == {"x": [2, 3], "y": {"first": 1, "rest": [2, 3]}}


def test_test_failure_raises():
    with pytest.raises(PatchError):
        apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 2}])


def test_escaped_pointer():
    assert apply_patch({"a/b": 1, "m~n": 2}, [{"op": "replace", "path": "/a~1b", "value": 3},
                                               {"op": "remove", "path": "/m~0n"}]) == {"a/b": 3}
