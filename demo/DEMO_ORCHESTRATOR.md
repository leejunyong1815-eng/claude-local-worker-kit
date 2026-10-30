# Lab meeting demonstration protocol

You orchestrate the provided small research-style demo. Read demo.json, tasks/A.json,
tasks/B.json and the module docstrings. Source and tests are already committed.
Do not rewrite skeletons, tests, task files, tools or configs. Do not import/read
the original QCFD repositories, old transcripts, or the kit's rehearsal solutions.
Do not replace local LLM workers with Claude Agent/Workflow agents.

## Compute and execution

- Compute backend is the current **local CPU**, typically WSL2. No SSH, remote-*
  commands, GPU jobs, QPU calls, server configuration changes or new packages.
- The inference server is separate: reuse the configured local LLM profile from
  the two specs. Do not change model routes, context windows or API credentials.
- Use the runner path in demo.json, or the installed worker-task CLI. Register
  tasks/A.json and tasks/B.json. Record the two returned IDs. Run each from a
  separate managed worktree, at most two concurrent executions. A shell job or
  Bash background task may be used; collect real process exit codes.
- Reuse the seed commit. Do not commit/merge/stash source or edit another worker's
  worktree. Do not use permission-bypass flags. If existing permissions prevent
  execution, explain which command/permission blocked it rather than changing it.
- The supplied tests deliberately fail before implementation. Each worker may
  modify exactly its assigned source module; the test/verification files are protected.

## Independent completion and presentation

Use worker-task status/result for both IDs. Require succeeded, verification_valid,
artifacts_complete and zero verification exit codes. Worker reports alone do not count.
If a task fails, inspect its logs, preserve it, and explicitly retry at most once.
If it still fails, stop that part and report incomplete coverage; do not quietly
implement it yourself and present it as local-worker completion.

After both tasks are verified, run in this demo checkout:

    python3 -B tools/finish.py --task-a <A ID> --task-b <B ID>

The tool independently rechecks the task results and imports only the verified
two modules. It runs the supplied experiment on the local CPU and writes JSON,
Markdown and standalone HTML outside the original checkout. No source copying
or merging is needed. If either verification is stale, do not run around that check.

Report the actual task IDs/attempts, worktree and log paths, verification codes,
compute backend, measured condition numbers/residuals and distribution fidelity,
and the final report.html path. Label condition numbers as infinity-norm values.
The readout metric concerns probabilities, not amplitude signs/phases. Finite-shot
samples need not improve monotonically for every seed. This is a synthetic local
workflow demonstration, not a full reproduction, model leaderboard, blind test,
timing speedup comparison, QPU result, or quantum-advantage demonstration.
