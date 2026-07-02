from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase7_public_benchmark_eval as phase7


class Phase7PublicBenchmarkEvalTest(unittest.TestCase):
    def test_build_phase7_candidates_retains_phase6_roles_with_phase7_ids(self) -> None:
        case = fixtures.FunctionCase(
            case_id="toy",
            function_name="toy",
            function_source="int toy(int x) {\n    return x + 1;\n}\n",
            tests=(fixtures.FunctionTest((1,), 2), fixtures.FunctionTest((2,), 3)),
        )
        entry = {
            "signature": "int toy(int x)",
            "function_name": "toy",
            "fixtures": [
                {"args": [1], "expected": 2},
                {"args": [2], "expected": 3},
            ],
        }
        candidates = phase7.build_phase7_candidates(
            case=case,
            entry=entry,
            opt_level="O0",
            assembly_context_path="analysis_outputs/toy.objdump.txt",
        )
        self.assertTrue(all(candidate.candidate_id.startswith("phase7_") for candidate in candidates))
        self.assertIn("behavior_preserving_original", {candidate.expected_role for candidate in candidates})
        self.assertIn("fixture_passing_semantic_drift", {candidate.expected_role for candidate in candidates})

    def test_phase7_verdict_requires_all_main_gates(self) -> None:
        summary = {
            "gate": {
                "source_function_scale_gate": True,
                "compile_pass_scale_gate": True,
                "paired_function_gate": True,
                "v3_beats_fixture_gate": True,
                "v3_beats_static_gate": True,
                "sota_delta_gate": True,
                "behavior_preserving_fp_gate": True,
                "fixture_collapse_gate": True,
                "risk_breakdown_gate": True,
            }
        }
        self.assertEqual(
            phase7.phase7_verdict(summary),
            "pass-phase7-public-benchmark-main-evidence",
        )
        summary["gate"]["sota_delta_gate"] = False
        self.assertEqual(
            phase7.phase7_verdict(summary),
            "method-negative-public-benchmark",
        )

    def test_gate_decision_keeps_public_row_below_external_sota_claim(self) -> None:
        summary = {
            "verdict": "pass-phase7-public-benchmark-main-evidence",
            "baseline_auc": {"v3_trace_total": 0.9},
            "best_non_oracle_baseline_auc": 0.8,
            "sota_delta_vs_best_baseline": 0.1,
            "external_sota_claim_ready": False,
            "gate": {"source_function_scale_gate": True},
        }
        gate = phase7.build_gate_decision(summary)
        self.assertEqual(gate["decision"], "ready-for-phase7d-second-decompiler-or-llm-baseline")
        self.assertIn("cannot claim external-paper SOTA", gate["claim_boundary"])
        self.assertIn("Phase 7D/7E", gate["next_step"])

    def test_gate_decision_reports_negative_delta_as_revise_method(self) -> None:
        summary = {
            "verdict": "method-negative-public-benchmark",
            "baseline_auc": {"v3_trace_total": 1.0},
            "best_non_oracle_baseline_auc": 0.97,
            "sota_delta_vs_best_baseline": 0.03,
            "external_sota_claim_ready": False,
            "gate": {"sota_delta_gate": False},
        }
        gate = phase7.build_gate_decision(summary)
        self.assertEqual(gate["decision"], "revise-method-before-sota-claim")
        self.assertIn("below the CCF-A/SOTA gate", gate["claim_boundary"])
        self.assertIn("static-hard", gate["next_step"])

    def test_write_markdown_includes_claim_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.md"
            phase7.write_result_markdown(
                path,
                {
                    "verdict": "pass-phase7-public-benchmark-main-evidence",
                    "benchmark": "CodeFuse-DeBench",
                    "source_function_count": 56,
                    "candidate_count": 560,
                    "compile_pass_count": 560,
                    "paired_case_count": 56,
                    "label_counts": {"faithful": 112, "plausible_wrong": 448},
                    "fixture_passing_wrong_count": 100,
                    "baseline_auc": {
                        "fixture_only": 0.5,
                        "static_structured_proxy": 0.8,
                        "v3_trace_total": 0.9,
                    },
                    "sota_delta_vs_best_baseline": 0.1,
                    "v3_behavior_preserving_false_positive_rate": 0.0,
                    "external_sota_claim_ready": False,
                    "external_sota_claim_blocker": "needs baselines",
                    "records_path": "analysis_outputs/records.jsonl",
                    "gate": {"source_function_scale_gate": True},
                    "by_risk_family": {
                        "branch": {
                            "candidate_count": 10,
                            "paired_case_count": 5,
                            "fixture_only_auc": 0.5,
                            "static_structured_auc": 0.7,
                            "v3_trace_total_auc": 0.9,
                        }
                    },
                    "by_mutation_type": {},
                    "failure_taxonomy": {},
                },
            )
            self.assertIn("External-paper SOTA claim ready", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
