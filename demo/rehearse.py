#!/usr/bin/env python3
"""Offline rehearsal: real managed runner and Git, fake Claude, no model calls."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from prepare import DEMO, KIT, prepare


MOCK = r'''#!/usr/bin/env python3
import json, os, re, shutil, sys
from pathlib import Path
if '--version' in sys.argv:
    print('2.1.314 (offline demo mock)'); sys.exit(0)
assert not os.environ.get('CLAUDECODE'), 'parent session marker leaked'
assert '--dangerously-skip-permissions' not in sys.argv
assert '--permission-mode' not in sys.argv
prompt = sys.argv[sys.argv.index('-p')+1]
allowed = json.loads(re.search(r'Allowed paths: (.+)', prompt).group(1))
assert len(allowed) == 1
target = Path(allowed[0])
assert target.name in ('precondition.py', 'readout.py')
assert Path.cwd().name == 'worktree'
shutil.copyfile(Path(os.environ['DEMO_REHEARSAL_REFERENCE']) / target.name, target)
print(json.dumps({'is_error': False, 'num_turns': 1, 'result': 'OFFLINE REHEARSAL ONLY; no LLM call'}))
'''


def rehearse(root):
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=False)
    conf, mock = root / "mock-conf", root / "mock-bin"
    conf.mkdir(); mock.mkdir()
    (conf / "env").write_text('export LLM_BASE_URL="http://127.0.0.1:9"\nexport LLM_API_KEY="none"\nexport LLM_MODEL="offline-demo-mock"\n')
    (mock / "claude").write_text(MOCK)
    (mock / "claude").chmod(0o755)
    env = dict(os.environ, PATH=str(mock) + os.pathsep + os.environ["PATH"],
               CLAUDE_WORKER_CONF_DIR=str(conf), DEMO_REHEARSAL_REFERENCE=str(DEMO / "reference"),
               PYTHONDONTWRITEBYTECODE="1", CLAUDECODE="1")
    metadata = prepare(root / "project", profile="", mode="offline-rehearsal")
    repo, state = Path(metadata["repository"]), root / "state"
    runner = [str(KIT / "bin/worker-task"), "--state-dir", str(state)]
    tasks = []
    for label in ("A", "B"):
        p = subprocess.run(runner + ["submit", str(repo / f"tasks/{label}.json")],
                           env=env, capture_output=True, text=True, check=True)
        tasks.append(p.stdout.strip())
    jobs = []
    for task in tasks:
        log = (root / (task + ".runner.log")).open("w")
        process = subprocess.Popen(runner + ["run", task], env=env, stdout=log, stderr=subprocess.STDOUT)
        jobs.append((process, log))
    try:
        codes = [p.wait(timeout=25) for p, _ in jobs]
    finally:
        for p, log in jobs:
            if p.poll() is None:
                subprocess.run(runner + ["cancel", tasks[jobs.index((p, log))]], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                p.wait(timeout=10)
            log.close()
    if any(codes):
        raise ValueError("offline runner failed; see preserved *.runner.log files in " + str(root))
    command = [sys.executable, "-B", str(repo / "tools/finish.py"), "--task-a", tasks[0],
               "--task-b", tasks[1], "--state-dir", str(state), "--output", str(root / "report")]
    subprocess.run(command, env=env, check=True)
    (root / "rehearsal.json").write_text(json.dumps(dict(mode="offline-rehearsal", tasks=tasks,
                                                repository=str(repo), state_dir=str(state)), indent=2) + "\n")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="fresh directory; preserves both task worktrees, logs and report")
    args = parser.parse_args()
    root = args.output or Path(tempfile.mkdtemp(prefix="lab-demo-rehearsal-")) / "run"
    try:
        root = rehearse(root)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"offline rehearsal failed: {exc}\n")
    print("OFFLINE REHEARSAL ONLY — real model/server were not called.")
    print(f"Preserved workspace, state and report: {root}")


if __name__ == "__main__":
    main()
