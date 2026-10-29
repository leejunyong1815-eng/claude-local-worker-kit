Task H2 (dependency-aware list scheduler from a specification). Role: IMPLEMENTER.
Files to read: tests/test_schedule.py. Do not read anything else. Create exactly one new file: schedule.py (standard library only).
Specification:
- `schedule(deps: dict[str, list[str]], duration: dict[str, int], workers: int) -> list[tuple[str, int, int, int]]`
  returns one tuple `(task, start, end, worker)` per task, sorted by `(start, worker)`.
- Validation (raise `ValueError`): `workers < 1`; a dependency naming a task not in `deps`; a task missing
  from `duration`; a duration < 1.
- Cycles: raise `CycleError(ValueError)` with attribute `cycle`: a list that starts and ends with the same task,
  e.g. `["a", "b", "a"]`, following dependency edges (task -> one of its deps). When several cycles exist, report the
  one found by a depth-first search that visits tasks in alphabetical order and iterates each task's deps in
  alphabetical order; the reported cycle starts at the first task of that cycle encountered by the search
  (so for `x->y->z->x` with another task `m->x`, the cycle is `["x","y","z","x"]`). A self-loop gives `["a","a"]`.
- Simulation (list scheduling): time starts at 0. A task is ready when all its deps have finished (end <= now).
  At each decision point assign ready tasks in alphabetical order to idle workers in increasing worker index
  (0, 1, ...), as many as fit. A task occupies its worker for `duration[task]` time units. Then advance time to
  the earliest end among running tasks and repeat. Tasks are never preempted. A worker that becomes idle is
  reusable immediately at that time. Empty `deps` returns `[]`.
Rules: do not edit tests/, no other new files. When done, run `python3 -m pytest -q tests` and reply with its last line.
