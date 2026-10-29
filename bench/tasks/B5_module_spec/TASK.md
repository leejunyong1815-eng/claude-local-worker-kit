Task B5 (write a whole module from a specification). Role: IMPLEMENTER.
Files to read: tests/test_lrucache.py. Do not read anything else. Create exactly one new file: lrucache.py.
Specification of lrucache.py (standard library only):
- `class LRUCache(capacity: int, ttl: float | None = None, clock=time.monotonic)`.
  `capacity <= 0` raises ValueError. `ttl` is seconds; None means entries never expire.
  `clock` is a zero-argument callable returning the current time (tests pass a fake one).
- `set(key, value)`: insert or update. An updated key becomes the most recently used and its
  expiry time is reset. When inserting a new key beyond capacity, remove the least recently
  used entry first (counts as one eviction).
- `get(key, default=None)`: return the value and mark the key most recently used (hit).
  A missing key returns `default` (miss). An entry whose age (`clock() - set time`) is >= ttl
  is removed, counted as one expiration AND one miss, and `default` is returned.
- `delete(key) -> bool`: remove the key; True if it existed, False otherwise. No stats change.
- `__contains__(key)`: True only if present and not expired; an expired entry found this way is
  removed and counted as an expiration (but NOT a miss). Does not change recency or hits.
- `__len__`: number of entries currently stored (expired entries that have not been touched yet
  still count until they are seen by get/contains).
- `stats() -> dict` with exactly the keys hits, misses, evictions, expirations (all int, start at 0).
- `clear()`: remove all entries; stats are kept.
Rules: do not edit tests/, no other new files. When done, run `python3 -m pytest -q tests` and reply with its last line.
