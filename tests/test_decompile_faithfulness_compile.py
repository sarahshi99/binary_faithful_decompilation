from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import fixtures


class DecompileFaithfulnessCompileTest(unittest.TestCase):
    def test_compile_and_run_original_case(self) -> None:
        case = fixtures.case_by_id("absdiff")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case=case,
                candidate_id="original",
                function_source=case.function_source,
                output_dir=Path(td),
                opt_level="O0",
            )
        self.assertTrue(result.compiled, result.stderr)
        self.assertTrue(result.behavior_passed, result.run_stdout + result.run_stderr)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.object_path.name.endswith(".o"))
        self.assertTrue(result.exe_path.name.endswith(".exe"))
        self.assertIn(".function.c", result.source_path.name)

    def test_behavior_gate_catches_wrong_predicate(self) -> None:
        case = fixtures.case_by_id("absdiff")
        wrong_source = case.function_source.replace("a > b", "a < b")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case=case,
                candidate_id="predicate_lt",
                function_source=wrong_source,
                output_dir=Path(td),
                opt_level="O0",
            )
        self.assertTrue(result.compiled, result.stderr)
        self.assertFalse(result.behavior_passed)
        self.assertGreaterEqual(result.exit_code, 100)

    def test_compile_gate_records_syntax_failure(self) -> None:
        case = fixtures.case_by_id("clamp8")
        bad_source = "int clamp8(int x) { return ; }"
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case=case,
                candidate_id="syntax_bad",
                function_source=bad_source,
                output_dir=Path(td),
                opt_level="O0",
            )
        self.assertFalse(result.compiled)
        self.assertFalse(result.behavior_passed)
        self.assertIn("error", result.stderr.lower())

    def test_run_command_records_timeout(self) -> None:
        result = ccompile.run_command(
            ["/bin/sh", "-c", "sleep 2"],
            timeout_s=1,
        )

        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", result.stderr)


if __name__ == "__main__":
    unittest.main()
