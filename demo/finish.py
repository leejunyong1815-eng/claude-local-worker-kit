#!/usr/bin/env python3
"""Recheck two managed tasks and produce a small local-CPU evidence report."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env, stderr=subprocess.PIPE)


def task_result(repo, metadata, task_id, module, state_dir=None):
    command = [metadata["runner"]]
    if state_dir:
        command += ["--state-dir", str(state_dir)]
    command += ["result", task_id]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    state = json.loads(result.stdout)
    if (state["state"] != "succeeded" or not state.get("verification_valid") or
            not state.get("artifacts_complete") or state.get("verification_exit_codes") != [0]):
        raise ValueError(f"task {task_id} has no current successful verification: {state.get('reason')}")
    if state["base_commit"] != git(repo, "rev-parse", "HEAD").decode().strip():
        raise ValueError("task base commit differs from the demo checkout")
    spec = json.loads((Path(state["worktree"]).parent.parent.parent / "spec.json").read_text())
    expected = f"src/labdemo/{module}.py"
    label = "A" if module == "precondition" else "B"
    canonical = json.loads((repo / f"tasks/{label}.json").read_text())
    if (spec["repository"] != str(repo) or spec["allowed_paths"] != [expected] or
            any(spec.get(k) != canonical[k] for k in ("purpose", "instructions", "profile", "references", "verify", "compute_backend")) or
            not set(canonical["protected_paths"]).issubset(spec["protected_paths"])):
        raise ValueError("task is not the assigned implementation for this demo")
    if any(c["path"] != expected for c in state["changed_files"]):
        raise ValueError("unexpected changed file")
    return state, Path(state["worktree"]) / expected


def table(headers, rows):
    return ("<table><thead><tr>" + "".join(f"<th>{html.escape(str(h))}</th>" for h in headers) +
            "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in rows) + "</tbody></table>")


def write_report(output, report):
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    rows = report["experiment"]["conditioning"]
    samples = report["experiment"]["sampling"]
    checks = report["experiment"]["checks"]
    mode = report["mode"]
    banner = ("OFFLINE REHEARSAL — 모의 Claude 실행. 실제 LLM 성능 결과가 아닙니다."
              if mode == "offline-rehearsal" else "LIVE WORKFLOW — 설정된 워커 CLI 실행 및 외부 검증 기록")
    title = "Claude + 로컬 LLM: 작은 연구 작업의 위임과 검증"
    task_table = table(["태스크", "task ID / attempt", "워커 종료", "외부 검증", "수정 파일"],
        [(t["label"], t["task_id"] + " / " + t["attempt_id"], t["worker_exit_code"],
          str(t["verification_exit_codes"]), ", ".join(c["path"] for c in t["changed_files"])) for t in report["tasks"]])
    condition_table = table(["격자 / 미지수", "κ∞ 원본", "κ∞ 스케일링", "비율", "상대 잔차"],
        [(f"{r['grid_side']}×{r['grid_side']} / {r['unknowns']}", f"{r['raw_condition']:.4g}",
          f"{r['scaled_condition']:.4g}", f"{r['condition_ratio']:.2f}×", f"{r['residual']:.3e}") for r in rows])
    sampling_table = table(["격자", "샷", "분포 충실도 평균", "시드 간 표준편차"],
        [(r["grid_side"], r["shots"], f"{r['mean']:.6f}", f"{r['sample_std']:.6f}") for r in samples])
    check_table = table(["독립 실험 검사", "값", "허용 상한", "판정"],
        [(c["name"], f"{c['value']:.3e}", c["limit"], "PASS" if c["passed"] else "FAIL") for c in checks])
    passed = sum(c["passed"] for c in checks)
    document = f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f3f5f8;color:#172338;margin:0;line-height:1.6}}
main{{max-width:1080px;margin:auto;padding:36px 24px}}h1{{font-size:30px;line-height:1.35}}h2{{margin-top:32px}}
.banner{{background:#fff0ce;border:1px solid #d4a63e;padding:12px 18px;border-radius:8px}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}}.card{{background:white;padding:16px 22px;border-radius:10px;flex:1}}
.card strong{{font-size:25px;display:block}}table{{width:100%;border-collapse:collapse;background:white;font-size:14px}}
th,td{{padding:10px 12px;border-bottom:1px solid #dae0e8;text-align:left;overflow-wrap:anywhere}}th{{background:#e8edf4}}
.note{{color:#4a586d}}code{{overflow-wrap:anywhere}}@media print{{body{{background:white}}main{{padding:8px}}}}
</style><main><p class="banner">{html.escape(banner)}</p><h1>{html.escape(title)}</h1>
<p>오케스트레이터는 두 독립 작업을 분배하고, 워커는 각 worktree에서 구현합니다. 실행기가 따로 검증한 뒤 로컬 CPU에서 실험합니다.</p>
<div class="cards"><div class="card">구현 커버리지<strong>2 / 2 태스크</strong></div>
<div class="card">외부 검증<strong>2 / 2 통과</strong></div>
<div class="card">수치 검사<strong>{passed} / {len(checks)} 통과</strong></div>
<div class="card">계산 backend<strong>로컬 CPU</strong></div></div>
<p class="note">run {html.escape(report['run_id'])} · {html.escape(report['created_at'])} · Python {html.escape(report['python'])} · {report['duration_seconds']:.3f}초(수치 실험만)</p>
<h2>1. 워커가 실제로 제출한 변경과 검증</h2>{task_table}
<p class="note">커버리지는 준비한 두 모듈의 범위입니다. 전체 QCFD 연구의 재현율이나 모델 벤치마크 점수가 아닙니다.</p>
<h2>2. 행 스케일링: 같은 해를 유지했는가?</h2>{condition_table}
<p class="note">2D Poisson 이산 행렬에 인위적인 행 크기 불균형을 추가했습니다. κ∞ = ‖A‖∞ ‖A⁻¹‖∞이며, 2-노름 조건수가 아닙니다.
조건수 감소는 이 입력에서의 관측입니다. 모든 전처리·모든 문제에서 개선된다는 주장은 하지 않습니다.</p>
<h2>3. 샷 수와 확률분포 충실도</h2>{sampling_table}
<p class="note">고정 시드의 고전 multinomial 표본입니다. 평균과 표본 표준편차를 표시하며, 신뢰구간으로 해석하지 않습니다.
이 지표는 부호·위상을 확인하지 않으므로 양자 상태 충실도가 아닙니다. 시드별 값은 results.json에 있습니다.</p>
<h2>4. 실험 결과를 다시 검사</h2>{check_table}
<p>기준 커밋: <code>{html.escape(report['base_commit'])}</code><br>
입력 SHA-256: <code>{html.escape(report['input_sha256'])}</code></p>
<p>원시 수치와 태스크·로그·diff 경로는 <a href="results.json">results.json</a>, 발표 요약은 <a href="REPORT.md">REPORT.md</a>에 있습니다.</p>
<p class="note">QCFD 전체 재현·실제 양자 하드웨어·양자 우위·모델 간 우열·토큰 절감의 근거로 사용할 수 없습니다.</p></main></html>"""
    (output / "report.html").write_text(document)
    markdown = [f"# {title}", "", banner, "", "- Compute backend: local CPU",
                f"- Run: {report['run_id']}", f"- Base: {report['base_commit']}",
                "- Coverage: 2/2 scoped implementation tasks; external validation: 2/2",
                f"- Numerical checks: {passed}/{len(checks)}", ""]
    for task in report["tasks"]:
        markdown += [f"- {task['label']}: {task['task_id']} / {task['attempt_id']}",
                     f"  - worktree: {task['worktree']}", f"  - diff: {task['diff_path']}"]
    for row in rows:
        markdown += [f"- N={row['grid_side']}: κ∞ {row['raw_condition']:.6g} → {row['scaled_condition']:.6g}; residual {row['residual']:.3e}"]
    markdown += ["", "See report.html and results.json. Synthetic local demonstration only; no QPU or original QCFD results."]
    (output / "REPORT.md").write_text("\n".join(markdown) + "\n")


def finish(repo, task_a, task_b, output=None, state_dir=None):
    repo = repo.resolve()
    metadata = json.loads((repo / "demo.json").read_text())
    if metadata["compute_backend"] != "local" or metadata["repository"] != str(repo):
        raise ValueError("not a local-CPU demo workspace")
    if task_a == task_b:
        raise ValueError("the two tasks must have distinct IDs")
    # The trusted harness/config must still be the committed seed inputs.
    for path in ("demo.json", "data/cases.json", "src/labdemo/experiment.py", "tools/finish.py", "tasks/A.json", "tasks/B.json"):
        if (repo / path).read_bytes() != git(repo, "show", "HEAD:" + path):
            raise ValueError("demo harness/input changed since setup: " + path)
    state_a, module_a = task_result(repo, metadata, task_a, "precondition", state_dir)
    state_b, module_b = task_result(repo, metadata, task_b, "readout", state_dir)
    started = time.monotonic()
    config_bytes = (repo / "data/cases.json").read_bytes()
    precondition = load("demo_verified_precondition", module_a)
    readout = load("demo_verified_readout", module_b)
    experiment = load("demo_experiment", repo / "src/labdemo/experiment.py")
    result = experiment.run(precondition.row_scale, readout.distribution_fidelity, json.loads(config_bytes))
    # Imports/experimentation must not silently mutate previously verified code.
    task_result(repo, metadata, task_a, "precondition", state_dir)
    task_result(repo, metadata, task_b, "readout", state_dir)
    report = dict(run_id=metadata["run_id"], mode=metadata["mode"], compute_backend="local", device="cpu",
                  created_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  platform=platform.system(), base_commit=state_a["base_commit"],
                  input_sha256=hashlib.sha256(config_bytes).hexdigest(), duration_seconds=time.monotonic() - started,
                  experiment=result, tasks=[])
    for label, state in (("A: row scaling", state_a), ("B: distribution fidelity", state_b)):
        report["tasks"].append(dict(label=label, **{k: state[k] for k in (
            "task_id", "attempt_id", "profile", "worktree", "worker_exit_code", "verification_exit_codes",
            "worker_timed_out", "verification_timed_out", "duration_seconds", "changed_files", "logs", "diff_path")}))
    if output:
        output = output.expanduser().resolve()
        for protected in (repo, Path(state_a["worktree"]), Path(state_b["worktree"])):
            if output == protected or protected in output.parents:
                raise ValueError("output must be outside all source worktrees")
        output.mkdir(parents=True, exist_ok=False)
    else:
        output = Path(tempfile.mkdtemp(prefix=f"lab-demo-report-{metadata['run_id']}-"))
    write_report(output, report)
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-a", required=True)
    parser.add_argument("--task-b", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]  # deployed as <workspace>/tools/finish.py
    try:
        output, report = finish(repo, args.task_a, args.task_b, args.output, args.state_dir)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"report refused: {exc}\n")
    print(f"report.html: {output / 'report.html'}")
    print(f"results.json: {output / 'results.json'}")
    return 0 if all(check["passed"] for check in report["experiment"]["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
