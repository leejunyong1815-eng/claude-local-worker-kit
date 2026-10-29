Task H3 (JSON Patch, RFC 6902, from a specification). Role: IMPLEMENTER.
Files to read: tests/test_jsonpatch.py. Do not read anything else. Create exactly one new file: jsonpatch.py (standard library only).
Specification:
- `apply_patch(doc, patch: list[dict])` returns a NEW document with all operations applied in order. The input
  document is never modified, even when an operation fails. Any failure raises `PatchError(Exception)`.
- JSON Pointer (RFC 6901): `""` is the whole document; otherwise the pointer must start with `/`; tokens are
  split on `/` and unescaped `~1` -> `/` then `~0` -> `~`. For lists a token must be a non-negative decimal integer
  without leading zeros (`"0"` is fine, `"01"` is not), or `-` which means "append" and is valid ONLY as the last
  token of an `add` path. Traversing through a scalar, a missing key, or an out-of-range index is an error.
- Operations: `add` (object: insert/replace key; list: insert at index, index may equal len; root: replace whole
  doc), `remove` (must exist), `replace` (must exist), `move` (`from` must exist; moving a location into one of its
  own children is an error; `from == path` is a no-op), `copy` (deep copy of `from` into `path`), `test` (strict
  equality: `1` vs `1.0` and `True` vs `1` are NOT equal; lists/dicts compared recursively with the same rule).
  Unknown op, missing `path`, missing `value` for add/replace/test, or missing `from` for move/copy are errors.
Rules: do not edit tests/, no other new files. When done, run `python3 -m pytest -q tests` and reply with its last line.
