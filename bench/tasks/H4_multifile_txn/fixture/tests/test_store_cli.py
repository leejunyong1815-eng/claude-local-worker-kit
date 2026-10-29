import json
import subprocess
import sys
from pathlib import Path

import pytest
from store import Store, StoreError, InsufficientStock

CLI = Path(__file__).resolve().parents[1] / "cli.py"


def run(db, *args):
    return subprocess.run([sys.executable, str(CLI), "--db", str(db), *args], capture_output=True, text=True)


def test_store_basic():
    s = Store()
    s.add("A", "apple", 2)
    s.adjust("A", -1)
    assert s.get("A").qty == 1
    with pytest.raises(InsufficientStock):
        s.adjust("A", -5)


def test_transaction_rolls_back_on_error():
    s = Store()
    s.add("A", "apple", 2)
    with pytest.raises(InsufficientStock):
        with s.transaction():
            s.add("B", "banana", 1)
            s.adjust("A", -1)
            s.adjust("A", -5)        # fails → everything above is undone
    assert s.get("B") is None and s.get("A").qty == 2


def test_transaction_commits():
    s = Store()
    with s.transaction():
        s.add("A", "apple", 1)
        s.adjust("A", 4)
    assert s.get("A").qty == 5


def test_cli_apply(tmp_path):
    db = tmp_path / "db.json"
    assert run(db, "add", "A", "apple", "3").returncode == 0
    ops = tmp_path / "ops.json"
    ops.write_text(json.dumps([{"op": "adjust", "sku": "A", "delta": -1}, {"op": "add", "sku": "B", "name": "banana", "qty": 7}]))
    r = run(db, "apply", str(ops))
    assert r.returncode == 0, r.stderr
    assert run(db, "list").stdout == "A\tapple\t2\nB\tbanana\t7\n"
