from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase17_operator_char_policy as phase17


class Phase17OperatorCharPolicyTest(unittest.TestCase):
    def test_metric_delta_tracks_auc_detection_misses_and_cost(self) -> None:
        delta = phase17.metric_delta(
            {
                "mismatch_auc": 1.0,
                "wrong_detection_rate": 0.98,
                "missed_wrong_count": 1,
                "avg_actual_inputs_per_candidate": 8.0,
            },
            {
                "mismatch_auc": 0.99,
                "wrong_detection_rate": 0.95,
                "missed_wrong_count": 3,
                "avg_actual_inputs_per_candidate": 7.5,
            },
        )
        self.assertAlmostEqual(delta["mismatch_auc_delta"], 0.01)
        self.assertAlmostEqual(delta["wrong_detection_rate_delta"], 0.03)
        self.assertEqual(delta["missed_wrong_count_delta"], -2.0)
        self.assertAlmostEqual(delta["avg_actual_inputs_delta"], 0.5)

    def test_large_risk_family_gate_ignores_tiny_rows(self) -> None:
        rows = [
            {"risk_family": "small", "paired_case_count": 2, "wrong_detection_rate": 0.0, "auc": 0.0},
            {"risk_family": "large", "paired_case_count": 3, "wrong_detection_rate": 0.95, "auc": 0.91},
        ]
        self.assertTrue(phase17.large_risk_family_gate(rows, "wrong_detection_rate", 0.90))
        self.assertTrue(phase17.large_risk_family_gate(rows, "auc", 0.90))
        rows[1]["wrong_detection_rate"] = 0.89
        self.assertFalse(phase17.large_risk_family_gate(rows, "wrong_detection_rate", 0.90))

    def test_require_risk_row(self) -> None:
        row = {"risk_family": "char_boundary", "paired_case_count": 3}
        self.assertIs(phase17.require_risk_row([row], "char_boundary"), row)
        with self.assertRaises(KeyError):
            phase17.require_risk_row([row], "multi_arg")

    def test_phase17_verdict(self) -> None:
        self.assertEqual(
            phase17.phase17_verdict({"a": True, "b": True}),
            "pass-phase17-operator-char-policy",
        )
        self.assertEqual(
            phase17.phase17_verdict({"a": True, "b": False}),
            "partial-phase17-operator-char-policy",
        )
        self.assertEqual(
            phase17.phase17_verdict({"a": False, "b": False}),
            "fail-phase17-operator-char-policy",
        )


if __name__ == "__main__":
    unittest.main()
