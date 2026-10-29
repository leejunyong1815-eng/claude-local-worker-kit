import pytest
from jsonpatch import apply_patch, PatchError


def test_root_replace_and_root_test():
    assert apply_patch({"a": 1}, [{"op": "replace", "path": "", "value": [1]}]) == [1]
    assert apply_patch(5, [{"op": "test", "path": "", "value": 5}]) == 5


def test_array_insert_shifts():
    assert apply_patch([1, 3], [{"op": "add", "path": "/1", "value": 2}]) == [1, 2, 3]
    assert apply_patch([1], [{"op": "add", "path": "/1", "value": 2}]) == [1, 2]


@pytest.mark.parametrize("doc,patch", [
    ([1, 2], [{"op": "add", "path": "/3", "value": 0}]),          # index > len
    ([1, 2], [{"op": "remove", "path": "/-"}]),                   # '-' only valid for add
    ([1, 2], [{"op": "add", "path": "/01", "value": 0}]),         # leading zero
    ({"a": 1}, [{"op": "replace", "path": "/b", "value": 0}]),    # replace missing
    ({"a": 1}, [{"op": "remove", "path": "/b"}]),
    ({"a": {"b": 1}}, [{"op": "move", "from": "/a", "path": "/a/b/c"}]),   # move into own child
    ({"a": 1}, [{"op": "add", "path": "a", "value": 0}]),         # pointer must start with '/'
    ({"a": 1}, [{"op": "frobnicate", "path": "/a"}]),
    ({"a": 1}, [{"op": "add", "path": "/a"}]),                    # missing value
    ({"a": 1}, [{"op": "add", "path": "/a/b", "value": 0}]),      # traverse through a scalar
])
def test_errors(doc, patch):
    with pytest.raises(PatchError):
        apply_patch(doc, patch)


def test_atomic_on_failure():
    doc = {"a": 1}
    with pytest.raises(PatchError):
        apply_patch(doc, [{"op": "add", "path": "/b", "value": 2}, {"op": "remove", "path": "/zzz"}])
    assert doc == {"a": 1}


def test_test_uses_deep_equality_and_type():
    assert apply_patch({"a": [1, {"b": 2}]}, [{"op": "test", "path": "/a", "value": [1, {"b": 2}]}]) == {"a": [1, {"b": 2}]}
    with pytest.raises(PatchError):
        apply_patch({"a": 1}, [{"op": "test", "path": "/a", "value": 1.0}])   # int vs float differ
    with pytest.raises(PatchError):
        apply_patch({"a": True}, [{"op": "test", "path": "/a", "value": 1}])  # bool vs int differ


def test_move_same_path_is_noop_and_copy_is_deep():
    assert apply_patch({"a": [1]}, [{"op": "move", "from": "/a", "path": "/a"}]) == {"a": [1]}
    out = apply_patch({"a": [1]}, [{"op": "copy", "from": "/a", "path": "/b"}])
    out["b"].append(2)
    assert out["a"] == [1]
