"""LRU cache with optional TTL (standard library only)."""
import time
from collections import OrderedDict


class LRUCache:
    """Least-recently-used cache with an optional time-to-live.

    Internals (suggested): ``self._data`` is an ``OrderedDict`` mapping key ->
    ``(value, set_time)``; the first item is the least recently used.
    ``self._stats`` holds the four counters.
    """

    def __init__(self, capacity: int, ttl: float | None = None, clock=time.monotonic):
        """Raise ValueError if capacity <= 0. ttl=None means never expire."""
        raise NotImplementedError

    def _expired(self, set_time: float) -> bool:
        """True if an entry stored at set_time has aged >= ttl (never if ttl is None)."""
        raise NotImplementedError

    def set(self, key, value) -> None:
        """Insert or update. Updated keys become most recent with a fresh set_time.
        Inserting a new key beyond capacity first removes the least recently used
        entry (one eviction)."""
        raise NotImplementedError

    def get(self, key, default=None):
        """Return the value and mark the key most recently used (one hit).
        Missing key → default (one miss). Expired key → remove it, count one
        expiration AND one miss, return default."""
        raise NotImplementedError

    def delete(self, key) -> bool:
        """Remove key; True if it existed. Stats unchanged."""
        raise NotImplementedError

    def __contains__(self, key) -> bool:
        """True only if present and not expired. An expired entry found here is
        removed and counted as one expiration (not a miss). No recency/hit change."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Number of stored entries (untouched expired entries still count)."""
        raise NotImplementedError

    def stats(self) -> dict:
        """Return a new dict with exactly: hits, misses, evictions, expirations."""
        raise NotImplementedError

    def clear(self) -> None:
        """Remove all entries; keep stats."""
        raise NotImplementedError
