from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import ranking


class DecompileFaithfulnessRankingTest(unittest.TestCase):
    def test_rank_candidates_orders_low_distance_first(self) -> None:
        rows = [
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="wrong",
                label="plausible_wrong",
                distance=3.0,
                mutation_type="predicate",
            ),
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="faithful",
                label="faithful",
                distance=0.0,
                mutation_type="original",
            ),
        ]
        ranked = ranking.rank_candidates(rows)
        self.assertEqual([row.candidate_id for row in ranked], ["faithful", "wrong"])

    def test_compute_ranking_summary_counts_top1_success(self) -> None:
        rows = [
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="faithful",
                label="faithful",
                distance=0.0,
                mutation_type="original",
            ),
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="wrong",
                label="plausible_wrong",
                distance=2.0,
                mutation_type="predicate",
            ),
            ranking.CandidateDistance(
                case_id="b",
                candidate_id="wrong",
                label="plausible_wrong",
                distance=1.0,
                mutation_type="constant",
            ),
            ranking.CandidateDistance(
                case_id="b",
                candidate_id="faithful",
                label="faithful",
                distance=3.0,
                mutation_type="original",
            ),
        ]
        summary = ranking.compute_ranking_summary(rows)
        self.assertEqual(summary["case_count"], 2)
        self.assertEqual(summary["top1_faithful_count"], 1)
        self.assertAlmostEqual(summary["top1_faithful_rate"], 0.5)
        self.assertEqual(summary["by_mutation_type"]["predicate"]["candidate_count"], 1)
        self.assertEqual(summary["by_mutation_type"]["constant"]["candidate_count"], 1)

    def test_pairwise_auc_handles_ties_as_half_credit(self) -> None:
        rows = [
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="faithful",
                label="faithful",
                distance=1.0,
                mutation_type="original",
            ),
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="wrong1",
                label="plausible_wrong",
                distance=2.0,
                mutation_type="predicate",
            ),
            ranking.CandidateDistance(
                case_id="a",
                candidate_id="wrong2",
                label="plausible_wrong",
                distance=1.0,
                mutation_type="constant",
            ),
        ]
        self.assertAlmostEqual(ranking.pairwise_auc(rows), 0.75)

    def test_load_external_candidate_manifest(self) -> None:
        manifest = {
            "case_id": "absdiff",
            "candidates": [
                {
                    "candidate_id": "ghidra_like_wrong",
                    "label": "unknown",
                    "mutation_type": "external_decompiler",
                    "function_source": "int absdiff(int a, int b) { return a - b; }",
                }
            ],
        }
        rows = ranking.external_candidates_from_manifest(manifest)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].case_id, "absdiff")
        self.assertEqual(rows[0].candidate_id, "ghidra_like_wrong")
        self.assertEqual(rows[0].label, "unknown")
        self.assertEqual(rows[0].mutation_type, "external_decompiler")


if __name__ == "__main__":
    unittest.main()
