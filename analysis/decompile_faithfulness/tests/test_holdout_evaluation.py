from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import holdout_evaluation as he


REPO_ROOT = Path(__file__).resolve().parents[3]


class HoldoutEvaluationTest(unittest.TestCase):
    def test_exact_domain_membership(self) -> None:
        function = _function(
            domain_specs=(
                {"type": "int", "values": [-1, 0, 1]},
                {"type": "unsigned char", "values": [0, 1, 127]},
            ),
        )
        self.assertTrue(he.exact_domain_contains(function, (0, 127)))
        self.assertFalse(he.exact_domain_contains(function, (2, 127)))
        self.assertFalse(he.exact_domain_contains(function, (0, 128)))
        self.assertFalse(he.exact_domain_contains(function, (0,)))

    def test_density_bucket_construction(self) -> None:
        self.assertEqual(he.density_bucket_for_label({"total_mismatching_input_count": 0, "exact_domain_size": 64}), "rho=0")
        self.assertEqual(he.density_bucket_for_label({"total_mismatching_input_count": 1, "exact_domain_size": 128}), "0<rho<=0.01")
        self.assertEqual(he.density_bucket_for_label({"total_mismatching_input_count": 4, "exact_domain_size": 64}), "0.01<rho<=0.10")
        self.assertEqual(he.density_bucket_for_label({"total_mismatching_input_count": 20, "exact_domain_size": 64}), "0.10<rho<=0.50")
        self.assertEqual(he.density_bucket_for_label({"total_mismatching_input_count": 64, "exact_domain_size": 64}), "0.50<rho<=1.00")

    def test_generic_type_boundary_ordering(self) -> None:
        function = _function(
            signature="int f(int x, unsigned char c)",
            domain_specs=(
                {"type": "int", "values": list(range(-32, 32))},
                {"type": "unsigned char", "values": list(range(0, 128))},
            ),
        )
        entry = {
            "signature": function.signature,
            "fixtures": [{"args": [3, 65], "expected": 0}],
        }
        probes = he.generic_type_boundary_order(function, entry)
        self.assertEqual(probes[0].args, (-32, 65))
        self.assertEqual(probes[1].args, (-1, 65))
        self.assertIn((3, 127), [probe.args for probe in probes])
        self.assertTrue(all(probe.generic_type_boundary_derived for probe in probes))

    def test_fixed_random_seeds(self) -> None:
        self.assertEqual(len(he.RANDOM_SEEDS), 30)
        self.assertEqual(len(set(he.RANDOM_SEEDS)), 30)
        self.assertEqual(he.RANDOM_SEEDS[:3], [101, 202, 303])

    def test_budget_prefix_consistency(self) -> None:
        function = _function()
        entry = {
            "case_id": function.function_id,
            "function_name": function.function_name,
            "signature": function.signature,
            "fixtures": [{"args": [0], "expected": 0}, {"args": [2], "expected": 2}],
        }
        case = he.fixtures.FunctionCase(
            function.function_id,
            function.function_name,
            function.source,
            tuple(he.fixtures.FunctionTest(tuple(row["args"]), int(row["expected"])) for row in entry["fixtures"]),
        )
        probes = he.build_policy_order("generic_type_boundaries", entry, case, function, seed=None)
        self.assertEqual([probe.args for probe in probes[:2]], [probe.args for probe in probes[:4]][:2])

    def test_primary_denominator_construction(self) -> None:
        candidates = [
            _candidate("wrong-pass", "semantic_wrong"),
            _candidate("wrong-fail", "semantic_wrong"),
            _candidate("ctrl-ok", "no_mismatch_under_exact_holdout_domain"),
            _candidate("nat-ok", "no_mismatch_under_exact_holdout_domain", stratum="natural_ghidra"),
        ]
        labels = {
            "wrong-pass": {"candidate_id": "wrong-pass", "total_mismatching_input_count": 1, "exact_domain_size": 64},
            "wrong-fail": {"candidate_id": "wrong-fail", "total_mismatching_input_count": 1, "exact_domain_size": 64},
            "ctrl-ok": {"candidate_id": "ctrl-ok", "total_mismatching_input_count": 0, "exact_domain_size": 64},
            "nat-ok": {"candidate_id": "nat-ok", "total_mismatching_input_count": 0, "exact_domain_size": 64},
        }
        replay = [
            {"candidate_id": "wrong-pass", "fixture_pass": True},
            {"candidate_id": "wrong-fail", "fixture_pass": False},
            {"candidate_id": "ctrl-ok", "fixture_pass": True},
        ]
        population = he.build_population(candidates, labels, replay, {"f": _function()})
        self.assertEqual(population["sets"]["primary_fixture_passing_wrong"], ["wrong-pass"])
        self.assertEqual(population["sets"]["low_density_fixture_passing_wrong"], ["wrong-pass"])
        self.assertEqual(set(population["sets"]["no_mismatch_comparison"]), {"ctrl-ok", "nat-ok"})

    def test_fixture_pass_reconstruction(self) -> None:
        function = _function(source="int f(int x) { return x; }\n")
        candidate = _candidate("same", "no_mismatch_under_exact_holdout_domain")
        with tempfile.TemporaryDirectory() as tmp:
            candidate_path = Path(tmp) / "candidate.c"
            candidate_path.write_text("int f(int x) { return x; }\n", encoding="utf-8")
            candidate = he.CandidateRecord(
                candidate_id=candidate.candidate_id,
                function_id=candidate.function_id,
                project=candidate.project,
                candidate_stratum=candidate.candidate_stratum,
                candidate_class=candidate.candidate_class,
                label=candidate.label,
                compile_status=candidate.compile_status,
                execution_status=candidate.execution_status,
                mutation_family=candidate.mutation_family,
                source_path=candidate_path,
                total_mismatching_input_count=0,
                exact_domain_size=3,
            )
            rows = he.replay_fixtures(
                REPO_ROOT,
                {"f": function},
                [candidate],
                {"f": [
                    {"args": [0], "source_output": 0, "rank": 1},
                    {"args": [1], "source_output": 1, "rank": 2},
                    {"args": [2], "source_output": 2, "rank": 3},
                    {"args": [3], "source_output": 3, "rank": 4},
                ]},
                Path(tmp) / "replay",
            )
        self.assertTrue(rows[0]["fixture_pass"])
        self.assertEqual(rows[0]["fixture_agreement_count"], 4)

    def test_seal_preflight_detects_artifact_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sealed.txt").write_text("sealed\n", encoding="utf-8")
            manifest = {
                "artifact_hashes": {
                    "sealed.txt": {"type": "file", "sha256": he.sha256_path(root / "sealed.txt")}
                }
            }
            (root / "sealed.txt").write_text("changed\n", encoding="utf-8")
            check = he.verify_sealed_artifacts(root, manifest)
        self.assertFalse(check["all_ok"])

    def test_method_hash_integrity(self) -> None:
        manifest = json.loads((REPO_ROOT / "analysis/decompile_faithfulness/holdout_sealed_manifest_v2.json").read_text(encoding="utf-8"))
        check = he.verify_method_hashes(REPO_ROOT, manifest)
        self.assertTrue(check["all_ok"])
        self.assertGreaterEqual(check["checked_count"], 1)

    def test_no_mismatch_unexpected_row_adjudication(self) -> None:
        candidate = _candidate("c", "no_mismatch_under_exact_holdout_domain")
        function = _function()
        row = he.unexpected_mismatch_row(
            candidate,
            function,
            he.FINAL_POLICY,
            None,
            8,
            1,
            he.PolicyProbe((0,), "fixture_neighbor"),
            0,
            1,
            True,
        )
        self.assertEqual(row["adjudication"], "unexpected_in_domain_mismatch")


def _function(
    *,
    signature: str = "int f(int x)",
    source: str = "int f(int x) { return x; }\n",
    domain_specs: tuple[dict[str, object], ...] = ({"type": "int", "values": [-1, 0, 1]},),
) -> he.HoldoutFunction:
    domain = tuple(tuple(int(value) for value in values) for values in __import__("itertools").product(*[spec["values"] for spec in domain_specs]))
    return he.HoldoutFunction(
        function_id="f",
        project="p",
        source_file="f.c",
        function_name="f",
        signature=signature,
        domain_specs=domain_specs,
        domain=domain,
        domain_size=len(domain),
        source=source,
        source_literal_count=0,
    )


def _candidate(
    candidate_id: str,
    label: str,
    *,
    stratum: str = "controlled_stress",
) -> he.CandidateRecord:
    return he.CandidateRecord(
        candidate_id=candidate_id,
        function_id="f",
        project="p",
        candidate_stratum=stratum,
        candidate_class="controlled_stress_candidate" if stratum == "controlled_stress" else "natural_ghidra_output",
        label=label,
        compile_status="compile_ready",
        execution_status="exact_domain_execution_complete",
        mutation_family="fixture_overfit_construction",
        source_path=Path("candidate.c"),
        total_mismatching_input_count=1 if label == "semantic_wrong" else 0,
        exact_domain_size=64,
    )


if __name__ == "__main__":
    unittest.main()
