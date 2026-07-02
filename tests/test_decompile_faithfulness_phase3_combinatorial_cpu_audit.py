from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as audit


class DecompileFaithfulnessPhase3CombinatorialCpuAuditTest(unittest.TestCase):
    def test_pairwise_auc_is_case_aware(self) -> None:
        records = [
            _record("a", "faithful", 0.0),
            _record("a", "plausible_wrong", 1.0),
            _record("b", "faithful", 10.0),
            _record("b", "plausible_wrong", 11.0),
        ]

        self.assertEqual(audit._pairwise_auc(records, audit._trace_score), 1.0)

    def test_fixture_passing_wrong_count_requires_trace_mismatch(self) -> None:
        records = [
            _record("a", "plausible_wrong", 0.5, fixture_mismatch=0.0, trace_mismatch=0.1),
            _record("a", "plausible_wrong", 0.0, fixture_mismatch=0.0, trace_mismatch=0.0),
            _record("a", "faithful", 0.0, fixture_mismatch=0.0, trace_mismatch=0.0),
        ]

        self.assertEqual(audit._fixture_passing_wrong_count(records), 1)

    def test_verdict_requires_non_fixture_collapse_subsets(self) -> None:
        summary = {
            "pairwise_auc": 1.0,
            "fixture_collapse": False,
            "fixture_passing_wrong_count": 3,
            "recommended_subset_metrics": [
                {
                    "pairwise_auc": 1.0,
                    "fixture_collapse": False,
                    "fixture_passing_wrong_count": 1,
                }
            ],
        }

        self.assertEqual(audit._verdict(summary), "pass-combinatorial-phase3-cpu-audit")


def _record(
    case_id: str,
    label: str,
    trace_total: float,
    fixture_mismatch: float = 0.0,
    trace_mismatch: float = 0.0,
) -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "features": {
            "trace_total": trace_total,
            "fixture_mismatch_rate": fixture_mismatch,
            "trace_mismatch_rate": trace_mismatch,
        },
    }


if __name__ == "__main__":
    unittest.main()
