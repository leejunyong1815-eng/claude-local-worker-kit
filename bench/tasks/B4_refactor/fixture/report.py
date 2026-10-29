"""Render a report of ingested values."""
import re


def _normalize_name(name):
    name = name.strip().lower()
    name = re.sub(r"\s+", " ", name)
    return name.replace(" ", "_")


def lookup(table, name):
    """Return table[name] using the same normalization as ingest, or None."""
    return table.get(_normalize_name(name))


def render(table):
    return "\n".join(f"{k}: {table[k]}" for k in sorted(table))
