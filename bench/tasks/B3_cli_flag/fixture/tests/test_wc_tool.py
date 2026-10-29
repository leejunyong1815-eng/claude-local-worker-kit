import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "wc_tool.py"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_text_default(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("one two\nthree\n")
    r = run(str(f))
    assert r.returncode == 0
    assert r.stdout.split() == ["2", "3", "14", str(f)]


def test_json_flag(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("one two\nthree\n")
    r = run("--json", str(f))
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data == [{"file": str(f), "lines": 2, "words": 3, "chars": 14}]
