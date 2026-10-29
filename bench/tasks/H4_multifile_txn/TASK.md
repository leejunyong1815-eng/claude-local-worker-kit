Task H4 (feature across several files). Role: IMPLEMENTER.
Files to read: models.py, store.py, cli.py, tests/test_store_cli.py. Do not read or create anything else.
Add atomic transactions to the inventory app:
1. `Store.transaction()` — a context manager. Operations inside it (add/remove/adjust) are applied as usual, but
   if ANY exception propagates out of the `with` block, the store is restored exactly to its state at entry (items,
   quantities, and removed items come back) and the exception is re-raised. On normal exit the changes stay.
   Opening a transaction while one is already open raises `StoreError` (and that error also rolls back the outer one
   when it propagates). Hint: snapshot the item data at entry and restore from the snapshot on failure.
2. `cli.py apply <ops.json>` — a new subcommand. The file holds a JSON list of operations:
   `{"op":"add","sku":..,"name":..,"qty":..}` (qty optional, default 0), `{"op":"remove","sku":..}`,
   `{"op":"adjust","sku":..,"delta":..}`. All operations run inside ONE transaction. On success save the db and exit 0.
   If any operation fails, or an op name is unknown, or the file cannot be read or is not valid JSON: print an error
   mentioning the problem to stderr, print nothing to stdout, do NOT write the db file, and exit 2.
Rules: do not edit tests/, keep every existing function and class name and signature, no new files.
When done, run `python3 -m pytest -q tests` and reply with its last line.
