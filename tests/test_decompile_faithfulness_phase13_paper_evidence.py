from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase13_paper_evidence_synthesis as phase13


class Phase13PaperEvidenceTest(unittest.TestCase):
    def test_phase13_verdict_requires_phase12_pass_and_claims(self) -> None:
        self.assertEqual(
            phase13.phase13_verdict(
                {"verdict": "pass-unified-budget8-low-budget-eval"},
                {"supported": ["claim"], "unsupported": []},
            ),
            "paper-evidence-ready-for-method-table",
        )
        self.assertEqual(
            phase13.phase13_verdict(
                {"verdict": "partial-unified-low-budget-eval"},
                {"supported": ["claim"], "unsupported": []},
            ),
            "paper-evidence-needs-more-experiments",
        )

    def test_claims_disallow_v3_margin_when_strong_baseline_erases_it(self) -> None:
        claims = phase13.build_claims(
            {"verdict": "strong-baseline-erases-v3-extra-margin"},
            {"verdict": "pass-unified-budget8-low-budget-eval"},
        )
        self.assertTrue(any("Budget-8 targeted dynamic re-execution" in claim for claim in claims["supported"]))
        self.assertTrue(any("v3 scoring components" in claim for claim in claims["unsupported"]))

    def test_main_table_row_contains_budget8_metrics(self) -> None:
        phase8 = {"point_estimates": [{"dataset_id": "toy", "v3_minus_strong_best": 0.0}]}
        phase10 = {"datasets": {"toy": {"budget_metrics": {"8": {"mismatch_auc": 0.9}}}}}
        phase12 = {
            "datasets": {
                "toy": {
                    "budget_metrics": {
                        "8": {
                            "candidate_count": 10,
                            "paired_case_count": 5,
                            "fixture_auc": 0.5,
                            "static_auc": 0.7,
                            "mismatch_auc": 0.99,
                            "wrong_detection_rate": 0.95,
                            "avg_actual_inputs_per_candidate": 8.0,
                            "missed_wrong_count": 1,
                        }
                    }
                }
            }
        }
        rows = phase13.build_main_table_rows(phase8, phase10, phase12)
        self.assertEqual(rows[0]["dataset_id"], "toy")
        self.assertEqual(rows[0]["phase10_original_order_auc"], 0.9)
        self.assertEqual(rows[0]["phase12_unified_budget8_auc"], 0.99)


if __name__ == "__main__":
    unittest.main()
