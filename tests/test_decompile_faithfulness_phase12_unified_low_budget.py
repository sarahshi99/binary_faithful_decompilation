from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase12_unified_low_budget_eval as phase12


class Phase12UnifiedLowBudgetTest(unittest.TestCase):
    def test_metric_delta(self) -> None:
        delta = phase12.metric_delta(
            {
                "mismatch_auc": 0.99,
                "wrong_detection_rate": 0.97,
                "avg_actual_inputs_per_candidate": 7.0,
            },
            {
                "mismatch_auc": 0.95,
                "wrong_detection_rate": 0.92,
                "avg_actual_inputs_per_candidate": 6.5,
            },
        )
        self.assertAlmostEqual(delta["mismatch_auc_delta"], 0.04)
        self.assertAlmostEqual(delta["wrong_detection_rate_delta"], 0.05)
        self.assertAlmostEqual(delta["avg_actual_inputs_delta"], 0.5)

    def test_phase12_verdict(self) -> None:
        self.assertEqual(
            phase12.phase12_verdict({"a": True, "b": True}),
            "pass-unified-budget8-low-budget-eval",
        )
        self.assertEqual(
            phase12.phase12_verdict({"a": True, "b": False}),
            "partial-unified-low-budget-eval",
        )
        self.assertEqual(
            phase12.phase12_verdict({"a": False, "b": False}),
            "fail-unified-low-budget-eval",
        )


if __name__ == "__main__":
    unittest.main()
