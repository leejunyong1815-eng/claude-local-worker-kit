Task B4 (refactor, no behavior change). Role: IMPLEMENTER.
Files to read: ingest.py, report.py, tests/test_ingest_report.py. Do not read anything else.
`_normalize_name` is duplicated in ingest.py and report.py. Create util.py containing a single
public function `normalize_name(name)` with exactly the current behavior, import it in both
modules with `from util import normalize_name`, use it, and delete both private copies
(`_normalize_name` must no longer exist in either module). Remove imports that become unused.
Rules: do not edit tests/, do not change the public functions ingest/lookup/render, only
create util.py as a new file. When done, run `python3 -m pytest -q tests` and reply with its last line.
