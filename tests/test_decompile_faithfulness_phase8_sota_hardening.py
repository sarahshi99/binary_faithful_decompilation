from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import run_phase8_sota_hardening as phase8


class Phase8SotaHardeningTest(unittest.TestCase):
    def test_build_case_stats_and_auc(self) -> None:
        records = [
            record("a", "faithful", fixture=0.0, static=0.0, trace_mismatch=0.0, trace_total=0.0),
            record("a", "plausible_wrong", fixture=1.0, static=0.2, trace_mismatch=1.0, trace_total=1.5),
            record("b", "faithful", fixture=0.0, static=0.0, trace_mismatch=0.0, trace_total=0.0),
            record("b", "plausible_wrong", fixture=0.0, static=0.0, trace_mismatch=0.0, trace_total=0.0),
        ]
        stats = phase8.build_case_stats(records)
        auc = phase8.aggregate_metric(stats, list(stats))
        self.assertEqual(auc["v3_trace_total"], 0.75)
        self.assertEqual(auc["fixture_only"], 0.75)

    def test_bootstrap_reports_strong_baseline_erasing_margin(self) -> None:
        records = [
            record("a", "faithful", fixture=0.0, static=0.0, trace_mismatch=0.0, trace_total=0.0),
            record("a", "plausible_wrong", fixture=0.0, static=0.0, trace_mismatch=1.0, trace_total=1.0),
            record("b", "faithful", fixture=0.0, static=0.0, trace_mismatch=0.0, trace_total=0.0),
            record("b", "plausible_wrong", fixture=1.0, static=0.0, trace_mismatch=1.0, trace_total=1.0),
        ]
        stats = phase8.build_case_stats(records)
        point = phase8.aggregate_metric(stats, list(stats))
        self.assertEqual(point["fuzzing_mismatch_rate"], point["v3_trace_total"])
        gate = {
            "phase7c2_present": True,
            "legacy_delta_ci_lower_gt_zero": True,
            "strong_baseline_not_erased": False,
        }
        self.assertEqual(phase8.phase8_verdict(gate), "strong-baseline-erases-v3-extra-margin")

    def test_combined_summary_loader_dedupes_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            write_jsonl(
                run_dir / "records.jsonl",
                [
                    {"case_id": "a", "candidate_id": "x", "label": "faithful", "compiled": True},
                    {"case_id": "a", "candidate_id": "x", "label": "faithful", "compiled": True},
                ],
            )
            summary = {"run_dirs": [str(run_dir), str(run_dir)]}
            summary_path = root / "combined.json"
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            spec = phase8.DatasetSpec(
                dataset_id="demo",
                title="Demo",
                combined_summary_path=Path("combined.json"),
            )
            records = phase8.load_dataset_records(root, spec)
        self.assertEqual(len(records), 1)

    def test_ci95_interpolates_bounds(self) -> None:
        low, high = phase8.ci95([0.0, 1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(low, 0.1)
        self.assertAlmostEqual(high, 3.9)


def record(
    case_id: str,
    label: str,
    *,
    fixture: float,
    static: float,
    trace_mismatch: float,
    trace_total: float,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": f"{case_id}_{label}_{fixture}_{trace_total}",
        "label": label,
        "compiled": True,
        "features": {
            "fixture_mismatch_rate": fixture,
            "static_structured_total": static,
            "trace_mismatch_rate": trace_mismatch,
            "trace_total": trace_total,
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
