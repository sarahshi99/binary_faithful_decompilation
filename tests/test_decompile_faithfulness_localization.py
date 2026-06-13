from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import localization


class DecompileFaithfulnessLocalizationTest(unittest.TestCase):
    def test_component_to_slot_votes_maps_expected_components(self) -> None:
        components = {
            "branch_count_abs": 1.0,
            "opcode_l1": 4.0,
            "immediate_symmetric_diff": 0.0,
            "call_count_abs": 0.0,
        }
        votes = localization.component_to_slot_votes(components)
        self.assertGreater(votes["branch_predicate"], votes["constant"])
        self.assertGreater(votes["control_structure"], 0.0)

    def test_localization_hit_at_k(self) -> None:
        ranked = ["branch_predicate", "control_structure", "constant"]
        self.assertTrue(localization.hit_at_k(ranked, "branch_predicate", 1))
        self.assertFalse(localization.hit_at_k(ranked, "constant", 2))
        self.assertTrue(localization.hit_at_k(ranked, "constant", 3))

    def test_localization_summary_counts_hits(self) -> None:
        rows = [
            localization.LocalizationRecord("a", "mut1", "branch_predicate", ["branch_predicate", "constant"]),
            localization.LocalizationRecord("a", "mut2", "constant", ["branch_predicate", "constant"]),
        ]
        summary = localization.compute_localization_summary(rows)
        self.assertEqual(summary["record_count"], 2)
        self.assertAlmostEqual(summary["hit_at_1"], 0.5)
        self.assertAlmostEqual(summary["hit_at_2"], 1.0)

    def test_slot_vote_concentration_tracks_localized_mismatch(self) -> None:
        concentrated = {"constant": 9.0, "branch_predicate": 1.0, "control_structure": 0.0}
        diffuse = {"constant": 4.0, "branch_predicate": 3.0, "control_structure": 3.0}
        self.assertGreater(
            localization.slot_vote_concentration(concentrated),
            localization.slot_vote_concentration(diffuse),
        )

    def test_pairwise_suspicion_auc_treats_higher_score_as_more_wrong(self) -> None:
        rows = [
            localization.SuspicionRecord("a", "faithful", "faithful", 0.3),
            localization.SuspicionRecord("a", "wrong", "plausible_wrong", 0.8),
            localization.SuspicionRecord("b", "faithful", "faithful", 0.5),
            localization.SuspicionRecord("b", "wrong", "plausible_wrong", 0.5),
        ]
        self.assertAlmostEqual(localization.pairwise_suspicion_auc(rows), 0.75)


if __name__ == "__main__":
    unittest.main()
