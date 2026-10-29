Task B6 (fill in a skeleton). Role: IMPLEMENTER.
Files to read: lrucache.py (skeleton: every method body is `raise NotImplementedError`), tests/test_lrucache.py.
Do not read or create anything else. Fill in the method bodies of lrucache.py, one method at a time,
following each method's docstring and this specification:
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
Rules: do not edit tests/, do not change any signature or docstring, no new files.
When done, run `python3 -m pytest -q tests` and reply with its last line.
