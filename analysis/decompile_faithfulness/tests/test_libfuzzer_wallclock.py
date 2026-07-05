from __future__ import annotations

import ast
import json
import os
import stat
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from analysis.decompile_faithfulness import libfuzzer_wallclock as lw
from analysis.decompile_faithfulness import strong_baselines_and_mechanism as sbm


REPO_ROOT = Path(__file__).resolve().parents[3]


class LibFuzzerWallClockTest(unittest.TestCase):
    def test_module_does_not_import_or_call_final_scheduler(self) -> None:
        self.assertTrue(lw.final_method_guard(Path(lw.__file__))["ok"])
        tree = ast.parse(Path(lw.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, lw.FORBIDDEN_FINAL_METHOD_MODULES)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, lw.FORBIDDEN_FINAL_METHOD_MODULES)

    def test_phase1f_harness_semantics_are_reused(self) -> None:
        self.assertIs(lw.sbm.build_libfuzzer_harness, sbm.build_libfuzzer_harness)
        self.assertIs(lw.sbm.validate_libfuzzer_harness_semantics, sbm.validate_libfuzzer_harness_semantics)
        self.assertIs(lw.sbm.parse_fuzzer_log, sbm.parse_fuzzer_log)
        self.assertEqual(lw.sbm.RANDOM_SEEDS, sbm.RANDOM_SEEDS)

    def test_fixed_30_seed_list(self) -> None:
        self.assertEqual(len(sbm.RANDOM_SEEDS), 30)
        self.assertEqual(sbm.RANDOM_SEEDS[:3], [101, 202, 303])
        self.assertEqual(sbm.RANDOM_SEEDS[-3:], [2819, 2920, 3021])

    def test_wall_clock_timeout_enforcement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "slow_runner"
            script.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "time.sleep(2.0)\n",
                encoding="utf-8",
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            seed_dir = root / "seed"
            seed_dir.mkdir()
            log_path = root / "log.txt"
            result = lw.invoke_fuzzer_wallclock(script, seed_dir, log_path, 101, 0.05)
            self.assertTrue(result["timed_out"])
            self.assertLess(result["elapsed_wall_clock_s"], 1.0)

    def test_end_to_end_and_in_process_timing_are_separate(self) -> None:
        candidate = _candidate("c", "semantic_wrong")
        function = _function()
        label = {"label": "semantic_wrong", "exact_domain_size": 64, "total_mismatching_input_count": 1}
        row = lw.wallclock_result_row(
            candidate,
            function,
            label,
            {sbm.PRIMARY_SCOPE: ["c"]},
            101,
            0.1,
            [{"eval": 1, "elapsed_s": 0.002, "args": [1], "source_output": 1, "candidate_output": 0, "mismatch": True}],
            {"eval": 1, "elapsed_s": 0.002, "args": [1], "source_output": 1, "candidate_output": 0, "mismatch": True},
            {"confirmed": True, "method": "unit"},
            {"process_startup_time_s": 0.03, "elapsed_wall_clock_s": 0.08, "timed_out": False, "crash": True, "infrastructure_failure": False, "infrastructure_reason": "", "returncode": 77, "stderr_tail": ""},
            Path("out.log"),
        )
        self.assertEqual(row["process_startup_time_s"], 0.03)
        self.assertEqual(row["in_process_time_to_first_witness_s"], 0.002)
        self.assertEqual(row["end_to_end_time_to_first_witness_s"], 0.08)
        self.assertFalse(row["crash"], "semantic mismatch traps are findings, not crash failures")

    def test_completed_evaluation_and_coverage_accounting(self) -> None:
        candidate = _candidate("c", "semantic_wrong")
        function = _function()
        label = {"label": "semantic_wrong", "exact_domain_size": 64, "total_mismatching_input_count": 0}
        sequence = [
            {"eval": 1, "elapsed_s": 0.001, "args": [0], "source_output": 0, "candidate_output": 0, "mismatch": False},
            {"eval": 2, "elapsed_s": 0.002, "args": [0], "source_output": 0, "candidate_output": 0, "mismatch": False},
            {"eval": 3, "elapsed_s": 0.003, "args": [1], "source_output": 1, "candidate_output": 1, "mismatch": False},
        ]
        row = lw.wallclock_result_row(
            candidate,
            function,
            label,
            {sbm.PRIMARY_SCOPE: ["c"]},
            101,
            1.0,
            sequence,
            None,
            {"confirmed": False, "reason": "no_witness"},
            {"process_startup_time_s": 0.01, "elapsed_wall_clock_s": 1.01, "timed_out": True, "crash": False, "infrastructure_failure": False, "infrastructure_reason": "", "returncode": -9, "stderr_tail": ""},
            Path("out.log"),
        )
        self.assertEqual(row["completed_input_evaluations"], 3)
        self.assertEqual(row["unique_exact_domain_inputs"], 2)
        self.assertAlmostEqual(row["exact_domain_coverage_fraction"], 2 / 64)
        self.assertTrue(row["timeout"])

    def test_witness_confirmation_parser(self) -> None:
        parsed = lw.parse_confirmation_stdout("source:10\ncandidate:11\n")
        self.assertEqual(parsed["source_output"], 10)
        self.assertEqual(parsed["candidate_output"], 11)

    def test_no_mismatch_false_alarm_handling(self) -> None:
        candidate = _candidate("c", "no_mismatch_under_exact_holdout_domain")
        function = _function()
        label = {"label": "no_mismatch_under_exact_holdout_domain", "exact_domain_size": 64, "total_mismatching_input_count": 0}
        row = lw.wallclock_result_row(
            candidate,
            function,
            label,
            {sbm.NO_MISMATCH_SCOPE: ["c"]},
            101,
            1.0,
            [{"eval": 1, "elapsed_s": 0.001, "args": [1], "source_output": 1, "candidate_output": 0, "mismatch": True}],
            {"eval": 1, "elapsed_s": 0.001, "args": [1], "source_output": 1, "candidate_output": 0, "mismatch": True},
            {"confirmed": True, "method": "unit"},
            {"process_startup_time_s": 0.01, "elapsed_wall_clock_s": 0.1, "timed_out": False, "crash": True, "infrastructure_failure": False, "infrastructure_reason": "", "returncode": 77, "stderr_tail": ""},
            Path("out.log"),
        )
        self.assertTrue(row["no_mismatch_false_alarm"])

    def test_candidate_population_reconciliation(self) -> None:
        first_rows = sbm.normalize_first_witness_rows(sbm.read_csv(REPO_ROOT / "results/decompile_faithfulness/holdout_first_witness.csv"))
        functions = sbm.load_functions(REPO_ROOT)
        candidates = sbm.load_candidates(REPO_ROOT)
        population = sbm.build_population(first_rows, functions, candidates)
        lw.check_population(population)
        self.assertEqual(len(population[sbm.PRIMARY_SCOPE]), 37)
        self.assertEqual(len(population["natural_ghidra_no_mismatch"]), 16)

    def test_candidate_set_comparison(self) -> None:
        first_rows = [
            _first("a", detected=True),
            _first("b", detected=True),
            _first("c", detected=False),
        ]
        run_rows = [
            {"wall_clock_budget_s": 0.1, "candidate_id": "a", "witness_confirmed": True},
            {"wall_clock_budget_s": 0.1, "candidate_id": "b", "witness_confirmed": False},
            {"wall_clock_budget_s": 0.1, "candidate_id": "c", "witness_confirmed": True},
        ]
        rows = lw.candidate_set_comparisons(run_rows, first_rows, {sbm.PRIMARY_SCOPE: ["a", "b", "c"]})
        first = [row for row in rows if row["wall_clock_budget_s"] == 0.1][0]
        self.assertEqual(first["detected_by_both_count"], 1)
        self.assertEqual(first["detected_only_by_final_count"], 1)
        self.assertEqual(first["detected_only_by_libfuzzer_count"], 1)

    def test_table_and_figure_data_reconciliation(self) -> None:
        summary = [
            _summary(0.1, sbm.PRIMARY_SCOPE, 0.2),
            _summary(0.1, sbm.LOW_DENSITY_SCOPE, 0.1),
            _summary(0.1, sbm.NON_FIXTURE_SCOPE, 0.1),
        ]
        detection = lw.detection_curve_rows(summary)
        time_rows = lw.time_to_witness_rows(summary)
        self.assertEqual(len(detection), 3)
        self.assertEqual(len(time_rows), 3)
        self.assertTrue(all(row["frozen_final_detection_at_b8"] == 33 / 37 for row in detection))

    def test_seal_and_method_integrity_preflight(self) -> None:
        preflight = lw.run_preflight(REPO_ROOT, "unit", "unit", 4)
        self.assertTrue(preflight["ok"])
        self.assertTrue(preflight["holdout_manifest_sha256_matches_expected"])
        self.assertTrue(preflight["sealed_artifact_checks"]["all_ok"])
        self.assertTrue(preflight["method_hash_checks"]["all_ok"])
        self.assertTrue(preflight["phase1f_evaluation_count_artifact_checks"]["all_ok"])

    def test_primary_rows_use_no_source_literal_dictionary(self) -> None:
        candidate = _candidate("c", "semantic_wrong")
        function = _function()
        label = {"label": "semantic_wrong", "exact_domain_size": 64, "total_mismatching_input_count": 1}
        row = lw.wallclock_result_row(
            candidate,
            function,
            label,
            {sbm.PRIMARY_SCOPE: ["c"]},
            101,
            0.1,
            [],
            None,
            {"confirmed": False, "reason": "none"},
            {"process_startup_time_s": 0.01, "elapsed_wall_clock_s": 0.1, "timed_out": True, "crash": False, "infrastructure_failure": False, "infrastructure_reason": "", "returncode": -9, "stderr_tail": ""},
            Path("out.log"),
        )
        self.assertFalse(row["source_literal_dictionary_used"])
        self.assertFalse(row["exact_mismatch_witness_provided"])

    def test_generated_phase1g_outputs_reconcile(self) -> None:
        runs_path = REPO_ROOT / "results/decompile_faithfulness/libfuzzer_wallclock_runs.jsonl"
        summary_path = REPO_ROOT / "results/decompile_faithfulness/libfuzzer_wallclock_summary.csv"
        if not runs_path.exists() or not summary_path.exists():
            self.skipTest("Phase 1g generated outputs are not present")
        runs = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(runs), 71 * 30 * 3)
        self.assertEqual(Counter(row["wall_clock_budget_s"] for row in runs), {0.1: 2130, 1.0: 2130, 5.0: 2130})
        self.assertEqual(len({row["seed"] for row in runs}), 30)
        self.assertEqual(len({row["candidate_id"] for row in runs}), 71)
        self.assertEqual(len({row["candidate_id"] for row in runs if row["supported_by_libfuzzer_pipeline"]}), 68)
        self.assertTrue(all(row["source_literal_dictionary_used"] is False for row in runs))
        self.assertTrue(all(row["exact_mismatch_witness_provided"] is False for row in runs))
        self.assertEqual(sum(1 for row in runs if row["no_mismatch_false_alarm"]), 0)
        summary = list(_csv(summary_path))
        primary = [
            row for row in summary
            if row["population"] == sbm.PRIMARY_SCOPE
        ]
        self.assertEqual(len(primary), 3)
        self.assertTrue(all(row["mean_detection"] == "1.0" for row in primary))
        no_mismatch = [
            row for row in summary
            if row["population"] == sbm.NO_MISMATCH_SCOPE
        ]
        self.assertTrue(all(row["no_mismatch_false_alarms"] == "0" for row in no_mismatch))


def _candidate(candidate_id: str, label: str) -> sbm.CandidateInfo:
    return sbm.CandidateInfo(
        candidate_id=candidate_id,
        function_id="f",
        project="p",
        candidate_stratum="controlled_stress",
        candidate_class="controlled",
        label=label,
        compile_status="compile_ready",
        execution_status="ok",
        mutation_family="return_value_perturbation",
        source_path="candidate.c",
    )


def _function() -> sbm.FunctionInfo:
    return sbm.FunctionInfo(
        function_id="f",
        project="p",
        source_file="f.c",
        function_name="f",
        signature="int f(int x)",
        domain_specs=({"type": "int", "values": list(range(64))},),
        domain_size=64,
        source_literal_count=0,
        source_path="source.c",
    )


def _first(candidate_id: str, detected: bool) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "policy": sbm.FINAL_POLICY,
        "budget": 8,
        "random_seed": None,
        "detected_in_domain": detected,
    }


def _summary(budget: float, population: str, detection: float) -> dict[str, object]:
    return {
        "wall_clock_budget_s": budget,
        "population": population,
        "mean_detection": detection,
        "median_detection": detection,
        "p2_5_detection": detection,
        "p97_5_detection": detection,
        "median_completed_evaluations": 1,
        "median_unique_domain_coverage": 1,
        "median_end_to_end_time_to_witness_s": 0.1,
        "median_in_process_time_to_witness_s": 0.01,
    }


def _csv(path: Path):
    import csv

    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


if __name__ == "__main__":
    unittest.main()
