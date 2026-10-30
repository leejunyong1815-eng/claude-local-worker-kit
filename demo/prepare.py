#!/usr/bin/env python3
"""Prepare a fresh, independent local-CPU lab demo. Never launches a model."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import uuid


DEMO = Path(__file__).resolve().parent
KIT = DEMO.parent


def git(repo, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                                    "-C", str(repo), *args], env=env, stderr=subprocess.PIPE).decode().strip()


def prepare(workspace, profile=None, mode="live"):
    workspace = workspace.expanduser().resolve()
    if workspace.exists():
        raise ValueError("workspace must not exist; choose a fresh path (nothing was overwritten)")
    if KIT == workspace or KIT in workspace.parents:
        raise ValueError("demo workspace must be outside the kit checkout")
    if mode not in {"live", "offline-rehearsal"}:
        raise ValueError("invalid run mode")
    if profile is None:
        conf = Path(os.environ.get("CLAUDE_WORKER_CONF_DIR", Path.home() / ".config/claude-worker"))
        profile = "impl" if (conf / "env.impl").is_file() else ""
    if profile and (not profile.isascii() or not all(c.isalnum() or c in "_-" for c in profile)):
        raise ValueError("invalid profile")
    run_id = uuid.uuid4().hex[:12]
    shutil.copytree(DEMO / "fixture", workspace, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    env = dict(os.environ, CLAUDE_WORKER_KIT=str(KIT))
    subprocess.run([str(KIT / "bin/project-init"), str(workspace)], env=env, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for name in ("PROMPT.md", "DEMO_ORCHESTRATOR.md"):
        shutil.copyfile(DEMO / name, workspace / name)
    tools = workspace / "tools"
    tools.mkdir()
    shutil.copyfile(DEMO / "finish.py", tools / "finish.py")
    metadata = dict(run_id=run_id, mode=mode, compute_backend="local", device="cpu",
                    repository=str(workspace), runner=str(KIT / "bin/worker-task"), profile=profile,
                    scientific_scope="synthetic demonstration; not a QCFD reproduction benchmark")
    (workspace / "demo.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    tasks = workspace / "tasks"
    tasks.mkdir()
    for task, module, test in (("A", "precondition", "test_precondition.py"), ("B", "readout", "test_readout.py")):
        relative = f"src/labdemo/{module}.py"
        spec = dict(purpose=f"Lab demo {run_id}: task {task} ({module})", repository=str(workspace),
                    base_commit="HEAD", profile=profile, compute_backend="local",
                    instructions=f"Implement only {relative} according to its docstring. Run the exact verify command. "
                    "Use this worktree's local CPU only (WSL is expected). Do not use SSH, remote-* or GPUs. "
                    "Do not edit tests, tools, configs or other source modules. Leave code uncommitted. "
                    "Report actual commands, exit codes and limitations. Do not claim a real quantum experiment.",
                    references=[relative, f"tests/{test}"], allowed_paths=[relative],
                    protected_paths=["tests/", "tools/", "data/", "tasks/", "demo.json", "DEMO_ORCHESTRATOR.md"],
                    verify=[f"python3 -B -m unittest discover -s tests -p {test} -v"],
                    timeout=240, verify_timeout=30, depends_on_uncommitted=False)
        (tasks / f"{task}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
    readme = """# Lab demo workspace

Compute backend: **local CPU** (WSL2 supported). LLM inference uses the installed
worker profile; it is separate from this experiment's compute backend.

Read DEMO_ORCHESTRATOR.md and paste PROMPT.md into the orchestrator.
Task A implements row scaling. Task B implements a classical distribution
fidelity metric. Both are intentionally unfinished; their protected tests fail
until a worker implements the assigned module.

After both tasks are independently verified, tools/finish.py loads the two
verified implementations and runs the provided small experiment locally.
It writes the presentation report outside this checkout. There is no automatic
source merge, commit or push. The original research repositories are not inputs.
The synthetic Poisson and multinomial experiment does not reproduce the full
QCFD campaign, call a QPU or demonstrate a quantum speedup. Infinity-norm
conditioning and probability-distribution fidelity must be labeled as such.
"""
    (workspace / "README.md").write_text(readme)
    (workspace / "AGENTS.md").write_text(
        "# Lab demo rules\n\nRead DEMO_ORCHESTRATOR.md first. Compute locally on CPU; no SSH or remote-* calls.\n"
        "Use the already committed skeleton/tests and the two tasks. Never open original QCFD repositories or chat logs.\n"
        "Do not use native Claude Agent/Workflow as a substitute for the configured local LLM workers.\n\n" +
        (workspace / "AGENTS.md").read_text())
    start = ("#!/usr/bin/env bash\nset -euo pipefail\n"
             'cd "$(dirname "$(readlink -f "$0")")"\n'
             f'export ORCHESTRATOR_NAME="lab-demo-{run_id}"\n'
             f"exec {shlex.quote(str(KIT / 'bin/claude-main'))} "
             '--model "${DEMO_ORCHESTRATOR_MODEL:-claude-fable-5-1}" --effort high '
             '--append-system-prompt "$(cat DEMO_ORCHESTRATOR.md)" "$@"\n')
    (workspace / "start.sh").write_text(start)
    (workspace / "start.sh").chmod(0o755)
    git(workspace, "init", "-q", "-b", "main")
    # Only files just created in this new directory, never the user's checkout.
    created = [str(p.relative_to(workspace)) for p in workspace.rglob("*")
               if p.is_file() and ".git" not in p.relative_to(workspace).parts]
    git(workspace, "add", "--", *sorted(created))
    git(workspace, "-c", "user.name=Lab demo setup", "-c", "user.email=demo@localhost",
        "commit", "-qm", "Prepare isolated local-CPU lab demonstration inputs")
    metadata["base_commit"] = git(workspace, "rev-parse", "HEAD")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="fresh path outside the kit; default creates a new /tmp project")
    parser.add_argument("--profile", help="existing worker profile; default impl if installed, otherwise base profile")
    args = parser.parse_args()
    path = args.workspace or Path(tempfile.mkdtemp(prefix="local-llm-lab-")) / "project"
    try:
        info = prepare(path, args.profile)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"demo setup failed: {exc}\n")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("\nStart the orchestrator:")
    print(f"  cd {shlex.quote(info['repository'])}")
    print("  ./start.sh")
    print("Then paste the contents of PROMPT.md. No model has been called by setup.")


if __name__ == "__main__":
    main()
