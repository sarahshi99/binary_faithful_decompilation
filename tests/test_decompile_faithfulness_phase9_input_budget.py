from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase9_input_budget as phase9


class Phase9InputBudgetTest(unittest.TestCase):
    def test_budget_hit_probability_uses_without_replacement_sampling(self) -> None:
        row = record("wrong", trace_input_count=10, trace_mismatch_count=2)
        self.assertAlmostEqual(phase9.budget_hit_probability(row, 1), 0.2)
        self.assertAlmostEqual(phase9.budget_hit_probability(row, 2), 1.0 - (8 / 10) * (7 / 9))

    def test_budget_hit_probability_handles_zero_and_saturation(self) -> None:
        self.assertEqual(phase9.budget_hit_probability(record("wrong", 0, 0), 8), 0.0)
        self.assertEqual(phase9.budget_hit_probability(record("wrong", 5, 0), 8), 0.0)
        self.assertEqual(phase9.budget_hit_probability(record("wrong", 5, 1), 5), 1.0)

    def test_budget_metrics_reports_auc_and_detection_stats(self) -> None:
        rows = [
            scored("a", "faithful", 0, 10),
            scored("a", "plausible_wrong", 2, 10),
            scored("b", "faithful", 0, 10),
            scored("b", "plausible_wrong", 0, 10),
        ]
        metrics = phase9.budget_metrics(rows, [rows[1], rows[3]], budget=1)
        self.assertEqual(metrics["auc"], 0.75)
        self.assertAlmostEqual(metrics["wrong_detection_mean"], 0.1)

    def test_grouped_family_metrics_finds_v3_delta(self) -> None:
        rows = [
            family_record("toy", "faithful", 0.0, 0.0, "risk_a"),
            family_record("toy", "plausible_wrong", 0.0, 1.0, "risk_a"),
        ]
        grouped = phase9.grouped_family_metrics(rows)
        self.assertGreater(grouped["risk:risk_a"]["delta_v3_vs_fuzzing_mismatch"], 0.0)
        self.assertGreater(grouped["mutation:mut"]["delta_v3_vs_fuzzing_mismatch"], 0.0)


def record(label: str, trace_input_count: int, trace_mismatch_count: int) -> dict[str, object]:
    return {
        "case_id": "case",
        "label": label,
        "features": {
            "trace_input_count": float(trace_input_count),
            "trace_mismatch_count": float(trace_mismatch_count),
        },
    }


def scored(case_id: str, label: str, mismatch_count: int, input_count: int) -> dict[str, object]:
    return {
        "case_id": case_id,
        "label": label,
        "compiled": True,
        "features": {
            "trace_input_count": float(input_count),
            "trace_mismatch_count": float(mismatch_count),
            "trace_mismatch_rate": mismatch_count / input_count if input_count else 0.0,
            "trace_total": mismatch_count / input_count if input_count else 0.0,
        },
    }


def family_record(
    case_id: str,
    label: str,
    fuzzing_mismatch: float,
    v3_total: float,
    risk: str,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "label": label,
        "compiled": True,
        "mutation_type": "mut",
        "metadata": {"risk_families": [risk]},
        "features": {
            "trace_mismatch_rate": fuzzing_mismatch,
            "trace_total": v3_total,
            "fixture_mismatch_rate": 0.0,
            "static_structured_total": 0.0,
        },
    }


if __name__ == "__main__":
    unittest.main()
