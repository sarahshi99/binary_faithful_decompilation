from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from analysis.decompile_faithfulness import run_dynamic_trace_audit as audit


class DecompileFaithfulnessDynamicTraceAuditTest(unittest.TestCase):
    def test_source_paths_for_record_use_phase1h_o0_candidate_naming(self) -> None:
        root = Path("artifact")
        record = {"case_id": "signum", "candidate_id": "manual_signum_reversed_signs"}

        paths = audit._source_paths_for_record(root, record)

        self.assertEqual(
            paths.original,
            root / "o0" / "candidates" / "signum__original__O0.function.c",
        )
        self.assertEqual(
            paths.candidate,
            root / "o0" / "candidates" / "signum__manual_signum_reversed_signs__O0.function.c",
        )

    def test_aggregate_records_adds_trace_features_without_using_labels_for_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "phase1h"
            _write_records(
                root,
                [
                    _record("signum", "faithful", "faithful", 0.2),
                    _record("signum", "wrong", "plausible_wrong", 0.8),
                ],
            )

            def fake_distance(paths: audit.SourcePaths) -> dict[str, float]:
                score = 0.0 if "__faithful__" in str(paths.candidate) else 1.0
                return _trace_components(score)

            records = audit._aggregate_records([root], distance_fn=fake_distance)
            by_id = {record["candidate_id"]: record for record in records}

            self.assertAlmostEqual(by_id["faithful"]["features"]["trace_total"], 0.0)
            self.assertAlmostEqual(by_id["wrong"]["features"]["trace_mismatch_rate"], 1.0)
            self.assertAlmostEqual(by_id["wrong"]["features"]["min_slot"], 0.8)
            self.assertEqual(by_id["wrong"]["label"], "plausible_wrong")

    def test_default_aggregation_passes_only_paths_to_dynamic_distance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "phase1h"
            _write_records(root, [_record("signum", "wrong", "DO_NOT_PASS_TO_TRACE", 0.8)])

            with mock.patch.object(audit, "_dynamic_distance_for_paths") as distance:
                distance.return_value = _trace_components(0.0)
                audit._aggregate_records([root])

            self.assertEqual(distance.call_count, 1)
            paths = distance.call_args.args[0]
            self.assertIsInstance(paths, audit.SourcePaths)
            self.assertNotIn("DO_NOT_PASS_TO_TRACE", str(paths.original))
            self.assertNotIn("DO_NOT_PASS_TO_TRACE", str(paths.candidate))

    def test_leave_one_case_out_selects_trace_formula_from_training_cases(self) -> None:
        records = [
            _scored("a", "a_faithful", "faithful", trace_total=0.0),
            _scored("a", "a_wrong", "plausible_wrong", trace_total=1.0),
            _scored("b", "b_faithful", "faithful", trace_total=0.0),
            _scored("b", "b_wrong", "plausible_wrong", trace_total=1.0),
            _scored("c", "c_faithful", "faithful", trace_total=0.0),
            _scored("c", "c_wrong", "plausible_wrong", trace_total=1.0),
        ]

        result = audit._leave_one_case_out(records, audit._formulas())

        self.assertAlmostEqual(result["pairwise_auc"], 1.0)
        self.assertTrue(
            all(fold["selected_formula"] == "trace_mismatch_rate" for fold in result["folds"])
        )


def _write_records(root: Path, records: list[dict[str, object]]) -> None:
    opt_dir = root / "o0"
    candidate_dir = opt_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        case_id = str(record["case_id"])
        candidate_id = str(record["candidate_id"])
        (candidate_dir / f"{case_id}__original__O0.function.c").write_text(
            "int signum(int x) { return x; }\n",
            encoding="utf-8",
        )
        (candidate_dir / f"{case_id}__{candidate_id}__O0.function.c").write_text(
            "int signum(int x) { return x; }\n",
            encoding="utf-8",
        )
    (opt_dir / "records.jsonl").write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _record(case_id: str, candidate_id: str, label: str, score: float) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "mutation_type": "manual",
        "slot_concentration": score,
    }


def _scored(case_id: str, candidate_id: str, label: str, *, trace_total: float) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "mutation_type": "manual",
        "features": {
            "trace_mismatch_rate": trace_total,
            "trace_total": trace_total,
            "min_slot": 0.0,
        },
    }


def _trace_components(score: float) -> dict[str, float]:
    return {
        "trace_input_count": 8.0,
        "trace_mismatch_count": score * 8.0,
        "trace_mismatch_rate": score,
        "trace_abs_error_mean": score,
        "trace_abs_error_max": score,
        "trace_sign_mismatch_rate": score,
        "trace_zero_mismatch_rate": 0.0,
        "trace_boundary_mismatch_rate": score,
        "trace_total": score,
        "fixture_mismatch_rate": score,
        "fixture_behavior_passed": 1.0 - min(score, 1.0),
    }


if __name__ == "__main__":
    unittest.main()
