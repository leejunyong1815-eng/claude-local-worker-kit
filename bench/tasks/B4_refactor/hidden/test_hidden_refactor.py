import ingest
import report
import util


def test_shared_function_exists():
    assert util.normalize_name("  A  b ") == "a_b"


def test_modules_use_the_shared_function():
    assert ingest.normalize_name is util.normalize_name
    assert report.normalize_name is util.normalize_name


def test_private_copies_removed():
    assert not hasattr(ingest, "_normalize_name")
    assert not hasattr(report, "_normalize_name")
