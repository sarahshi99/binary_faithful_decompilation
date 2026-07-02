from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase2_v3_boundary_trace_audit as audit


class DecompileFaithfulnessPhase2V3BoundaryTraceTest(unittest.TestCase):
    def test_pairwise_auc_is_case_aware(self) -> None:
        records = [
            _record("a", "faithful", 0.0),
            _record("a", "plausible_wrong", 1.0),
            _record("b", "faithful", 5.0),
            _record("b", "plausible_wrong", 6.0),
        ]

        self.assertEqual(audit._pairwise_auc(records, audit._trace_score), 1.0)

    def test_source_by_candidate_reads_manifest(self) -> None:
        manifest = [
            {
                "case_id": "signum",
                "candidates": [
                    {
                        "candidate_id": "c1",
                        "function_source": "int signum(int x) { return 0; }",
                    }
                ],
            }
        ]

        self.assertEqual(
            audit._source_by_candidate(manifest)["c1"],
            "int signum(int x) { return 0; }",
        )

    def test_verdict_requires_hard_case_repair(self) -> None:
        summary = {
            "pairwise_auc": 0.97,
            "case_pairwise_auc": {"signum": 1.0, "is_power_of_two": 1.0},
            "fixture_collapse": False,
            "trace_zero_blind_spot_wrong_count": 0,
        }

        self.assertEqual(audit._verdict(summary), "pass-v3-boundary-trace")


def _record(case_id: str, label: str, trace_total: float) -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "features": {"trace_total": trace_total},
    }


if __name__ == "__main__":
    unittest.main()
