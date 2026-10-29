from ingest import ingest
from report import lookup, render


def test_ingest_normalizes():
    t = ingest([("  Max   Speed ", 3), ("max speed", 5)])
    assert t == {"max_speed": 5}


def test_lookup_normalizes():
    t = ingest([("Max Speed", 5)])
    assert lookup(t, "MAX\tSPEED") == 5
    assert lookup(t, "other") is None


def test_render():
    assert render({"b": 1, "a": 2}) == "a: 2\nb: 1"
