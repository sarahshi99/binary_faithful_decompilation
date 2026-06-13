from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_component_combination_audit as combo


class DecompileFaithfulnessComponentCombinationTest(unittest.TestCase):
    def test_pairwise_auc_scores_higher_wrong_as_success(self) -> None:
        records = [
            {"case_id": "a", "label": "faithful", "features": {"score": 0.2}},
            {"case_id": "a", "label": "plausible_wrong", "features": {"score": 0.8}},
            {"case_id": "b", "label": "faithful", "features": {"score": 0.5}},
            {"case_id": "b", "label": "plausible_wrong", "features": {"score": 0.5}},
        ]
        self.assertAlmostEqual(
            combo._pairwise_auc(records, lambda record: record["features"]["score"]),
            0.75,
        )

    def test_squash_keeps_zero_and_bounds_positive_values(self) -> None:
        self.assertEqual(combo._squash(0.0), 0.0)
        self.assertGreater(combo._squash(10.0), combo._squash(1.0))
        self.assertLess(combo._squash(10.0), 1.0)


if __name__ == "__main__":
    unittest.main()
