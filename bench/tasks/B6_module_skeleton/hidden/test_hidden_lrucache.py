from lrucache import LRUCache


def test_update_existing_key_does_not_evict_and_refreshes():
    c = LRUCache(2)
    c.set("a", 1); c.set("b", 2)
    c.set("a", 10)           # update: a becomes most recent, nothing evicted
    assert len(c) == 2
    c.set("c", 3)            # evicts b
    assert c.get("a") == 10 and c.get("b") is None


def test_contains_does_not_touch_recency_or_stats():
    c = LRUCache(2)
    c.set("a", 1); c.set("b", 2)
    assert "a" in c
    c.set("c", 3)            # a is still least recent → evicted
    assert c.get("a") is None
    assert c.stats()["hits"] == 0 and c.stats()["misses"] == 1


def test_expiration_counts_and_removes():
    now = [0.0]
    c = LRUCache(5, ttl=1, clock=lambda: now[0])
    c.set("a", 1); c.set("b", 2)
    now[0] = 2
    assert c.get("a") is None and "b" not in c
    s = c.stats()
    assert s["expirations"] == 2 and s["misses"] == 1 and len(c) == 0


def test_clear_keeps_stats():
    c = LRUCache(2)
    c.set("a", 1); c.get("a")
    c.clear()
    assert len(c) == 0 and c.get("a") is None
    assert c.stats()["hits"] == 1 and c.stats()["misses"] == 1


def test_ttl_none_never_expires():
    now = [0.0]
    c = LRUCache(1, clock=lambda: now[0])
    c.set("a", 1)
    now[0] = 1e9
    assert c.get("a") == 1
