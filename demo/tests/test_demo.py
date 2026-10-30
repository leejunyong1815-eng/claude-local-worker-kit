"""Offline tests: demo setup, two real managed executions, numeric/report checks."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DEMO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO))
from prepare import prepare
from rehearse import rehearse


class LabDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-lab-demo-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def exercise(self):
        run = rehearse(self.root / "rehearsal")
        metadata = json.loads((run / "rehearsal.json").read_text())
        report = json.loads((run / "report/results.json").read_text())
        return run, metadata, report

    def test_complete_offline_rehearsal(self):
        run, metadata, report = self.exercise()
        self.assertEqual(report["mode"], "offline-rehearsal")
        self.assertEqual(report["compute_backend"], "local")
        self.assertEqual(report["device"], "cpu")
        self.assertEqual(len(report["tasks"]), 2)
        self.assertNotEqual(report["tasks"][0]["worktree"], report["tasks"][1]["worktree"])
        self.assertEqual(len(report["experiment"]["conditioning"]), 2)
        self.assertEqual(len(report["experiment"]["sampling"]), 6)
        self.assertTrue(all(c["passed"] for c in report["experiment"]["checks"]))
        for task in report["tasks"]:
            self.assertEqual(task["worker_exit_code"], 0)
            self.assertEqual(task["verification_exit_codes"], [0])
            self.assertEqual(len(task["changed_files"]), 1)
            self.assertTrue(Path(task["diff_path"]).is_file())
        self.assertIn("OFFLINE REHEARSAL", (run / "report/report.html").read_text())
        self.assertIn("quantum_state", report["experiment"]["fidelity_quantity"])
        repo = Path(metadata["repository"])
        self.assertFalse((repo / "reference").exists())
        status = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"])
        self.assertEqual(status, b"")
        # The original skeleton is unchanged while two completed worktrees survive.
        self.assertIn("NotImplementedError", (repo / "src/labdemo/precondition.py").read_text())

    def test_preparation_preserves_existing_paths_and_stubs_fail(self):
        target = self.root / "existing"
        target.mkdir()
        note = target / "my-work.txt"
        note.write_text("keep")
        with self.assertRaises(ValueError):
            prepare(target, profile="")
        self.assertEqual(note.read_text(), "keep")
        info = prepare(self.root / "fresh", profile="")
        repo = Path(info["repository"])
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                                cwd=repo, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"NotImplementedError", result.stderr)
        for label in ("A", "B"):
            spec = json.loads((repo / f"tasks/{label}.json").read_text())
            self.assertEqual(spec["compute_backend"], "local")
            self.assertEqual(len(spec["allowed_paths"]), 1)
        self.assertTrue((repo / "start.sh").stat().st_mode & 0o111)

    def test_report_rejects_stale_worker_code(self):
        run, metadata, report = self.exercise()
        Path(report["tasks"][0]["worktree"], "src/labdemo/precondition.py").write_text("changed = True\n")
        process = self.finish_again(run, metadata)
        self.assertEqual(process.returncode, 2)
        self.assertIn("no current successful verification", process.stderr)
        self.assertFalse((run / "second-report").exists())

    def test_report_rejects_changed_harness(self):
        run, metadata, report = self.exercise()
        repo = Path(metadata["repository"])
        (repo / "data/cases.json").write_text('{"compute_backend":"ssh"}')
        process = self.finish_again(run, metadata)
        self.assertEqual(process.returncode, 2)
        self.assertIn("harness/input changed", process.stderr)
        self.assertFalse((run / "second-report").exists())

    def test_report_rejects_weakened_verification_spec(self):
        run, metadata, report = self.exercise()
        repo = Path(metadata["repository"])
        spec = json.loads((repo / "tasks/A.json").read_text())
        spec["verify"] = ["true"]
        weakened = run / "weak-task.json"
        weakened.write_text(json.dumps(spec))
        env = dict(os.environ, PATH=str(run / "mock-bin") + os.pathsep + os.environ["PATH"],
                   CLAUDE_WORKER_CONF_DIR=str(run / "mock-conf"),
                   DEMO_REHEARSAL_REFERENCE=str(DEMO / "reference"), PYTHONDONTWRITEBYTECODE="1")
        runner = [str(DEMO.parent / "bin/worker-task"), "--state-dir", metadata["state_dir"]]
        task = subprocess.check_output(runner + ["submit", str(weakened)], env=env, text=True).strip()
        subprocess.run(runner + ["run", task], env=env, check=True, stdout=subprocess.DEVNULL)
        metadata["tasks"][0] = task
        process = self.finish_again(run, metadata)
        self.assertEqual(process.returncode, 2)
        self.assertIn("not the assigned implementation", process.stderr)
        self.assertFalse((run / "second-report").exists())

    def test_report_refuses_duplicate_task_and_source_output(self):
        run, metadata, report = self.exercise()
        process = self.finish_again(run, metadata, duplicate=True)
        self.assertEqual(process.returncode, 2)
        self.assertIn("distinct IDs", process.stderr)
        process = self.finish_again(run, metadata, output=Path(metadata["repository"]) / "outputs")
        self.assertEqual(process.returncode, 2)
        self.assertIn("outside all source worktrees", process.stderr)
        self.assertFalse((Path(metadata["repository"]) / "outputs").exists())

    def finish_again(self, run, metadata, duplicate=False, output=None):
        task_a, task_b = metadata["tasks"]
        return subprocess.run([sys.executable, "-B", str(Path(metadata["repository"]) / "tools/finish.py"),
                               "--task-a", task_a, "--task-b", task_a if duplicate else task_b,
                               "--state-dir", metadata["state_dir"], "--output", str(output or run / "second-report")],
                              capture_output=True, text=True)

    def test_numerical_harness_against_small_known_matrix(self):
        spec = importlib.util.spec_from_file_location("provided_experiment", DEMO / "fixture/src/labdemo/experiment.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        inv = module.inverse([[2, 0], [0, 4]])
        self.assertEqual(inv, [[0.5, 0.0], [0.0, 0.25]])
        self.assertEqual(module.norm_inf([[2, 0], [0, 4]]) * module.norm_inf(inv), 2)
        with self.assertRaises(ValueError):
            module.manufactured_case(100)

    def test_start_script_selects_main_model_and_unique_name(self):
        info = prepare(self.root / "project", profile="")
        mock = self.root / "bin"
        mock.mkdir()
        (mock / "claude").write_text('#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        (mock / "claude").chmod(0o755)
        env = dict(os.environ, PATH=str(mock) + os.pathsep + os.environ["PATH"])
        env.pop("DEMO_ORCHESTRATOR_MODEL", None)
        launcher = str(Path(info["repository"]) / "start.sh")
        for override in (None, "selected-demo-model"):
            if override:
                env["DEMO_ORCHESTRATOR_MODEL"] = override
            args = json.loads(subprocess.check_output([launcher], env=env, text=True))
            self.assertEqual(args[args.index("--model") + 1], override or "claude-fable-5-1")
            self.assertEqual(args[args.index("--name") + 1], "lab-demo-" + info["run_id"])
            self.assertEqual(args[args.index("--effort") + 1], "high")
            self.assertNotIn("--dangerously-skip-permissions", args)
            self.assertIn("local CPU", args[args.index("--append-system-prompt") + 1])


if __name__ == "__main__":
    unittest.main()
