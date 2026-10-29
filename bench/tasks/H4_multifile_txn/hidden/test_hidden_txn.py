import json
import subprocess
import sys
from pathlib import Path

import pytest
from store import Store, StoreError

CLI = Path(__file__).resolve().parents[1] / "cli.py"


def run(db, *args):
    return subprocess.run([sys.executable, str(CLI), "--db", str(db), *args], capture_output=True, text=True)


def test_nested_transaction_is_error_and_outer_rolls_back():
    s = Store()
    s.add("A", "apple", 1)
    with pytest.raises(StoreError):
        with s.transaction():
            s.adjust("A", 1)
            with s.transaction():
                pass
    assert s.get("A").qty == 1


def test_rollback_restores_removed_item_and_isolation_of_objects():
    s = Store()
    s.add("A", "apple", 1)
    before = s.get("A")
    with pytest.raises(StoreError):
        with s.transaction():
            s.remove("A")
            s.remove("A")      # unknown → error
    assert s.get("A").qty == 1 and s.get("A") == before


def test_cli_apply_atomic_and_exit_code(tmp_path):
    db = tmp_path / "db.json"
    run(db, "add", "A", "apple", "3")
    ops = tmp_path / "ops.json"
    ops.write_text(json.dumps([{"op": "add", "sku": "B", "name": "banana", "qty": 1}, {"op": "adjust", "sku": "A", "delta": -9}]))
    r = run(db, "apply", str(ops))
    assert r.returncode == 2 and "A" in r.stderr and r.stdout == ""
    assert json.load(open(db)) == [{"sku": "A", "name": "apple", "qty": 3}]


def test_cli_apply_remove_and_bad_op(tmp_path):
    db = tmp_path / "db.json"
    run(db, "add", "A", "apple", "3"); run(db, "add", "B", "banana", "1")
    ops = tmp_path / "ops.json"
    ops.write_text(json.dumps([{"op": "remove", "sku": "B"}]))
    assert run(db, "apply", str(ops)).returncode == 0
    assert run(db, "list").stdout == "A\tapple\t3\n"
    ops.write_text(json.dumps([{"op": "explode", "sku": "A"}]))
    r = run(db, "apply", str(ops))
    assert r.returncode == 2 and r.stdout == ""
    assert run(db, "list").stdout == "A\tapple\t3\n"


def test_cli_apply_unreadable_file(tmp_path):
    db = tmp_path / "db.json"
    r = run(db, "apply", str(tmp_path / "missing.json"))
    assert r.returncode == 2 and r.stdout == ""
