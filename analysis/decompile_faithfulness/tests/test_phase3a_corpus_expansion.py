from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import phase3a_corpus_expansion as expansion


class Phase3aCorpusExpansionTest(unittest.TestCase):
    def test_target_feasibility_reconciles_project_capacity(self) -> None:
        rows = _rows([43, 10, 9, 9, 8, 4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1])
        target_80 = expansion.target_feasibility(rows, 80)
        target_81 = expansion.target_feasibility(rows, 81)
        target_90 = expansion.target_feasibility(rows, 90)
        self.assertTrue(target_80["feasible_under_expansion_framework"])
        self.assertFalse(target_81["feasible_under_expansion_framework"])
        self.assertFalse(target_90["feasible_under_expansion_framework"])
        self.assertIn("dominance_share_capacity_shortfall", target_90["reasons"])

    def test_no_candidate_or_label_guard_detects_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(expansion.guard_no_candidate_or_label_artifacts(root)["ok"])
            path = root / "results/decompile_faithfulness/phase3a_exact_labels.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text("label\n", encoding="utf-8")
            result = expansion.guard_no_candidate_or_label_artifacts(root)
        self.assertFalse(result["ok"])
        self.assertEqual(result["present_paths"], ["results/decompile_faithfulness/phase3a_exact_labels.jsonl"])

    def test_v2_artifact_guard_detects_existing_v2_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(expansion.guard_no_v2_artifacts(root)["ok"])
            path = root / "analysis/decompile_faithfulness/phase3a_function_fixture_seal_v2.json"
            path.parent.mkdir(parents=True)
            path.write_text("{}\n", encoding="utf-8")
            result = expansion.guard_no_v2_artifacts(root)
        self.assertFalse(result["ok"])
        self.assertEqual(result["present_paths"], ["analysis/decompile_faithfulness/phase3a_function_fixture_seal_v2.json"])

    def test_auditor_import_guard(self) -> None:
        self.assertEqual(expansion.guard_against_auditor_imports(), {"imports_ok": True, "calls_ok": True})
        tree = ast.parse(Path(expansion.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, expansion.FORBIDDEN_AUDITOR_IMPORTS)


def _rows(counts: list[int]) -> list[dict[str, str]]:
    rows = []
    for project, count in enumerate(counts):
        for index in range(count):
            rows.append(
                {
                    "project": f"p{project}",
                    "function_id": f"p{project}::f{index}",
                    "argument_count": "1",
                    "domain_size": "128",
                    "loop_count": "0",
                    "lookup_table_access": "0",
                    "bitwise_operation_count": "0",
                    "branch_count": "0",
                    "multiple_interacting_arguments": "0",
                    "switch_like_categorical_behavior": "0",
                }
            )
    return rows


if __name__ == "__main__":
    unittest.main()
