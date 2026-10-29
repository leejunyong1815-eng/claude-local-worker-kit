"""Ingest raw records into a dict keyed by a normalized name."""
import re


def _normalize_name(name):
    name = name.strip().lower()
    name = re.sub(r"\s+", " ", name)
    return name.replace(" ", "_")


def ingest(records):
    """records: iterable of (name, value). Later values overwrite earlier ones."""
    out = {}
    for name, value in records:
        out[_normalize_name(name)] = value
    return out
