from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase1l_ablation_audit as audit


class DecompileFaithfulnessPhase1LAblationTest(unittest.TestCase):
    def test_pairwise_auc_scores_wrong_above_faithful_within_case(self) -> None:
        records = [
            _record("a", "faithful", "faithful", score=0.1),
            _record("a", "wrong", "plausible_wrong", score=0.9),
            _record("b", "faithful", "faithful", score=0.2),
            _record("b", "wrong", "plausible_wrong", score=0.4),
        ]

        self.assertAlmostEqual(
            audit._pairwise_auc(records, lambda record: record["features"]["score"]),
            1.0,
        )

    def test_variant_summary_reads_requested_feature(self) -> None:
        records = [
            _record("a", "faithful", "faithful", score=0.1, min_slot=0.8),
            _record("a", "wrong", "plausible_wrong", score=0.9, min_slot=0.2),
        ]

        summary = audit._variant_summary("trace", records, "score")

        self.assertEqual(summary["name"], "trace")
        self.assertEqual(summary["score_feature"], "score")
        self.assertAlmostEqual(summary["pairwise_auc"], 1.0)
        self.assertAlmostEqual(summary["case_pairwise_auc"]["a"], 1.0)

    def test_score_vectors_identical_detects_fixture_collapse(self) -> None:
        records = [
            _record("a", "faithful", "faithful", trace=0.0, fixture=0.0),
            _record("a", "wrong", "plausible_wrong", trace=1.0, fixture=1.0),
        ]

        self.assertTrue(
            audit._score_vectors_identical(records, "trace_mismatch_rate", "fixture_mismatch_rate")
        )

    def test_leakage_audit_reports_fixture_argument_only_policy(self) -> None:
        records = [
            _record("a", "faithful", "faithful", trace=0.0, fixture=0.0),
            _record("a", "wrong", "plausible_wrong", trace=1.0, fixture=0.0),
        ]

        leakage = audit._leakage_audit(records)

        self.assertEqual(leakage["domain_inference_source"], "fixture_argument_values_only")
        self.assertFalse(leakage["v2_scores_identical_to_fixture_only"])
        self.assertEqual(leakage["verdict"], "no-label-or-output-leakage-found")


def _record(
    case_id: str,
    candidate_id: str,
    label: str,
    *,
    score: float = 0.0,
    trace: float | None = None,
    fixture: float | None = None,
    min_slot: float = 0.0,
) -> dict[str, object]:
    trace_score = score if trace is None else trace
    fixture_score = score if fixture is None else fixture
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "features": {
            "score": score,
            "trace_mismatch_rate": trace_score,
            "trace_total": trace_score,
            "fixture_mismatch_rate": fixture_score,
            "min_slot": min_slot,
        },
    }


if __name__ == "__main__":
    unittest.main()
