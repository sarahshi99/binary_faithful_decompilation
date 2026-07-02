from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase14_paper_readiness as phase14


class Phase14PaperReadinessTest(unittest.TestCase):
    def test_pairwise_auc_and_detection_use_case_records(self) -> None:
        records = [
            row("a", "faithful", 0.0),
            row("a", "plausible_wrong", 1.0),
            row("b", "faithful", 0.0),
            row("b", "plausible_wrong", 0.0),
        ]
        self.assertEqual(phase14.pairwise_auc(records), 0.75)
        self.assertEqual(phase14.wrong_detection_rate(records), 0.5)

    def test_case_bootstrap_respects_case_sampling(self) -> None:
        records = [
            row("a", "faithful", 0.0),
            row("a", "plausible_wrong", 1.0),
            row("b", "faithful", 0.0),
            row("b", "plausible_wrong", 0.0),
        ]
        metrics = phase14.bootstrap_case_metrics(records, iterations=20, seed=7)
        self.assertIn("auc_ci95", metrics)
        self.assertIn("wrong_detection_rate_ci95", metrics)
        self.assertLessEqual(metrics["auc_ci95"][0], metrics["auc_ci95"][1])

    def test_miss_taxonomy_groups_fixture_ifchain(self) -> None:
        records = [
            row("a", "faithful", 0.0, candidate_id="phase6_a_original_control"),
            row("a", "plausible_wrong", 0.0, candidate_id="phase6_a_fixture_ifchain_00"),
            row("b", "plausible_wrong", 1.0, candidate_id="phase6_b_fixture_ifchain_00"),
        ]
        taxonomy = phase14.miss_taxonomy(records)
        self.assertEqual(taxonomy["missed_wrong_count"], 1)
        self.assertEqual(taxonomy["by_candidate_family"], {"fixture_ifchain": 1})

    def test_phase14_verdict(self) -> None:
        self.assertEqual(
            phase14.phase14_verdict({"a": True, "b": True}),
            "pass-phase14-paper-readiness-hardening",
        )
        self.assertEqual(
            phase14.phase14_verdict({"a": True, "b": False}),
            "partial-phase14-paper-readiness-hardening",
        )
        self.assertEqual(
            phase14.phase14_verdict({"a": False, "b": False}),
            "fail-phase14-paper-readiness-hardening",
        )


def row(
    case_id: str,
    label: str,
    mismatch_count: float,
    candidate_id: str | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id or f"{case_id}_{label}",
        "label": label,
        "compiled": True,
        "requested_budget": 8,
        "actual_budget": 8,
        "features": {
            "trace_mismatch_count": mismatch_count,
            "trace_mismatch_rate": mismatch_count,
        },
    }


if __name__ == "__main__":
    unittest.main()
