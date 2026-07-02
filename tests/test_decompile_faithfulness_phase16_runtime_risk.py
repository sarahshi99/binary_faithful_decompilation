from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase16_runtime_risk_breakdown as phase16


class Phase16RuntimeRiskTest(unittest.TestCase):
    def test_runtime_summary_reports_p95_and_rate(self) -> None:
        summary = phase16.summarize_runtime([0.1, 0.2, 0.4], actual_input_evals=24, total_seconds=1.2)
        self.assertEqual(summary["candidate_count"], 3)
        self.assertAlmostEqual(summary["mean_seconds_per_candidate"], 0.23333333333333336)
        self.assertEqual(summary["p95_seconds_per_candidate"], 0.4)
        self.assertAlmostEqual(summary["input_evals_per_second"], 20.0)

    def test_risk_family_breakdown_duplicates_multitagged_cases(self) -> None:
        entries = {
            "case_a": {"risk_families": ["branch", "boundary"]},
            "case_b": {"risk_families": ["branch"]},
        }
        rows = phase16.risk_family_breakdown(
            [
                row("case_a", "faithful", 0.0),
                row("case_a", "plausible_wrong", 1.0),
                row("case_b", "faithful", 0.0),
                row("case_b", "plausible_wrong", 0.0),
            ],
            entries,
        )
        by_family = {item["risk_family"]: item for item in rows}
        self.assertEqual(by_family["branch"]["case_count"], 2)
        self.assertEqual(by_family["boundary"]["case_count"], 1)
        self.assertEqual(by_family["branch"]["wrong_detection_rate"], 0.5)

    def test_phase16_verdict(self) -> None:
        self.assertEqual(phase16.phase16_verdict({"a": True}), "pass-phase16-runtime-risk-breakdown")
        self.assertEqual(phase16.phase16_verdict({"a": False, "b": True}), "partial-phase16-runtime-risk-breakdown")
        self.assertEqual(phase16.phase16_verdict({"a": False}), "fail-phase16-runtime-risk-breakdown")


def row(case_id: str, label: str, mismatch_count: float) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": f"{case_id}_{label}",
        "label": label,
        "compiled": True,
        "features": {
            "trace_mismatch_count": mismatch_count,
            "trace_mismatch_rate": mismatch_count,
        },
    }


if __name__ == "__main__":
    unittest.main()
