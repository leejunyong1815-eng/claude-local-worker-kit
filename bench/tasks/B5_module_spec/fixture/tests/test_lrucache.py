import pytest
from lrucache import LRUCache


def test_set_get():
    c = LRUCache(2)
    c.set("a", 1)
    assert c.get("a") == 1
    assert c.get("missing") is None
    assert c.get("missing", 0) == 0


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.set("a", 1); c.set("b", 2)
    c.get("a")              # a is now most recent
    c.set("c", 3)           # evicts b
    assert c.get("b") is None
    assert c.get("a") == 1 and c.get("c") == 3


def test_len_contains_delete():
    c = LRUCache(3)
    c.set("a", 1); c.set("b", 2)
    assert len(c) == 2 and "a" in c and "z" not in c
    assert c.delete("a") is True
    assert c.delete("a") is False
    assert len(c) == 1


def test_ttl_expiry_with_fake_clock():
    now = [100.0]
    c = LRUCache(2, ttl=10, clock=lambda: now[0])
    c.set("a", 1)
    now[0] = 105
    assert c.get("a") == 1
    now[0] = 110.5
    assert c.get("a") is None
    assert len(c) == 0


def test_stats():
    c = LRUCache(1)
    c.set("a", 1)
    c.get("a"); c.get("b")
    c.set("c", 3)            # evicts a
    assert c.stats() == {"hits": 1, "misses": 1, "evictions": 1, "expirations": 0}


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(0)
