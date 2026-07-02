from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import analyze_phase3_gpu_generated_smoke as analysis


class DecompileFaithfulnessPhase3GpuGeneratedAnalysisTest(unittest.TestCase):
    def test_pairwise_auc_is_case_aware(self) -> None:
        records = [
            _record("a", "faithful", 0.0),
            _record("a", "plausible_wrong", 1.0),
            _record("b", "faithful", 10.0),
            _record("b", "plausible_wrong", 11.0),
        ]

        self.assertEqual(analysis._pairwise_auc(records, analysis._trace_score), 1.0)

    def test_fixture_passing_trace_mismatch_count(self) -> None:
        records = [
            _record("a", "faithful", 0.2, fixture=0.0, trace=0.1),
            _record("a", "faithful", 0.0, fixture=0.0, trace=0.0),
            _record("a", "plausible_wrong", 1.0, fixture=1.0, trace=1.0),
        ]

        self.assertEqual(analysis._fixture_passing_trace_mismatch_count(records), 1)

    def test_verdict_requires_hidden_non_oracle_signal(self) -> None:
        summary = {
            "candidate_count": 40,
            "compile_pass_count": 20,
            "paired_case_count": 5,
            "pairwise_auc": 0.95,
            "fixture_collapse": False,
            "fixture_passing_trace_mismatch_count": 1,
        }

        self.assertEqual(
            analysis._verdict(summary),
            "pass-phase3-gpu-generated-combined-analysis",
        )


def _record(
    case_id: str,
    label: str,
    trace_total: float,
    fixture: float = 0.0,
    trace: float = 0.0,
) -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "features": {
            "trace_total": trace_total,
            "fixture_mismatch_rate": fixture,
            "trace_mismatch_rate": trace,
        },
    }


if __name__ == "__main__":
    unittest.main()
