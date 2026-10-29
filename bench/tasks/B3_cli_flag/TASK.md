Task B3 (add a CLI option). Role: IMPLEMENTER.
Files to read: wc_tool.py, tests/test_wc_tool.py. Do not read or create anything else.
Add a `--json` flag to wc_tool.py. With `--json`, print to stdout a single JSON array
(`json.dumps(rows)`) of objects `{"file", "lines", "words", "chars"}` in the order the files
were given, and nothing else on stdout. Without the flag keep the current text output unchanged.
Also: if any file cannot be opened, print an error mentioning the file name to stderr, print
nothing to stdout, and exit with status 1 (both with and without --json).
Rules: do not edit tests/, keep `count_file` and `main(argv=None)` as they are named, no new files.
When done, run `python3 -m pytest -q tests` and reply with its last line.
