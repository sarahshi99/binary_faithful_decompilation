from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import select_phase3_source_subsets as selection


class DecompileFaithfulnessPhase3SourceSelectionTest(unittest.TestCase):
    def test_render_fixture_harness_uses_expected_values(self) -> None:
        harness = selection.render_fixture_harness(
            "int f(int x) { return x + 1; }",
            "f",
            [{"args": [2], "expected": 3}],
        )

        self.assertIn("if (f(2) != 3)", harness)
        self.assertIn("return 100;", harness)

    def test_validate_source_pool_compiles_and_runs_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "src"
            source_dir.mkdir()
            (source_dir / "f.c").write_text("int f(int x) { return x + 1; }\n")
            functions = [
                {
                    "case_id": "f",
                    "source_path": "src/f.c",
                    "function_name": "f",
                    "fixtures": [{"args": [2], "expected": 3}],
                    "tags": ["arithmetic"],
                    "risk_families": ["toy"],
                }
            ]

            results = selection.validate_source_pool(root, functions, root / "out")

        self.assertEqual(results[0]["case_id"], "f")
        self.assertTrue(results[0]["compiled"])
        self.assertTrue(results[0]["fixture_passed"])

    def test_diverse_subset_selection_limits_overlap(self) -> None:
        functions = [
            _function("a", ["branch"], ["p"]),
            _function("b", ["loop"], ["q"]),
            _function("c", ["bitwise"], ["r"]),
            _function("d", ["division"], ["s"]),
            _function("e", ["boundary"], ["t"]),
            _function("f", ["sign_zero"], ["u"]),
        ]

        subsets = selection.enumerate_source_subsets(functions, min_size=3, max_size=4)
        selected = selection.select_diverse_subsets(subsets, limit=2, max_jaccard=0.5)

        self.assertGreaterEqual(len(subsets), 1)
        self.assertEqual(len(selected), 2)


def _function(case_id: str, tags: list[str], risks: list[str]) -> dict:
    return {
        "case_id": case_id,
        "tags": tags,
        "risk_families": risks,
    }


if __name__ == "__main__":
    unittest.main()
