from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase6r_ghidra_full as ghidra_full
from analysis.decompile_faithfulness import run_phase6_decompiler_like_candidates as phase6


class Phase6RGhidraFullTest(unittest.TestCase):
    def test_function_names_from_source_extracts_helpers_and_target(self) -> None:
        source = """int helper(int x) {
    return x + 1;
}

int target(int y) { return helper(y); }
"""
        self.assertEqual(
            ghidra_full.function_names_from_source(source),
            ["helper", "target"],
        )

    def test_normalize_ghidra_translation_unit_removes_unused_locals(self) -> None:
        normalized = ghidra_full.normalize_ghidra_translation_unit([
            """
int GCD(int x,int y)

{
  int y_local;
  int x_local;
  if (y != 0) {
    x = GCD(y,x % y);
  }
  return x;
}
"""
        ])
        self.assertIn("typedef unsigned int uint;", normalized)
        self.assertNotIn("int y_local;", normalized)
        self.assertIn("int GCD(int x,int y)", normalized)

    def test_normalize_ghidra_translation_unit_removes_only_truly_unused_locals(self) -> None:
        normalized = ghidra_full.normalize_ghidra_translation_unit([
            """
int GCD(int x,int y)

{
  int iVar1;
  int phase6_decompiler_like_guard;

  if (y == 0) {
    return x;
  }
  do {
    iVar1 = y;
    y = x % iVar1;
    x = iVar1;
  } while (y != 0);
  return iVar1;
}
"""
        ])
        self.assertNotIn("int phase6_decompiler_like_guard;", normalized)
        self.assertIn("int iVar1;", normalized)
        self.assertIn("return iVar1;", normalized)

    def test_select_proxy_candidates_limits_fixture_ifchains(self) -> None:
        candidates = [
            phase6.Phase6Candidate("c", "orig", "m0", "int f(void){return 0;}", "behavior_preserving_original", "s", "n", "objdump", "O0", ""),
            phase6.Phase6Candidate("c", "rw", "m1", "int f(void){return 0;}", "behavior_preserving_rewrite", "s", "n", "objdump", "O0", ""),
            phase6.Phase6Candidate("c", "bad0", "m2", "int f(void){return 1;}", "fixture_passing_semantic_drift", "s", "n", "objdump", "O0", ""),
            phase6.Phase6Candidate("c", "bad1", "m2", "int f(void){return 2;}", "fixture_passing_semantic_drift", "s", "n", "objdump", "O0", ""),
        ]
        selected = ghidra_full.select_proxy_candidates(candidates, max_fixture_ifchains=1)
        self.assertEqual([candidate.candidate_id for candidate in selected], ["orig", "rw", "bad0"])


if __name__ == "__main__":
    unittest.main()
