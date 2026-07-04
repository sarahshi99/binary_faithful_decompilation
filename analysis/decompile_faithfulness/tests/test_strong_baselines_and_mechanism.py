from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import strong_baselines_and_mechanism as sbm


REPO_ROOT = Path(__file__).resolve().parents[3]


class StrongBaselinesAndMechanismTest(unittest.TestCase):
    def test_module_does_not_import_final_scheduler(self) -> None:
        tree = ast.parse(Path(sbm.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "analysis.decompile_faithfulness.run_phase11_input_ordering",
            "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
        }
        forbidden_calls = {
            "build_ordered_inputs",
            "source_literal_char_inputs",
            "fixture_neighbor_inputs",
            "interleave_inputs",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls)
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)

    def test_paired_set_computation(self) -> None:
        rows = [
            _first("a", sbm.FINAL_POLICY, 8, True),
            _first("b", sbm.FINAL_POLICY, 8, True),
            _first("c", sbm.FINAL_POLICY, 8, False),
            _first("d", sbm.FINAL_POLICY, 8, False),
            _first("a", sbm.GENERIC_BOUNDARY_POLICY, 8, True),
            _first("b", sbm.GENERIC_BOUNDARY_POLICY, 8, False),
            _first("c", sbm.GENERIC_BOUNDARY_POLICY, 8, True),
            _first("d", sbm.GENERIC_BOUNDARY_POLICY, 8, False),
        ]
        final = sbm.detected_set(rows, sbm.FINAL_POLICY, 8, None, ["a", "b", "c", "d"])
        other, rule = sbm.comparator_detected_set(rows, sbm.GENERIC_BOUNDARY_POLICY, 8, ["a", "b", "c", "d"])
        record = sbm.paired_row(
            sbm.PRIMARY_SCOPE,
            sbm.GENERIC_BOUNDARY_POLICY,
            8,
            ["a", "b", "c", "d"],
            final,
            other,
            rule,
            {"fa": _function("p"), "fb": _function("p"), "fc": _function("q"), "fd": _function("q")},
            rows,
        )
        self.assertEqual(record["detected_by_both_count"], 1)
        self.assertEqual(record["detected_only_by_final_count"], 1)
        self.assertEqual(record["detected_only_by_comparator_count"], 1)
        self.assertEqual(record["detected_by_neither_count"], 1)
        self.assertEqual(record["mcnemar_b10_final_only"], 1)

    def test_selected_final_miss_reconciliation(self) -> None:
        rows = [
            _first("a", sbm.FINAL_POLICY, 8, True),
            _first("b", sbm.FINAL_POLICY, 8, False),
            _first("a", sbm.FINAL_POLICY, 32, True),
            _first("b", sbm.FINAL_POLICY, 32, False),
            _first("a", sbm.GENERIC_BOUNDARY_POLICY, 8, False),
            _first("b", sbm.GENERIC_BOUNDARY_POLICY, 8, True),
            _first("a", sbm.LITERAL_FIRST_POLICY, 8, True),
            _first("b", sbm.LITERAL_FIRST_POLICY, 8, False),
            _first("a", sbm.FIXTURE_NEIGHBOR_POLICY, 8, False),
            _first("b", sbm.FIXTURE_NEIGHBOR_POLICY, 8, False),
        ]
        selected = sbm.selected_mechanism_lists(rows, {sbm.PRIMARY_SCOPE: ["a", "b"]})
        self.assertEqual(selected["final_miss_b8"]["ids"], ["b"])
        self.assertEqual(selected["final_miss_b32"]["ids"], ["b"])
        self.assertEqual(selected["final_only_vs_generic_type_boundaries"]["ids"], ["a"])
        self.assertEqual(selected["generic_type_boundaries_only_vs_final"]["ids"], ["b"])

    def test_out_of_domain_denominator_reconciliation(self) -> None:
        summary: dict[tuple[str, int, str], dict[str, object]] = {}
        row = {
            "policy": sbm.FINAL_POLICY,
            "budget": 8,
            "candidate_id": "c",
            "input_tuple": (43,),
            "in_exact_domain": False,
            "mismatch": True,
            "source_execution_status": "ok",
            "candidate_execution_status": "ok",
        }
        sbm.update_ood(summary, row, sbm.PRIMARY_SCOPE)
        rows = sbm.out_of_domain_summary_rows(
            {"out_of_domain": summary, "final_b8_ood_confirmations": []},
            {sbm.PRIMARY_SCOPE: ["c"], sbm.LOW_DENSITY_SCOPE: [], sbm.NO_MISMATCH_SCOPE: []},
        )
        self.assertEqual(rows[0]["candidate_denominator"], 1)
        self.assertEqual(rows[0]["out_of_domain_probe_count"], 1)
        self.assertEqual(rows[0]["distinct_out_of_domain_witness_count"], 1)

    def test_klee_domain_constraints_are_exact_domain_ranges(self) -> None:
        fn = _function("p", domain_specs=({"type": "int", "values": [-2, -1, 0, 1]},))
        preview = sbm.klee_domain_constraint_preview(fn)
        self.assertIn("arg0 >= -2", preview)
        self.assertIn("arg0 <= 1", preview)
        self.assertNotIn("arg0 <= 2", preview)

    def test_klee_witness_confirmation_uses_label_mismatch_set(self) -> None:
        label = {"stored_mismatches": [{"args": [1, 2]}, {"args": [3, 4]}]}
        self.assertTrue(sbm.confirm_witness_against_exact_label(label, [3, 4]))
        self.assertFalse(sbm.confirm_witness_against_exact_label(label, [4, 3]))

    def test_libfuzzer_byte_to_domain_mapping_and_seed_encoding(self) -> None:
        specs = (
            {"type": "int", "values": [-1, 0, 1]},
            {"type": "unsigned char", "values": [0, 127]},
        )
        self.assertEqual(sbm.bytes_to_domain_tuple(bytes([0, 0, 1, 0]), specs), (-1, 127))
        encoded = sbm.encode_domain_tuple(specs, [1, 127])
        self.assertEqual(sbm.bytes_to_domain_tuple(encoded, specs), (1, 127))

    def test_libfuzzer_primary_rows_use_no_source_literal_dictionary(self) -> None:
        population = {
            sbm.PRIMARY_SCOPE: ["c"],
            sbm.LOW_DENSITY_SCOPE: ["c"],
            sbm.NON_FIXTURE_SCOPE: ["c"],
            sbm.NO_MISMATCH_SCOPE: [],
        }
        candidates = {
            "c": sbm.CandidateInfo(
                candidate_id="c",
                function_id="f",
                project="p",
                candidate_stratum="controlled_stress",
                candidate_class="controlled_stress_candidate",
                label="semantic_wrong",
                compile_status="compile_ready",
                execution_status="exact_domain_execution_complete",
                mutation_family="return_value_perturbation",
                source_path="candidate.c",
            )
        }
        run_rows, summary_rows = sbm.libfuzzer_blocker_rows(population, candidates)
        self.assertTrue(run_rows)
        self.assertTrue(summary_rows)
        self.assertTrue(all(row["source_literal_dictionary_used"] is False for row in run_rows))
        self.assertIn(sbm.NON_FIXTURE_SCOPE, {row["population"] for row in summary_rows})

    def test_no_mismatch_false_alarm_handling(self) -> None:
        candidate = sbm.CandidateInfo("c", "f", "p", "controlled_stress", "controlled", "no_mismatch_under_exact_holdout_domain", "compile_ready", "ok", "noop", "")
        fn = _function("p")
        row = sbm.libfuzzer_result_row(
            candidate,
            fn,
            {"label": "no_mismatch_under_exact_holdout_domain"},
            "evaluation_count",
            101,
            8,
            [{"eval": 1, "elapsed_s": 0.0, "args": [0], "source_output": 0, "candidate_output": 1, "mismatch": True}],
            {"eval": 1, "elapsed_s": 0.0, "args": [0], "mismatch": True},
            {"returncode": 77, "timed_out": False, "elapsed_wall_clock_s": 0.01, "stderr_tail": ""},
        )
        self.assertTrue(row["no_mismatch_false_alarm"])

    def test_generated_phase1f_tables_reconcile(self) -> None:
        paired = list(_csv(REPO_ROOT / "results/decompile_faithfulness/holdout_paired_policy_analysis.csv"))
        final_b8 = [
            row for row in paired
            if row["scope"] == sbm.PRIMARY_SCOPE
            and row["comparator_policy"] == sbm.GENERIC_BOUNDARY_POLICY
            and row["budget"] == "8"
        ][0]
        self.assertEqual(int(final_b8["denominator"]), 37)
        self.assertEqual(int(final_b8["detected_only_by_final_count"]), 2)
        self.assertEqual(int(final_b8["detected_only_by_comparator_count"]), 1)
        klee = list(_csv(REPO_ROOT / "results/decompile_faithfulness/klee_summary.csv"))
        self.assertIn(sbm.NON_FIXTURE_SCOPE, {row["population"] for row in klee})
        lib = list(_csv(REPO_ROOT / "results/decompile_faithfulness/libfuzzer_summary.csv"))
        lib_b8 = [
            row for row in lib
            if row["mode"] == "evaluation_count"
            and row["budget_or_time_limit"] == "8"
            and row["population"] == sbm.PRIMARY_SCOPE
        ][0]
        self.assertEqual(lib_b8["baseline_status"], "completed")
        self.assertEqual(int(lib_b8["no_mismatch_false_alarms"]), 0)
        wall_clock = [
            row for row in lib
            if row["mode"] == "wall_clock"
            and row["population"] == sbm.PRIMARY_SCOPE
        ]
        self.assertTrue(wall_clock)
        self.assertTrue(all(row["baseline_status"] == "not_run_blocked" for row in wall_clock))

    def test_interpretation_gate_reflects_literal_first_low_budget_dominance(self) -> None:
        first_rows = sbm.normalize_first_witness_rows(
            sbm.read_csv(REPO_ROOT / "results/decompile_faithfulness/holdout_first_witness.csv")
        )
        functions = sbm.load_functions(REPO_ROOT)
        candidates = sbm.load_candidates(REPO_ROOT)
        population = sbm.build_population(first_rows, functions, candidates)
        lib = list(_csv(REPO_ROOT / "results/decompile_faithfulness/libfuzzer_summary.csv"))
        klee = list(_csv(REPO_ROOT / "results/decompile_faithfulness/klee_summary.csv"))
        gate = sbm.interpretation_gates(
            first_rows=first_rows,
            population=population,
            libfuzzer_summary=lib,
            klee_summary=klee,
        )
        self.assertFalse(gate["strong_low_budget_execution_claim_supported"])
        self.assertFalse(gate["final_on_detection_evaluation_pareto_frontier_b_le8"])
        self.assertEqual(gate["libfuzzer_at_8_status"], "completed")
        self.assertIn("literal-first", gate["claim_consequence"])


def _first(candidate_id: str, policy: str, budget: int, detected: bool) -> dict[str, object]:
    suffix = candidate_id[-1]
    return {
        "candidate_id": candidate_id,
        "function_id": f"f{suffix}",
        "project": "p" if suffix in {"a", "b"} else "q",
        "candidate_stratum": "controlled_stress",
        "label": "semantic_wrong",
        "mutation_family": "return_value_perturbation",
        "policy": policy,
        "budget": budget,
        "random_seed": None,
        "first_in_domain_witness_rank": 1 if detected else None,
        "detected_in_domain": detected,
        "mismatch_density": 0.1,
        "in_primary_fixture_passing_wrong": True,
        "in_low_density_fixture_passing_wrong": True,
        "in_all_controlled_semantic_wrong": True,
        "in_no_mismatch_comparison": False,
    }


def _function(
    project: str,
    *,
    domain_specs: tuple[dict[str, object], ...] = ({"type": "int", "values": [-1, 0, 1]},),
) -> sbm.FunctionInfo:
    return sbm.FunctionInfo(
        function_id=f"f{project[-1] if project else 'x'}",
        project=project,
        source_file="f.c",
        function_name="f",
        signature="int f(int x)",
        domain_specs=domain_specs,
        domain_size=3,
        source_literal_count=0,
        source_path="",
    )


def _csv(path: Path):
    import csv

    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


if __name__ == "__main__":
    unittest.main()
