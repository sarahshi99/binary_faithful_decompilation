from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from analysis.decompile_faithfulness import run_structural_binding_audit as audit


class DecompileFaithfulnessStructuralBindingAuditTest(unittest.TestCase):
    def test_object_path_lookup_uses_phase1h_candidate_naming(self) -> None:
        root = Path("artifact")
        record = {
            "case_id": "signum",
            "candidate_id": "manual_signum_reversed_signs",
        }

        paths = audit._object_paths_for_record(root, "O2", record)

        self.assertEqual(
            paths.original,
            root / "o2" / "candidates" / "signum__original__O2.function.o",
        )
        self.assertEqual(
            paths.candidate,
            root / "o2" / "candidates" / "signum__manual_signum_reversed_signs__O2.function.o",
        )

    def test_aggregate_records_adds_structured_features_across_opts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "phase1h"
            for opt_level in ["O0", "O1", "O2", "O3"]:
                _write_records(
                    root,
                    opt_level,
                    [
                        _record("signum", "faithful", "faithful", 0.2),
                        _record("signum", "wrong", "plausible_wrong", 0.8),
                    ],
                )

            def fake_distance(paths: audit.ObjectPaths) -> dict[str, float]:
                score = 0.0 if "__faithful__" in str(paths.candidate) else 4.0
                return {
                    "basic_block_shape_l1": 0.0,
                    "terminal_opcode_l1": 0.0,
                    "cfg_edge_motif_l1": score / 4.0,
                    "branch_return_binding_l1": score / 2.0,
                    "compare_branch_return_l1": score / 4.0,
                    "loop_update_binding_l1": 0.0,
                    "structured_binding_total": score,
                }

            records = audit._aggregate_records([root], distance_fn=fake_distance)
            by_candidate = {record["candidate_id"]: record for record in records}

            self.assertAlmostEqual(by_candidate["faithful"]["features"]["min_slot"], 0.2)
            self.assertAlmostEqual(by_candidate["faithful"]["features"]["mean_slot"], 0.2)
            self.assertAlmostEqual(by_candidate["wrong"]["features"]["max_structured_binding_total"], 4.0)
            self.assertAlmostEqual(by_candidate["wrong"]["features"]["mean_branch_return_binding_l1"], 2.0)
            self.assertEqual(set(by_candidate["wrong"]["by_opt"]), {"O0", "O1", "O2", "O3"})

    def test_leave_one_case_out_selects_formula_from_training_cases(self) -> None:
        records = [
            _scored("a", "a_faithful", "faithful", min_slot=0.0, structured_binding_total=0.0),
            _scored("a", "a_wrong", "plausible_wrong", min_slot=0.0, structured_binding_total=4.0),
            _scored("b", "b_faithful", "faithful", min_slot=0.0, structured_binding_total=0.0),
            _scored("b", "b_wrong", "plausible_wrong", min_slot=0.0, structured_binding_total=4.0),
            _scored("c", "c_faithful", "faithful", min_slot=0.0, structured_binding_total=0.0),
            _scored("c", "c_wrong", "plausible_wrong", min_slot=0.0, structured_binding_total=4.0),
        ]

        result = audit._leave_one_case_out(records, audit._formulas())

        self.assertAlmostEqual(result["pairwise_auc"], 1.0)
        self.assertTrue(
            all(
                fold["selected_formula"] == "structured_only"
                for fold in result["folds"]
            )
        )

    def test_labels_are_not_used_for_structured_feature_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "phase1h"
            _write_records(
                root,
                "O0",
                [_record("signum", "wrong", "DO_NOT_PASS_TO_EXTRACTOR", 0.8)],
            )

            with mock.patch.object(audit.structured_features, "extract_structured_features") as extract:
                with mock.patch.object(audit.structured_features, "structured_feature_distance") as distance:
                    extract.side_effect = lambda path: object()
                    distance.return_value = {
                        "basic_block_shape_l1": 0.0,
                        "terminal_opcode_l1": 0.0,
                        "cfg_edge_motif_l1": 0.0,
                        "branch_return_binding_l1": 0.0,
                        "compare_branch_return_l1": 0.0,
                        "loop_update_binding_l1": 0.0,
                        "structured_binding_total": 0.0,
                    }

                    audit._aggregate_records([root])

            called_paths = [call.args[0] for call in extract.call_args_list]
            self.assertEqual(len(called_paths), 2)
            self.assertTrue(all(isinstance(path, Path) for path in called_paths))
            self.assertTrue(all("DO_NOT_PASS_TO_EXTRACTOR" not in str(path) for path in called_paths))


def _write_records(root: Path, opt_level: str, records: list[dict[str, object]]) -> None:
    opt_dir = root / opt_level.lower()
    candidate_dir = opt_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        case_id = str(record["case_id"])
        candidate_id = str(record["candidate_id"])
        (candidate_dir / f"{case_id}__original__{opt_level}.function.o").write_text("", encoding="utf-8")
        (candidate_dir / f"{case_id}__{candidate_id}__{opt_level}.function.o").write_text("", encoding="utf-8")
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
        "global_distance": score,
        "components": {},
    }


def _scored(
    case_id: str,
    candidate_id: str,
    label: str,
    *,
    min_slot: float,
    structured_binding_total: float,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "mutation_type": "manual",
        "features": {
            "min_slot": min_slot,
            "mean_slot": min_slot,
            "max_structured_binding_total": structured_binding_total,
            "mean_structured_binding_total": structured_binding_total,
            "max_branch_return_binding_l1": structured_binding_total,
            "max_cfg_edge_motif_l1": structured_binding_total,
            "structured_only": structured_binding_total,
        },
    }


if __name__ == "__main__":
    unittest.main()
