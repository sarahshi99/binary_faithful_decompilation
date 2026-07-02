from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase18_source_literal_char_policy as phase18


class Phase18SourceLiteralCharPolicyTest(unittest.TestCase):
    def test_phase18_verdict(self) -> None:
        self.assertEqual(
            phase18.phase18_verdict({"a": True, "b": True}),
            "pass-phase18-source-literal-char-policy",
        )
        self.assertEqual(
            phase18.phase18_verdict({"a": True, "b": False}),
            "partial-phase18-source-literal-char-policy",
        )
        self.assertEqual(
            phase18.phase18_verdict({"a": False, "b": False}),
            "fail-phase18-source-literal-char-policy",
        )


if __name__ == "__main__":
    unittest.main()
