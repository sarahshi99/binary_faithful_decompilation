from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase5_deterministic_candidates as det


class Phase5DeterministicCandidatesTest(unittest.TestCase):
    def test_constant_return_preserves_signature_and_uses_params(self) -> None:
        source = det.constant_return_source(
            "int f(int a, char b)",
            7,
            det.zero_use_expression(["a", "b"]),
        )
        self.assertIn("int f(int a, char b) {", source)
        self.assertIn("return 7 + 0 * ((a) + (b));", source)

    def test_candidate_manifest_verdict_requires_scale(self) -> None:
        self.assertEqual(det._candidate_manifest_verdict(99, 38), "needs-full-candidate-generation")
        self.assertEqual(det._candidate_manifest_verdict(100, 20), "pass-phase5-full-candidate-generation")


if __name__ == "__main__":
    unittest.main()
