from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
import platform
import signal
import shutil
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.decompile_faithfulness import holdout_evaluation
from analysis.decompile_faithfulness import strong_baselines_and_mechanism as sbm


METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
VERIFIED_HOLDOUT_SEAL = "cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42"
PHASE1E_RESULT_COMMIT = "f302bb51eb9371c0dad51bce92be53f58fc1a341"
PHASE1F_RESULT_ARTIFACT_COMMIT = "66b60c7a1ec0981c1ff5b307e0ee85efcf7d9589"
PHASE1F_FINAL_HEAD = "b626b38dd9f1398945a7c604b3213f589b936b8a"
FROZEN_FINAL_DETECTED_B8 = 33
FROZEN_FINAL_DENOMINATOR = 37
CLANG = Path("/usr/lib/llvm-11/bin/clang")
WALL_CLOCK_BUDGETS = [0.1, 1.0, 5.0]
MAX_WORKERS_DEFAULT = 4
TERMINATION_TOLERANCE_S = 0.75
WORK_DIR = Path("analysis_outputs/decompile_faithfulness/phase1g_wallclock")
PREREG_PATH = Path("docs/paper_agent/libfuzzer_wallclock_preregistration.md")

PROTECTED_PHASE1F_ARTIFACTS = [
    "results/decompile_faithfulness/libfuzzer_runs.jsonl",
    "results/decompile_faithfulness/libfuzzer_summary.csv",
]
PROTECTED_PHASE1F_HARNESS_FILES = [
    "analysis/decompile_faithfulness/strong_baselines_and_mechanism.py",
]

FORBIDDEN_FINAL_METHOD_MODULES = {
    "analysis.decompile_faithfulness.run_phase11_input_ordering",
    "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
}
FORBIDDEN_FINAL_METHOD_CALLS = {
    "build_ordered_inputs",
    "source_literal_char_inputs",
    "fixture_neighbor_inputs",
    "interleave_inputs",
}


@dataclass(frozen=True)
class HarnessInfo:
    candidate_id: str
    ok: bool
    exe: Path | None
    seed_dir: Path | None
    reason: str
    validation: dict[str, Any]


@dataclass(frozen=True)
class RunJob:
    candidate_id: str
    seed: int
    budget_s: float


class WitnessConfirmer:
    def __init__(self, clang: Path, work_dir: Path, candidates: dict[str, sbm.CandidateInfo], functions: dict[str, sbm.FunctionInfo]):
        self.clang = clang
        self.work_dir = work_dir
        self.candidates = candidates
        self.functions = functions
        self.cache: dict[tuple[str, tuple[int, ...]], dict[str, Any]] = {}
        self._lock = threading.Lock()

    def confirm(self, candidate_id: str, args: list[int]) -> dict[str, Any]:
        key = (candidate_id, tuple(int(value) for value in args))
        with self._lock:
            if key in self.cache:
                return self.cache[key]
            result = self._confirm_uncached(candidate_id, list(key[1]))
            self.cache[key] = result
            return result

    def _confirm_uncached(self, candidate_id: str, args: list[int]) -> dict[str, Any]:
        candidate = self.candidates[candidate_id]
        function = self.functions[candidate.function_id]
        out_dir = self.work_dir / sbm.safe_name(candidate_id) / ("args_" + "_".join(str(value) for value in args))
        out_dir.mkdir(parents=True, exist_ok=True)
        source_path = Path(function.source_path)
        candidate_path = Path(candidate.source_path)
        if not source_path.exists() or not candidate_path.exists():
            return {"confirmed": False, "method": "single_input_reexecution", "reason": "missing_source_or_candidate_path"}
        harness_path = out_dir / "confirm.c"
        exe = out_dir / "confirm"
        harness_path.write_text(render_confirmation_harness(function, source_path.read_text(encoding="utf-8"), candidate_path.read_text(encoding="utf-8"), args), encoding="utf-8")
        compile_result = subprocess.run(
            [
                str(self.clang),
                "-std=c11",
                "-O1",
                "-g",
                "-fsanitize=address,undefined",
                "-fno-sanitize-recover=all",
                str(harness_path),
                "-o",
                str(exe),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if compile_result.returncode != 0:
            return {
                "confirmed": False,
                "method": "single_input_reexecution",
                "reason": "confirmation_compile_failure",
                "stderr_tail": compile_result.stderr[-1000:],
            }
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0"
        env["LSAN_OPTIONS"] = "detect_leaks=0"
        env["CUDA_VISIBLE_DEVICES"] = ""
        run = subprocess.run(
            [str(exe)],
            cwd=out_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
            timeout=30,
        )
        if run.returncode != 0:
            return {
                "confirmed": False,
                "method": "single_input_reexecution",
                "reason": "confirmation_runtime_failure",
                "stderr_tail": run.stderr[-1000:],
            }
        parsed = parse_confirmation_stdout(run.stdout)
        confirmed = parsed.get("source_output") != parsed.get("candidate_output")
        return {
            "confirmed": bool(confirmed),
            "method": "single_input_reexecution",
            "args": args,
            "source_output": parsed.get("source_output", ""),
            "candidate_output": parsed.get("candidate_output", ""),
            "sanitizer_clean": True,
            "reason": "source_candidate_outputs_differ" if confirmed else "source_candidate_outputs_match",
        }


def main() -> None:
    args = parse_args()
    summary = run(Path(args.repo_root).resolve(), max_workers=args.max_workers)
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 1g CPU-only libFuzzer wall-clock baseline")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS_DEFAULT, help="Maximum concurrent CPU workers")
    return parser.parse_args()


def run(repo_root: Path, *, max_workers: int = MAX_WORKERS_DEFAULT) -> dict[str, Any]:
    out_dir = repo_root / "results/decompile_faithfulness"
    fig_data_dir = repo_root / "figures/data"
    fig_dir = repo_root / "figures"
    table_dir = repo_root / "paper/tables"
    docs_dir = repo_root / "docs/paper_agent"
    work_dir = repo_root / WORK_DIR
    for path in [out_dir, fig_data_dir, fig_dir, table_dir, docs_dir, work_dir]:
        path.mkdir(parents=True, exist_ok=True)

    max_workers = choose_worker_count(max_workers)
    command = " ".join(sys.argv)
    preflights = [run_preflight(repo_root, "initial", command, max_workers)]
    if not preflights[-1]["ok"]:
        write_json(out_dir / "libfuzzer_wallclock_preflight.json", {"ok": False, "batch_preflights": preflights})
        raise RuntimeError("Phase 1g preflight failed before harness build")

    functions = sbm.load_functions(repo_root)
    candidates = sbm.load_candidates(repo_root)
    labels = {row["candidate_id"]: row for row in sbm.read_jsonl(out_dir / "holdout_exact_labels.jsonl")}
    fixtures = sbm.load_fixtures(repo_root)
    first_rows = sbm.normalize_first_witness_rows(sbm.read_csv(out_dir / "holdout_first_witness.csv"))
    population = sbm.build_population(first_rows, functions, candidates)
    check_population(population)

    run_root = work_dir / ("run_" + short_head(repo_root) + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    harness_dir = run_root / "harnesses"
    matrix_dir = run_root / "runs"
    confirm_dir = run_root / "confirmations"
    harness_dir.mkdir(parents=True, exist_ok=True)
    matrix_dir.mkdir(parents=True, exist_ok=True)
    confirm_dir.mkdir(parents=True, exist_ok=True)

    candidate_ids = sbm.baseline_candidate_ids(population)
    harnesses = build_harnesses(CLANG, harness_dir, candidate_ids, candidates, functions, labels, fixtures)
    confirmer = WitnessConfirmer(CLANG, confirm_dir, candidates, functions)
    run_rows: list[dict[str, Any]] = []
    for budget in WALL_CLOCK_BUDGETS:
        preflights.append(run_preflight(repo_root, f"before_budget_{budget:g}", command, max_workers))
        write_json(out_dir / "libfuzzer_wallclock_preflight.json", {"ok": all(item["ok"] for item in preflights), "batch_preflights": preflights})
        if not preflights[-1]["ok"]:
            raise RuntimeError(f"Phase 1g preflight failed before budget {budget:g}")
        run_rows.extend(unsupported_budget_rows(budget, candidate_ids, harnesses, candidates, functions, labels, population))
        jobs = [
            RunJob(candidate_id=cid, seed=seed, budget_s=budget)
            for cid in candidate_ids
            if harnesses[cid].ok
            for seed in sbm.RANDOM_SEEDS
        ]
        run_rows.extend(run_budget_jobs(jobs, harnesses, candidates, functions, labels, population, matrix_dir, confirmer, max_workers))

    preflight_payload = {"ok": all(item["ok"] for item in preflights), "batch_preflights": preflights}
    write_json(out_dir / "libfuzzer_wallclock_preflight.json", preflight_payload)
    run_rows = sorted(run_rows, key=lambda row: (float(row["wall_clock_budget_s"]), row["candidate_id"], int(row["seed"])))
    summary_rows = summarize_wallclock_runs(run_rows, population)
    candidate_set_rows = candidate_set_comparisons(run_rows, first_rows, population)
    failures = failure_rows(run_rows)
    environment = environment_manifest(repo_root, run_root, max_workers, harnesses, population, command)
    detection_rows = detection_curve_rows(summary_rows)
    time_rows = time_to_witness_rows(summary_rows)

    sbm.write_jsonl(out_dir / "libfuzzer_wallclock_runs.jsonl", run_rows)
    sbm.write_csv(out_dir / "libfuzzer_wallclock_summary.csv", summary_rows)
    sbm.write_csv(out_dir / "libfuzzer_wallclock_candidate_sets.csv", candidate_set_rows)
    sbm.write_jsonl(out_dir / "libfuzzer_wallclock_failures.jsonl", failures)
    write_json(out_dir / "libfuzzer_wallclock_environment.json", environment)
    sbm.write_csv(fig_data_dir / "libfuzzer_wallclock_detection.csv", detection_rows)
    sbm.write_csv(fig_data_dir / "libfuzzer_wallclock_time_to_witness.csv", time_rows)
    sbm.write_csv(fig_data_dir / "libfuzzer_wallclock_candidate_sets.csv", candidate_set_rows)
    write_tables(repo_root, summary_rows, candidate_set_rows, first_rows, population)
    write_plot_script(repo_root)
    generate_figures(repo_root)
    handoff = write_handoff(repo_root, summary_rows, candidate_set_rows, failures, environment, preflight_payload, first_rows, population)

    return {
        "status": "completed",
        "run_rows": len(run_rows),
        "supported_candidates": sum(1 for item in harnesses.values() if item.ok),
        "declared_candidates": len(candidate_ids),
        "max_workers": max_workers,
        "preflight_ok": preflight_payload["ok"],
        "handoff": str(handoff.relative_to(repo_root)),
    }


def run_preflight(repo_root: Path, batch: str, command: str, max_workers: int) -> dict[str, Any]:
    manifest_path = repo_root / holdout_evaluation.SEALED_MANIFEST_PATH
    manifest_sha = sha256_path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_checks = holdout_evaluation.verify_sealed_artifacts(repo_root, manifest)
    method_checks = holdout_evaluation.verify_method_hashes(repo_root, manifest)
    phase1f_checks = verify_phase1f_artifacts(repo_root)
    guard = final_method_guard(repo_root / "analysis/decompile_faithfulness/libfuzzer_wallclock.py")
    payload = {
        "batch": batch,
        "created_at_utc": now_utc(),
        "current_commit": git_output(repo_root, ["rev-parse", "HEAD"]),
        "current_branch": git_output(repo_root, ["branch", "--show-current"]),
        "command": command,
        "max_workers": max_workers,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "expected_holdout_seal": VERIFIED_HOLDOUT_SEAL,
        "holdout_manifest_sha256": manifest_sha,
        "holdout_manifest_sha256_matches_expected": manifest_sha == VERIFIED_HOLDOUT_SEAL,
        "sealed_artifact_checks": artifact_checks,
        "method_hash_checks": method_checks,
        "phase1f_evaluation_count_artifact_checks": phase1f_checks,
        "final_method_import_call_guard": guard,
        "environment": basic_environment(),
        "cpu_only": True,
        "gpu_usage": "not_used",
    }
    payload["ok"] = (
        payload["holdout_manifest_sha256_matches_expected"]
        and artifact_checks["all_ok"]
        and method_checks["all_ok"]
        and phase1f_checks["all_ok"]
        and guard["ok"]
    )
    return payload


def verify_phase1f_artifacts(repo_root: Path) -> dict[str, Any]:
    checks = []
    all_ok = True
    for rel in PROTECTED_PHASE1F_ARTIFACTS:
        current_path = repo_root / rel
        current_sha = sha256_path(current_path) if current_path.exists() else ""
        expected_sha = git_blob_sha256(repo_root, PHASE1F_RESULT_ARTIFACT_COMMIT, rel)
        ok = current_path.exists() and current_sha == expected_sha
        all_ok = all_ok and ok
        checks.append({"path": rel, "expected_commit": PHASE1F_RESULT_ARTIFACT_COMMIT, "expected_sha256": expected_sha, "current_sha256": current_sha, "ok": ok})
    for rel in PROTECTED_PHASE1F_HARNESS_FILES:
        current_path = repo_root / rel
        current_sha = sha256_path(current_path) if current_path.exists() else ""
        expected_sha = git_blob_sha256(repo_root, PHASE1F_FINAL_HEAD, rel)
        ok = current_path.exists() and current_sha == expected_sha
        all_ok = all_ok and ok
        checks.append({"path": rel, "expected_commit": PHASE1F_FINAL_HEAD, "expected_sha256": expected_sha, "current_sha256": current_sha, "ok": ok})
    return {"all_ok": all_ok, "checked_count": len(checks), "checks": checks}


def final_method_guard(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "reason": "module_missing", "path": str(path)}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_FINAL_METHOD_MODULES:
            violations.append({"kind": "import_from", "name": node.module})
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_FINAL_METHOD_MODULES:
                    violations.append({"kind": "import", "name": alias.name})
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_FINAL_METHOD_CALLS:
                violations.append({"kind": "call", "name": node.func.id})
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_FINAL_METHOD_CALLS:
                violations.append({"kind": "call", "name": node.func.attr})
    return {"ok": not violations, "violations": violations}


def build_harnesses(
    clang: Path,
    harness_dir: Path,
    candidate_ids: list[str],
    candidates: dict[str, sbm.CandidateInfo],
    functions: dict[str, sbm.FunctionInfo],
    labels: dict[str, dict[str, Any]],
    fixtures: dict[str, list[dict[str, Any]]],
) -> dict[str, HarnessInfo]:
    harnesses: dict[str, HarnessInfo] = {}
    if not sbm.libfuzzer_smoke_available(clang):
        for cid in candidate_ids:
            harnesses[cid] = HarnessInfo(cid, False, None, None, "clang_libfuzzer_unavailable", {})
        return harnesses
    for cid in candidate_ids:
        candidate = candidates[cid]
        function = functions[candidate.function_id]
        cdir = harness_dir / sbm.safe_name(cid)
        build = sbm.build_libfuzzer_harness(clang, cdir, candidate, function, fixtures[function.function_id])
        if not build.get("ok"):
            harnesses[cid] = HarnessInfo(cid, False, None, None, str(build.get("reason", "build_failed")), build)
            continue
        validation = sbm.validate_libfuzzer_harness_semantics(clang, cdir, candidate, function, labels[cid])
        if not validation.get("ok"):
            harnesses[cid] = HarnessInfo(cid, False, None, None, str(validation.get("reason", "validation_failed")), validation)
            continue
        harnesses[cid] = HarnessInfo(cid, True, Path(build["exe"]), Path(build["seed_dir"]), "", validation)
    return harnesses


def run_budget_jobs(
    jobs: list[RunJob],
    harnesses: dict[str, HarnessInfo],
    candidates: dict[str, sbm.CandidateInfo],
    functions: dict[str, sbm.FunctionInfo],
    labels: dict[str, dict[str, Any]],
    population: dict[str, list[str]],
    matrix_dir: Path,
    confirmer: WitnessConfirmer,
    max_workers: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(run_one_wallclock_job, job, harnesses[job.candidate_id], candidates, functions, labels, population, matrix_dir, confirmer)
            for job in jobs
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    return rows


def run_one_wallclock_job(
    job: RunJob,
    harness: HarnessInfo,
    candidates: dict[str, sbm.CandidateInfo],
    functions: dict[str, sbm.FunctionInfo],
    labels: dict[str, dict[str, Any]],
    population: dict[str, list[str]],
    matrix_dir: Path,
    confirmer: WitnessConfirmer,
) -> dict[str, Any]:
    candidate = candidates[job.candidate_id]
    function = functions[candidate.function_id]
    label = labels[job.candidate_id]
    assert harness.exe is not None and harness.seed_dir is not None
    run_dir = matrix_dir / f"budget_{budget_label(job.budget_s)}" / sbm.safe_name(job.candidate_id) / f"seed_{job.seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    row_path = run_dir / "row.json"
    if row_path.exists():
        return json.loads(row_path.read_text(encoding="utf-8"))
    corpus_dir = run_dir / "seed_corpus"
    prepare_run_corpus(harness.seed_dir, corpus_dir)
    log_path = run_dir / "fuzzer.log"
    if log_path.exists():
        log_path.unlink()
    result = invoke_fuzzer_wallclock(harness.exe, corpus_dir, log_path, job.seed, job.budget_s)
    sequence = sbm.parse_fuzzer_log(log_path)
    witness = next((row for row in sequence if row["mismatch"]), None)
    confirmation = {"confirmed": False, "method": "not_applicable", "reason": "no_witness"}
    if witness:
        confirmation = confirmer.confirm(job.candidate_id, witness["args"])
    row = wallclock_result_row(candidate, function, label, population, job.seed, job.budget_s, sequence, witness, confirmation, result, log_path)
    row_path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
    return row


def invoke_fuzzer_wallclock(exe: Path, seed_dir: Path, log_path: Path, seed: int, budget_s: float) -> dict[str, Any]:
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    env["PHASE1F_FUZZER_LOG"] = str(log_path)
    env["PHASE1F_EVAL_LIMIT"] = ""
    env["CUDA_VISIBLE_DEVICES"] = ""
    cmd = [
        str(exe),
        str(seed_dir),
        f"-seed={seed}",
        "-use_value_profile=0",
        "-print_final_stats=0",
        "-close_fd_mask=3",
        f"-artifact_prefix={exe.parent.as_posix()}/",
    ]
    started = time.perf_counter()
    try:
        process = subprocess.Popen(cmd, cwd=exe.parent, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, start_new_session=True)
    except OSError as exc:
        return {
            "returncode": "",
            "timed_out": False,
            "crash": False,
            "infrastructure_failure": True,
            "infrastructure_reason": f"popen_failed:{exc}",
            "process_startup_time_s": "",
            "elapsed_wall_clock_s": time.perf_counter() - started,
            "stderr_tail": "",
        }
    after_spawn = time.perf_counter()
    startup_s = after_spawn - started
    remaining = max(0.0, budget_s - startup_s)
    stdout = ""
    stderr = ""
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_group(process)
        try:
            stdout, stderr = process.communicate(timeout=TERMINATION_TOLERANCE_S)
        except subprocess.TimeoutExpired as exc:
            kill_process_group(process)
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else "process did not terminate after SIGKILL"
            return {
                "returncode": process.returncode if process.returncode is not None else "",
                "timed_out": True,
                "crash": False,
                "infrastructure_failure": True,
                "infrastructure_reason": "process_group_did_not_terminate_within_tolerance",
                "process_startup_time_s": startup_s,
                "elapsed_wall_clock_s": time.perf_counter() - started,
                "stdout_tail": (stdout or "")[-1000:],
                "stderr_tail": (stderr or "")[-1000:],
            }
    elapsed = time.perf_counter() - started
    return {
        "returncode": process.returncode,
        "timed_out": timed_out,
        "crash": bool(process.returncode not in {0, None, -9} and not timed_out),
        "infrastructure_failure": False,
        "infrastructure_reason": "",
        "process_startup_time_s": startup_s,
        "elapsed_wall_clock_s": elapsed,
        "stdout_tail": (stdout or "")[-1000:],
        "stderr_tail": (stderr or "")[-1000:],
    }


def kill_process_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        process.kill()


def wallclock_result_row(
    candidate: sbm.CandidateInfo,
    function: sbm.FunctionInfo,
    label: dict[str, Any],
    population: dict[str, list[str]],
    seed: int,
    budget_s: float,
    sequence: list[dict[str, Any]],
    witness: dict[str, Any] | None,
    confirmation: dict[str, Any],
    run: dict[str, Any],
    log_path: Path,
) -> dict[str, Any]:
    unique = {tuple(row["args"]) for row in sequence}
    first_elapsed = sequence[0]["elapsed_s"] if sequence else ""
    last_elapsed = sequence[-1]["elapsed_s"] if sequence else 0.0
    witness_confirmed = bool(witness and confirmation.get("confirmed"))
    false_alarm = bool(witness_confirmed and label["label"] == "no_mismatch_under_exact_holdout_domain")
    return {
        "candidate_id": candidate.candidate_id,
        "project": candidate.project,
        "function_id": candidate.function_id,
        "candidate_stratum": candidate.candidate_stratum,
        "mutation_family": candidate.mutation_family,
        "mismatch_density_bucket": density_bucket(label),
        "source_literal_availability": function.source_literal_count > 0,
        "source_literal_count": function.source_literal_count,
        "label": label["label"],
        "seed": seed,
        "wall_clock_budget_s": budget_s,
        "supported_by_libfuzzer_pipeline": True,
        "baseline_status": "completed",
        "unsupported_reason": "",
        "source_literal_dictionary_used": False,
        "exact_mismatch_witness_provided": False,
        "seed_corpus": "four_sealed_fixtures_only",
        "process_startup_time_s": run["process_startup_time_s"],
        "harness_initialization_time_s": "",
        "harness_initialization_time_note": "not self-reported by reused Phase 1f harness",
        "first_in_process_eval_time_s": first_elapsed,
        "in_process_fuzzing_time_s": last_elapsed,
        "end_to_end_elapsed_time_s": run["elapsed_wall_clock_s"],
        "completed_input_evaluations": len(sequence),
        "unique_exact_domain_inputs": len(unique),
        "exact_domain_coverage_fraction": sbm.safe_div(len(unique), function.domain_size),
        "witness_found": bool(witness),
        "first_witness_input": json.dumps(witness["args"]) if witness else "",
        "witness_confirmed": witness_confirmed,
        "witness_confirmation": json.dumps(confirmation, sort_keys=True),
        "evaluations_to_first_witness": witness["eval"] if witness else "",
        "in_process_time_to_first_witness_s": witness["elapsed_s"] if witness else "",
        "end_to_end_time_to_first_witness_s": run["elapsed_wall_clock_s"] if witness else "",
        "timeout": bool(run["timed_out"] and not witness),
        "crash": bool(run["crash"] and not witness),
        "infrastructure_failure": bool(run["infrastructure_failure"]),
        "infrastructure_reason": run.get("infrastructure_reason", ""),
        "no_mismatch_false_alarm": false_alarm,
        "process_returncode": run["returncode"],
        "stderr_tail": run.get("stderr_tail", ""),
        "ordered_input_sequence_prefix": json.dumps([row["args"] for row in sequence[:1024]]),
        "ordered_input_sequence_sha256": sbm.sha256_text(json.dumps([row["args"] for row in sequence], sort_keys=True)),
        "sequence_truncated": len(sequence) > 1024,
        "output_log_path": str(log_path),
    }


def unsupported_budget_rows(
    budget: float,
    candidate_ids: list[str],
    harnesses: dict[str, HarnessInfo],
    candidates: dict[str, sbm.CandidateInfo],
    functions: dict[str, sbm.FunctionInfo],
    labels: dict[str, dict[str, Any]],
    population: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows = []
    for cid in candidate_ids:
        harness = harnesses[cid]
        if harness.ok:
            continue
        candidate = candidates[cid]
        function = functions[candidate.function_id]
        label = labels[cid]
        for seed in sbm.RANDOM_SEEDS:
            rows.append(
                {
                    "candidate_id": cid,
                    "project": candidate.project,
                    "function_id": candidate.function_id,
                    "candidate_stratum": candidate.candidate_stratum,
                    "mutation_family": candidate.mutation_family,
                    "mismatch_density_bucket": density_bucket(label),
                    "source_literal_availability": function.source_literal_count > 0,
                    "source_literal_count": function.source_literal_count,
                    "label": label["label"],
                    "seed": seed,
                    "wall_clock_budget_s": budget,
                    "supported_by_libfuzzer_pipeline": False,
                    "baseline_status": "unsupported",
                    "unsupported_reason": harness.reason,
                    "support_validation": json.dumps(harness.validation, sort_keys=True),
                    "source_literal_dictionary_used": False,
                    "exact_mismatch_witness_provided": False,
                    "seed_corpus": "four_sealed_fixtures_only_when_supported",
                    "process_startup_time_s": "",
                    "harness_initialization_time_s": "",
                    "harness_initialization_time_note": "unsupported candidate was not executed",
                    "first_in_process_eval_time_s": "",
                    "in_process_fuzzing_time_s": "",
                    "end_to_end_elapsed_time_s": "",
                    "completed_input_evaluations": 0,
                    "unique_exact_domain_inputs": 0,
                    "exact_domain_coverage_fraction": 0.0,
                    "witness_found": False,
                    "first_witness_input": "",
                    "witness_confirmed": False,
                    "witness_confirmation": json.dumps({"confirmed": False, "reason": "unsupported"}, sort_keys=True),
                    "evaluations_to_first_witness": "",
                    "in_process_time_to_first_witness_s": "",
                    "end_to_end_time_to_first_witness_s": "",
                    "timeout": False,
                    "crash": False,
                    "infrastructure_failure": False,
                    "infrastructure_reason": "",
                    "no_mismatch_false_alarm": False,
                    "process_returncode": "",
                    "stderr_tail": "",
                    "ordered_input_sequence_prefix": "",
                    "ordered_input_sequence_sha256": "",
                    "sequence_truncated": False,
                    "output_log_path": "",
                }
            )
    return rows


def summarize_wallclock_runs(run_rows: list[dict[str, Any]], population: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scopes = {
        sbm.PRIMARY_SCOPE: set(population[sbm.PRIMARY_SCOPE]),
        sbm.LOW_DENSITY_SCOPE: set(population[sbm.LOW_DENSITY_SCOPE]),
        sbm.NON_FIXTURE_SCOPE: set(population[sbm.NON_FIXTURE_SCOPE]),
        sbm.NO_MISMATCH_SCOPE: set(population[sbm.NO_MISMATCH_SCOPE]),
        "natural_ghidra_no_mismatch": set(population["natural_ghidra_no_mismatch"]),
    }
    for budget in WALL_CLOCK_BUDGETS:
        budget_rows = [row for row in run_rows if float(row["wall_clock_budget_s"]) == budget]
        for scope, ids in scopes.items():
            scope_rows = [row for row in budget_rows if row["candidate_id"] in ids]
            supported_rows = [row for row in scope_rows if row["supported_by_libfuzzer_pipeline"]]
            supported_candidates = {row["candidate_id"] for row in supported_rows}
            per_seed = []
            for seed in sbm.RANDOM_SEEDS:
                seed_rows = [row for row in scope_rows if int(row["seed"]) == seed]
                detected = {row["candidate_id"] for row in seed_rows if row["witness_confirmed"]}
                per_seed.append(sbm.safe_div(len(detected), len(ids)))
            all_detected_counts = candidate_detection_counts(scope_rows)
            detected_all = sorted(cid for cid, count in all_detected_counts.items() if count == len(sbm.RANDOM_SEEDS))
            detected_any = sorted(cid for cid, count in all_detected_counts.items() if count > 0)
            never = sorted(ids - set(detected_any))
            detected_rows = [row for row in scope_rows if row["witness_confirmed"]]
            no_mismatch_rows = [row for row in scope_rows if row["label"] == "no_mismatch_under_exact_holdout_domain"]
            rows.append(
                {
                    "wall_clock_budget_s": budget,
                    "population": scope,
                    "candidate_denominator": len(ids),
                    "supported_candidates": len(supported_candidates),
                    "total_runs": len(scope_rows),
                    "supported_runs": len(supported_rows),
                    "mean_detection": statistics.mean(per_seed) if per_seed else 0.0,
                    "median_detection": sbm.percentile(per_seed, 0.5),
                    "stddev_detection": statistics.pstdev(per_seed) if len(per_seed) > 1 else 0.0,
                    "p2_5_detection": sbm.percentile(per_seed, 0.025),
                    "p97_5_detection": sbm.percentile(per_seed, 0.975),
                    "best_seed_detection": max(per_seed) if per_seed else 0.0,
                    "worst_seed_detection": min(per_seed) if per_seed else 0.0,
                    "median_completed_evaluations": median_or_blank([int(row["completed_input_evaluations"]) for row in supported_rows]),
                    "median_unique_domain_coverage": median_or_blank([int(row["unique_exact_domain_inputs"]) for row in supported_rows]),
                    "median_exact_domain_coverage_fraction": median_or_blank([float(row["exact_domain_coverage_fraction"]) for row in supported_rows]),
                    "median_end_to_end_time_to_witness_s": median_or_blank([float(row["end_to_end_time_to_first_witness_s"]) for row in detected_rows if row["end_to_end_time_to_first_witness_s"] != ""]),
                    "median_in_process_time_to_witness_s": median_or_blank([float(row["in_process_time_to_first_witness_s"]) for row in detected_rows if row["in_process_time_to_first_witness_s"] != ""]),
                    "candidates_never_detected_any_seed_count": len(never),
                    "candidates_never_detected_any_seed": json.dumps(never),
                    "candidates_detected_all_seeds_count": len(detected_all),
                    "candidates_detected_all_seeds": json.dumps(detected_all),
                    "source_candidate_mismatch_findings": sum(1 for row in no_mismatch_rows if row["witness_found"]),
                    "confirmed_in_domain_mismatch_findings": sum(1 for row in no_mismatch_rows if row["witness_confirmed"]),
                    "no_mismatch_false_alarms": sum(1 for row in no_mismatch_rows if row["no_mismatch_false_alarm"]),
                    "distinct_no_mismatch_false_alarm_candidates": len({row["candidate_id"] for row in no_mismatch_rows if row["no_mismatch_false_alarm"]}),
                    "crashes": sum(1 for row in scope_rows if row["crash"]),
                    "timeouts": sum(1 for row in scope_rows if row["timeout"]),
                    "infrastructure_failures": sum(1 for row in scope_rows if row["infrastructure_failure"]),
                    "unsupported_runs": sum(1 for row in scope_rows if not row["supported_by_libfuzzer_pipeline"]),
                    "baseline_status": "completed",
                    "source_literal_dictionary_used": False,
                    "exact_mismatch_witnesses_provided": False,
                    "clang_version": sbm.command_first_line([str(CLANG), "--version"]),
                }
            )
    return rows


def candidate_detection_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, set[int]] = {}
    for row in rows:
        if row["witness_confirmed"]:
            counts.setdefault(row["candidate_id"], set()).add(int(row["seed"]))
    return {cid: len(seeds) for cid, seeds in counts.items()}


def candidate_set_comparisons(
    run_rows: list[dict[str, Any]],
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows = []
    primary = population[sbm.PRIMARY_SCOPE]
    final = sbm.detected_set(first_rows, sbm.FINAL_POLICY, 8, None, primary)
    all_ids = set(primary)
    for budget in WALL_CLOCK_BUDGETS:
        budget_rows = [row for row in run_rows if float(row["wall_clock_budget_s"]) == budget and row["candidate_id"] in all_ids]
        lib_ids = {row["candidate_id"] for row in budget_rows if row["witness_confirmed"]}
        both = sorted(final & lib_ids)
        final_only = sorted(final - lib_ids)
        lib_only = sorted(lib_ids - final)
        neither = sorted(all_ids - final - lib_ids)
        rows.append(
            {
                "wall_clock_budget_s": budget,
                "population": sbm.PRIMARY_SCOPE,
                "libfuzzer_detection_rule": "detected_by_any_of_30_fixed_seeds",
                "denominator": len(primary),
                "frozen_final_detected_b8": len(final),
                "libfuzzer_detected_candidates": len(lib_ids),
                "detected_by_both_count": len(both),
                "detected_only_by_final_count": len(final_only),
                "detected_only_by_libfuzzer_count": len(lib_only),
                "detected_by_neither_count": len(neither),
                "detected_by_both": json.dumps(both),
                "detected_only_by_final": json.dumps(final_only),
                "detected_only_by_libfuzzer": json.dumps(lib_only),
                "detected_by_neither": json.dumps(neither),
            }
        )
    return rows


def failure_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for row in run_rows:
        if (
            not row["supported_by_libfuzzer_pipeline"]
            or row["timeout"]
            or row["crash"]
            or row["infrastructure_failure"]
            or row["no_mismatch_false_alarm"]
        ):
            failures.append(row)
    return failures


def detection_curve_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in summary_rows:
        if row["population"] in {sbm.PRIMARY_SCOPE, sbm.LOW_DENSITY_SCOPE, sbm.NON_FIXTURE_SCOPE}:
            rows.append(
                {
                    "baseline": "libFuzzer",
                    "timing_view": "end_to_end",
                    "wall_clock_budget_s": row["wall_clock_budget_s"],
                    "population": row["population"],
                    "mean_detection": row["mean_detection"],
                    "median_detection": row["median_detection"],
                    "p2_5_detection": row["p2_5_detection"],
                    "p97_5_detection": row["p97_5_detection"],
                    "frozen_final_detection_at_b8": sbm.safe_div(FROZEN_FINAL_DETECTED_B8, FROZEN_FINAL_DENOMINATOR),
                }
            )
    return rows


def time_to_witness_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in summary_rows:
        if row["population"] in {sbm.PRIMARY_SCOPE, sbm.LOW_DENSITY_SCOPE, sbm.NON_FIXTURE_SCOPE}:
            rows.append(
                {
                    "baseline": "libFuzzer",
                    "wall_clock_budget_s": row["wall_clock_budget_s"],
                    "population": row["population"],
                    "median_end_to_end_time_to_witness_s": row["median_end_to_end_time_to_witness_s"],
                    "median_in_process_time_to_witness_s": row["median_in_process_time_to_witness_s"],
                    "median_completed_evaluations": row["median_completed_evaluations"],
                    "median_unique_domain_coverage": row["median_unique_domain_coverage"],
                }
            )
    return rows


def write_tables(
    repo_root: Path,
    summary_rows: list[dict[str, Any]],
    candidate_set_rows: list[dict[str, Any]],
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
) -> None:
    table_dir = repo_root / "paper/tables"
    primary_rows = [row for row in summary_rows if row["population"] == sbm.PRIMARY_SCOPE]
    low_rows = [row for row in summary_rows if row["population"] == sbm.LOW_DENSITY_SCOPE]
    non_fixture_rows = [row for row in summary_rows if row["population"] == sbm.NON_FIXTURE_SCOPE]
    no_mismatch = [row for row in summary_rows if row["population"] == sbm.NO_MISMATCH_SCOPE]
    natural_nm = [row for row in summary_rows if row["population"] == "natural_ghidra_no_mismatch"]
    table_rows = []
    for row in primary_rows:
        low = find_summary(low_rows, row["wall_clock_budget_s"])
        non_fixture = find_summary(non_fixture_rows, row["wall_clock_budget_s"])
        nm = find_summary(no_mismatch, row["wall_clock_budget_s"])
        table_rows.append([
            row["wall_clock_budget_s"],
            fmt_rate(row["mean_detection"]),
            fmt_rate(row["p2_5_detection"]),
            fmt_rate(row["p97_5_detection"]),
            fmt_rate(low["mean_detection"]),
            fmt_rate(non_fixture["mean_detection"]),
            row["median_completed_evaluations"],
            nm["no_mismatch_false_alarms"],
        ])
    sbm.write_latex_table(
        table_dir / "libfuzzer_wallclock.tex",
        "CPU-only libFuzzer wall-clock baseline",
        ["Budget (s)", "Primary mean", "P2.5", "P97.5", "Low-density", "Non-overfit", "Median evals", "False alarms"],
        table_rows,
    )
    final_timing = frozen_final_timing(repo_root, first_rows, population)
    cost_rows = [
        [
            "Frozen final B=8",
            "8 concrete evaluations",
            f"{FROZEN_FINAL_DETECTED_B8}/{FROZEN_FINAL_DENOMINATOR}",
            fmt_rate(sbm.safe_div(FROZEN_FINAL_DETECTED_B8, FROZEN_FINAL_DENOMINATOR)),
            final_timing["median_complete_prefix_time_s"],
            final_timing["median_early_stop_time_s"],
            "deterministic concrete probes",
        ]
    ]
    for row in primary_rows:
        cost_rows.append([
            "libFuzzer",
            f"{row['wall_clock_budget_s']} s end-to-end",
            "",
            fmt_rate(row["mean_detection"]),
            row["median_end_to_end_time_to_witness_s"],
            row["median_in_process_time_to_witness_s"],
            f"median evals {row['median_completed_evaluations']}",
        ])
    natural5 = find_summary(natural_nm, 5.0)
    cost_rows.append(["Natural Ghidra no-mismatch", "5 s", "", "", "", "", f"false alarms {natural5['no_mismatch_false_alarms']}"])
    sbm.write_latex_table(
        table_dir / "libfuzzer_cost_comparison.tex",
        "Frozen policy and libFuzzer cost views",
        ["Method", "Resource", "Detected", "Detection", "Complete/e2e time", "Early/in-process time", "Notes"],
        cost_rows,
    )


def write_plot_script(repo_root: Path) -> None:
    script = repo_root / "figures/plot_libfuzzer_wallclock.py"
    script.write_text(
        """from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_detection() -> None:
    data = [row for row in rows("libfuzzer_wallclock_detection.csv") if row["population"] in {"primary_fixture_passing_wrong", "low_density_fixture_passing_wrong", "non_fixture_overfit_fixture_passing_wrong"}]
    fig, ax = plt.subplots(figsize=(6.2, 3.9))
    labels = {
        "primary_fixture_passing_wrong": "Primary",
        "low_density_fixture_passing_wrong": "Low density",
        "non_fixture_overfit_fixture_passing_wrong": "Non-overfit",
    }
    for population in labels:
        items = sorted([row for row in data if row["population"] == population], key=lambda row: float(row["wall_clock_budget_s"]))
        ax.plot([float(row["wall_clock_budget_s"]) for row in items], [float(row["mean_detection"]) for row in items], marker="o", linewidth=1.4, label=labels[population])
    if not data:
        raise RuntimeError("libfuzzer_wallclock_detection.csv has no rows")
    final_ref = float(data[0]["frozen_final_detection_at_b8"])
    ax.axhline(final_ref, color="black", linestyle="--", linewidth=1.0, label="Frozen final Detection@8")
    ax.set_xscale("log")
    ax.set_xlabel("libFuzzer end-to-end wall-clock budget (s)")
    ax.set_ylabel("Detection")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/libfuzzer_wallclock_detection.pdf")


def plot_time_to_witness() -> None:
    data = [row for row in rows("libfuzzer_wallclock_time_to_witness.csv") if row["population"] == "primary_fixture_passing_wrong"]
    items = sorted(data, key=lambda row: float(row["wall_clock_budget_s"]))
    fig, ax1 = plt.subplots(figsize=(6.1, 3.8))
    budgets = [float(row["wall_clock_budget_s"]) for row in items]
    e2e = [float(row["median_end_to_end_time_to_witness_s"] or 0.0) for row in items]
    proc = [float(row["median_in_process_time_to_witness_s"] or 0.0) for row in items]
    ax1.plot(budgets, e2e, marker="o", linewidth=1.4, label="End-to-end")
    ax1.plot(budgets, proc, marker="s", linewidth=1.4, label="In-process")
    ax1.set_xscale("log")
    ax1.set_xlabel("libFuzzer wall-clock budget (s)")
    ax1.set_ylabel("Median time to witness (s)")
    ax1.grid(True, alpha=0.25)
    ax1.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/libfuzzer_wallclock_time_to_witness.pdf")


if __name__ == "__main__":
    plot_detection()
    plot_time_to_witness()
""",
        encoding="utf-8",
    )


def generate_figures(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "figures/plot_libfuzzer_wallclock.py")],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def write_handoff(
    repo_root: Path,
    summary_rows: list[dict[str, Any]],
    candidate_set_rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    environment: dict[str, Any],
    preflight: dict[str, Any],
    first_rows: list[dict[str, Any]],
    population: dict[str, list[str]],
) -> Path:
    path = repo_root / "docs/paper_agent/libfuzzer_wallclock_handoff.md"
    branch = git_output(repo_root, ["branch", "--show-current"])
    head = git_output(repo_root, ["rev-parse", "HEAD"])
    prereg_commit = git_output(repo_root, ["log", "-n", "1", "--format=%H", "--", str(PREREG_PATH)])
    primary = {float(row["wall_clock_budget_s"]): row for row in summary_rows if row["population"] == sbm.PRIMARY_SCOPE}
    low = {float(row["wall_clock_budget_s"]): row for row in summary_rows if row["population"] == sbm.LOW_DENSITY_SCOPE}
    non_fixture = {float(row["wall_clock_budget_s"]): row for row in summary_rows if row["population"] == sbm.NON_FIXTURE_SCOPE}
    no_mismatch = {float(row["wall_clock_budget_s"]): row for row in summary_rows if row["population"] == sbm.NO_MISMATCH_SCOPE}
    final_timing = frozen_final_timing(repo_root, first_rows, population)
    gate = interpretation_gate(summary_rows)
    set5 = next(row for row in candidate_set_rows if float(row["wall_clock_budget_s"]) == 5.0 and row["libfuzzer_detection_rule"] == "detected_by_any_of_30_fixed_seeds")
    lines = [
        "# libFuzzer Wall-Clock Handoff",
        "",
        "## Git And Seals",
        "",
        f"- Branch: `{branch}`",
        f"- Preregistration commit: `{prereg_commit}`",
        f"- Generated-at commit context: `{head}`",
        "- Result commit and final HEAD: the commit containing this handoff; the exact hash is available after commit creation.",
        f"- Verified holdout seal: `{VERIFIED_HOLDOUT_SEAL}`",
        f"- Frozen method commit: `{METHOD_FREEZE_COMMIT}`",
        f"- Phase 1e result: `{PHASE1E_RESULT_COMMIT}`",
        f"- Phase 1f artifact commit: `{PHASE1F_RESULT_ARTIFACT_COMMIT}`",
        f"- Preflight OK: `{preflight['ok']}`",
        "",
        "## Environment",
        "",
        f"- Clang/libFuzzer: `{environment['clang_version']}`",
        f"- CPU: `{environment['cpu_model']}`",
        f"- OS: `{environment['platform']}`",
        f"- Worker configuration: `{environment['max_workers']}` workers; CPU affinity `{environment['cpu_affinity_policy']}`",
        f"- GPU usage: `{environment['gpu_usage']}`",
        f"- Runs completed: `{environment['completed_supported_runs']}` supported runs plus `{environment['unsupported_rows']}` unsupported rows",
        "",
        "## Detection",
        "",
    ]
    for budget in WALL_CLOCK_BUDGETS:
        lines.append(
            f"- {budget:g}s primary Detection mean `{fmt_rate(primary[budget]['mean_detection'])}` "
            f"(median `{fmt_rate(primary[budget]['median_detection'])}`); "
            f"low-density `{fmt_rate(low[budget]['mean_detection'])}`; "
            f"non-fixture-overfit `{fmt_rate(non_fixture[budget]['mean_detection'])}`"
        )
    lines.extend([
        "",
        "## Cost And Failures",
        "",
        f"- Frozen final B=8 Detection: `{FROZEN_FINAL_DETECTED_B8}/{FROZEN_FINAL_DENOMINATOR}`.",
        f"- Frozen final median complete-prefix time: `{final_timing['median_complete_prefix_time_s']}`.",
        f"- Frozen final median simulated early-stop time: `{final_timing['median_early_stop_time_s']}`.",
    ])
    for budget in WALL_CLOCK_BUDGETS:
        row = primary[budget]
        nm = no_mismatch[budget]
        lines.append(
            f"- libFuzzer {budget:g}s median evaluations `{row['median_completed_evaluations']}`, "
            f"median end-to-end witness time `{row['median_end_to_end_time_to_witness_s']}`, "
            f"median in-process witness time `{row['median_in_process_time_to_witness_s']}`, "
            f"no-mismatch false alarms `{nm['no_mismatch_false_alarms']}`, "
            f"crashes `{nm['crashes']}`, timeouts `{nm['timeouts']}`, infrastructure failures `{nm['infrastructure_failures']}`"
        )
    lines.extend([
        "",
        "## Candidate Sets",
        "",
        f"- At 5s, both final and libFuzzer detect `{set5['detected_by_both_count']}` primary candidates.",
        f"- At 5s, final-only candidates: `{set5['detected_only_by_final']}`",
        f"- At 5s, libFuzzer-only candidates: `{set5['detected_only_by_libfuzzer']}`",
        f"- At 5s, neither-detected candidates: `{set5['detected_by_neither']}`",
        "",
        "## Interpretation",
        "",
        f"- Gate outcome: `{gate['outcome']}`",
        f"- Paper-claim consequence: {gate['paper_claim_consequence']}",
        "",
        "## Tests Run",
        "",
        "- `python -m py_compile analysis/decompile_faithfulness/libfuzzer_wallclock.py`",
        "- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition analysis.decompile_faithfulness.tests.test_holdout_evaluation analysis.decompile_faithfulness.tests.test_strong_baselines_and_mechanism analysis.decompile_faithfulness.tests.test_libfuzzer_wallclock`",
        "",
        "The Phase 1g run reused the Phase 1f libFuzzer harness semantics, did not provide source-literal dictionaries or exact mismatch witnesses, did not install or run KLEE, did not use GPU devices, and did not invoke the frozen final auditor.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def interpretation_gate(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary = {float(row["wall_clock_budget_s"]): row for row in summary_rows if row["population"] == sbm.PRIMARY_SCOPE}
    no_mismatch = {float(row["wall_clock_budget_s"]): row for row in summary_rows if row["population"] == sbm.NO_MISMATCH_SCOPE}
    final_rate = sbm.safe_div(FROZEN_FINAL_DETECTED_B8, FROZEN_FINAL_DENOMINATOR)
    lib_01 = float(primary[0.1]["mean_detection"])
    lib_1 = float(primary[1.0]["mean_detection"])
    lib_5 = float(primary[5.0]["mean_detection"])
    false_alarms = sum(int(row["no_mismatch_false_alarms"]) for row in no_mismatch.values())
    median_evals_01 = float(primary[0.1]["median_completed_evaluations"] or 0.0)
    strong = lib_01 < final_rate - 0.05 and median_evals_01 >= 8 and false_alarms == 0
    catches_up = (lib_1 >= final_rate or lib_5 >= final_rate) and lib_01 < final_rate
    if strong:
        outcome = "strong_early_yield_support"
        consequence = "The frozen source-conditioned policy provides higher early witness yield than coverage-guided fuzzing in the evaluated startup-dominated, low-budget regime."
    elif catches_up:
        outcome = "cost_regime_differentiation"
        consequence = "Coverage-guided fuzzing catches up with additional time or executions, whereas the frozen policy targets deterministic early witness discovery."
    else:
        outcome = "weak_comparative_support"
        consequence = "The frozen policy is a deterministic solver-free alternative, but the evaluation does not establish superiority over coverage-guided fuzzing."
    return {"outcome": outcome, "paper_claim_consequence": consequence}


def frozen_final_timing(repo_root: Path, first_rows: list[dict[str, Any]], population: dict[str, list[str]]) -> dict[str, Any]:
    primary = set(population[sbm.PRIMARY_SCOPE])
    early = [
        float(row["time_to_first_witness_s"])
        for row in first_rows
        if row["candidate_id"] in primary
        and row["policy"] == sbm.FINAL_POLICY
        and row["budget"] == 8
        and row["random_seed"] is None
        and row["time_to_first_witness_s"] is not None
    ]
    complete_times: dict[str, float] = {}
    with (repo_root / "results/decompile_faithfulness/holdout_policy_traces.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if (
                row["candidate_id"] in primary
                and row["policy"] == sbm.FINAL_POLICY
                and int(row["budget"]) == 8
                and row.get("random_seed") is None
            ):
                complete_times[row["candidate_id"]] = complete_times.get(row["candidate_id"], 0.0) + float(row.get("elapsed_generation_time_s", 0.0)) + float(row.get("elapsed_execution_time_s", 0.0))
    return {
        "median_early_stop_time_s": median_or_blank(early),
        "median_complete_prefix_time_s": median_or_blank(list(complete_times.values())),
    }


def prepare_run_corpus(seed_dir: Path, corpus_dir: Path) -> None:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    for existing in corpus_dir.iterdir():
        if existing.is_dir():
            shutil.rmtree(existing)
        else:
            existing.unlink()
    for seed_file in sorted(seed_dir.iterdir()):
        if seed_file.is_file():
            shutil.copy2(seed_file, corpus_dir / seed_file.name)


def render_confirmation_harness(function: sbm.FunctionInfo, source_text: str, candidate_text: str, args: list[int]) -> str:
    function_name = function.function_name
    source_name = "phase1g_source_" + sbm.safe_c_identifier(function_name)
    candidate_name = "phase1g_candidate_" + sbm.safe_c_identifier(function_name)
    call_args = ", ".join(str(int(value)) for value in args)
    return f"""#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

#define {function_name} {source_name}
{source_text.rstrip()}
#undef {function_name}

#define {function_name} {candidate_name}
{candidate_text.rstrip()}
#undef {function_name}

int main(void) {{
    long long source_output = (long long){source_name}({call_args});
    long long candidate_output = (long long){candidate_name}({call_args});
    printf("source:%lld\\n", source_output);
    printf("candidate:%lld\\n", candidate_output);
    return 0;
}}
"""


def parse_confirmation_stdout(stdout: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in stdout.splitlines():
        if line.startswith("source:"):
            parsed["source_output"] = int(line.split(":", 1)[1])
        if line.startswith("candidate:"):
            parsed["candidate_output"] = int(line.split(":", 1)[1])
    return parsed


def check_population(population: dict[str, list[str]]) -> None:
    expected = {
        sbm.PRIMARY_SCOPE: 37,
        sbm.LOW_DENSITY_SCOPE: 16,
        sbm.NON_FIXTURE_SCOPE: 15,
        sbm.NO_MISMATCH_SCOPE: 34,
        "natural_ghidra_no_mismatch": 16,
    }
    observed = {key: len(population.get(key, [])) for key in expected}
    if observed != expected:
        raise RuntimeError(f"unexpected Phase 1e population sizes: {observed}")


def environment_manifest(
    repo_root: Path,
    run_root: Path,
    max_workers: int,
    harnesses: dict[str, HarnessInfo],
    population: dict[str, list[str]],
    command: str,
) -> dict[str, Any]:
    completed_supported_runs = sum(1 for item in harnesses.values() if item.ok) * len(sbm.RANDOM_SEEDS) * len(WALL_CLOCK_BUDGETS)
    unsupported_rows = sum(1 for item in harnesses.values() if not item.ok) * len(sbm.RANDOM_SEEDS) * len(WALL_CLOCK_BUDGETS)
    return {
        "created_at_utc": now_utc(),
        "branch": git_output(repo_root, ["branch", "--show-current"]),
        "head": git_output(repo_root, ["rev-parse", "HEAD"]),
        "command": command,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "verified_holdout_seal": VERIFIED_HOLDOUT_SEAL,
        "phase1e_result": PHASE1E_RESULT_COMMIT,
        "phase1f_result_artifact_commit": PHASE1F_RESULT_ARTIFACT_COMMIT,
        "clang_path": str(CLANG),
        "clang_version": sbm.command_first_line([str(CLANG), "--version"]),
        "compiler_flags": "-std=c11 -O1 -g -fsanitize=fuzzer,address,undefined -fno-sanitize-recover=all",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "max_workers": max_workers,
        "cpu_affinity_policy": "none_explicit",
        "gpu_usage": "none; CUDA_VISIBLE_DEVICES cleared for libFuzzer subprocesses",
        "wall_clock_budgets_s": WALL_CLOCK_BUDGETS,
        "termination_tolerance_s": TERMINATION_TOLERANCE_S,
        "fixed_random_seeds": sbm.RANDOM_SEEDS,
        "source_literal_dictionary_used": False,
        "exact_mismatch_witnesses_provided": False,
        "seed_corpus": "four_sealed_fixtures_only",
        "phase1f_harness_reuse": {
            "module": "analysis.decompile_faithfulness.strong_baselines_and_mechanism",
            "module_sha256": sha256_path(repo_root / "analysis/decompile_faithfulness/strong_baselines_and_mechanism.py"),
            "functions": [
                "build_libfuzzer_harness",
                "validate_libfuzzer_harness_semantics",
                "parse_fuzzer_log",
                "bytes_to_domain_tuple",
                "encode_domain_tuple",
            ],
        },
        "population_counts": {
            sbm.PRIMARY_SCOPE: len(population[sbm.PRIMARY_SCOPE]),
            sbm.LOW_DENSITY_SCOPE: len(population[sbm.LOW_DENSITY_SCOPE]),
            sbm.NON_FIXTURE_SCOPE: len(population[sbm.NON_FIXTURE_SCOPE]),
            sbm.NO_MISMATCH_SCOPE: len(population[sbm.NO_MISMATCH_SCOPE]),
            "natural_ghidra_no_mismatch": len(population["natural_ghidra_no_mismatch"]),
        },
        "declared_candidate_count": len(sbm.baseline_candidate_ids(population)),
        "supported_candidate_count": sum(1 for item in harnesses.values() if item.ok),
        "unsupported_candidates": [{"candidate_id": item.candidate_id, "reason": item.reason, "validation": item.validation} for item in harnesses.values() if not item.ok],
        "completed_supported_runs": completed_supported_runs,
        "unsupported_rows": unsupported_rows,
        "work_dir": str(run_root),
    }


def find_summary(rows: list[dict[str, Any]], budget: float) -> dict[str, Any]:
    return next(row for row in rows if float(row["wall_clock_budget_s"]) == float(budget))


def density_bucket(label: dict[str, Any]) -> str:
    rho = sbm.safe_div(int(label.get("total_mismatching_input_count", 0)), int(label.get("exact_domain_size", 0)))
    if rho == 0:
        return "rho=0"
    if rho <= 0.01:
        return "rho<=0.01"
    if rho <= 0.10:
        return "rho<=0.10"
    if rho <= 0.50:
        return "rho<=0.50"
    return "rho>0.50"


def choose_worker_count(requested: int) -> int:
    logical = os.cpu_count() or 1
    return max(1, min(int(requested), MAX_WORKERS_DEFAULT, logical))


def median_or_blank(values: Iterable[float | int]) -> float | str:
    items = [float(value) for value in values]
    return statistics.median(items) if items else ""


def fmt_rate(value: Any) -> str:
    if value == "":
        return ""
    return f"{float(value):.3f}"


def budget_label(value: float) -> str:
    return str(value).replace(".", "p")


def short_head(repo_root: Path) -> str:
    return git_output(repo_root, ["rev-parse", "--short", "HEAD"])


def basic_environment() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "clang_version": sbm.command_first_line([str(CLANG), "--version"]),
    }


def cpu_model() -> str:
    try:
        with Path("/proc/cpuinfo").open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha256(repo_root: Path, commit: str, rel: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{rel}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def git_output(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.strip()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
