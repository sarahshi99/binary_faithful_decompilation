from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import analyze_phase5_result_analysis as analysis


class Phase5ResultAnalysisTest(unittest.TestCase):
    def test_verdict_separates_scale_from_sota_delta(self) -> None:
        summary = {
            "missing_record_paths": [],
            "phase5_pass_gates": {
                "scale_gate": True,
                "auc_gate": True,
                "sota_delta_gate": False,
                "fixture_collapse_gate": True,
                "fixture_passing_wrong_gate": False,
            },
        }
        self.assertEqual(
            analysis.verdict(summary),
            "scale-positive-sota-delta-not-established",
        )

    def test_fixture_passing_wrong_count(self) -> None:
        records = [
            {
                "label": "plausible_wrong",
                "compiled": True,
                "features": {"fixture_mismatch_rate": 0.0},
            },
            {
                "label": "plausible_wrong",
                "compiled": True,
                "features": {"fixture_mismatch_rate": 1.0},
            },
        ]
        self.assertEqual(analysis.fixture_passing_wrong_count(records), 1)


if __name__ == "__main__":
    unittest.main()
