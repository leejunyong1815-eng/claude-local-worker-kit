import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "wc_tool.py"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_json_multiple_files_in_order(tmp_path):
    a = tmp_path / "a.txt"; a.write_text("x\n")
    b = tmp_path / "b.txt"; b.write_text("y z\n\n")
    r = run("--json", str(a), str(b))
    data = json.loads(r.stdout)
    assert [d["file"] for d in data] == [str(a), str(b)]
    assert data[1] == {"file": str(b), "lines": 2, "words": 2, "chars": 5}


def test_missing_file_json_exit_1(tmp_path):
    r = run("--json", str(tmp_path / "nope.txt"))
    assert r.returncode == 1
    assert r.stdout.strip() == ""
    assert "nope.txt" in r.stderr


def test_missing_file_text_exit_1(tmp_path):
    r = run(str(tmp_path / "nope.txt"))
    assert r.returncode == 1
    assert "nope.txt" in r.stderr
