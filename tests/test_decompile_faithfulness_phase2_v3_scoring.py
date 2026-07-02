from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase2_v3_scoring_diagnostic as diag


class DecompileFaithfulnessPhase2V3ScoringTest(unittest.TestCase):
    def test_build_summary_identifies_fixture_only_blind_spot(self) -> None:
        records = [
            _record("signum", "faithful", "faithful", trace_total=0.0, fixture=0.0),
            _record("signum", "wrong", "plausible_wrong", trace_total=0.0, fixture=0.2),
        ]

        summary = diag.build_summary(records)

        self.assertEqual(summary["baseline"]["pairwise_auc"], 0.5)
        self.assertEqual(len(summary["blind_spot_candidates"]), 1)
        self.assertEqual(
            summary["best_fixture_diagnostic"]["formula"],
            "trace_total_plus_fixture_0.25",
        )
        self.assertEqual(summary["verdict"], "needs-boundary-input-regeneration")

    def test_boundary_formula_can_be_method_candidate(self) -> None:
        records = [
            _record("clamp8", "faithful", "faithful", trace_total=0.0, fixture=0.0, boundary=0.0),
            _record("clamp8", "wrong", "plausible_wrong", trace_total=0.0, fixture=0.2, boundary=1.0),
        ]

        summary = diag.build_summary(records)

        self.assertEqual(summary["baseline"]["pairwise_auc"], 0.5)
        self.assertEqual(summary["best_non_fixture"]["formula"], "trace_total_plus_boundary_0.25")
        self.assertEqual(summary["best_non_fixture"]["pairwise_auc"], 1.0)
        self.assertEqual(summary["verdict"], "continue-boundary-formula-v3")


def _record(
    case_id: str,
    candidate_id: str,
    label: str,
    trace_total: float,
    fixture: float,
    boundary: float = 0.0,
) -> dict:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "features": {
            "trace_total": trace_total,
            "fixture_mismatch_rate": fixture,
            "trace_boundary_mismatch_rate": boundary,
            "trace_zero_mismatch_rate": 0.0,
        },
        "metadata": {"prompt_id": "strict_bug"},
    }


if __name__ == "__main__":
    unittest.main()
