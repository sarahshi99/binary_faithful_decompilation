from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import fixtures


class DecompileFaithfulnessFixturesTest(unittest.TestCase):
    def test_builtin_cases_have_expected_shape(self) -> None:
        cases = fixtures.builtin_cases()
        self.assertGreaterEqual(len(cases), 3)
        for case in cases:
            self.assertRegex(case.case_id, r"^[a-z0-9_]+$")
            self.assertIn("int", case.function_source)
            self.assertIn(case.function_name, case.function_source)
            self.assertGreaterEqual(len(case.tests), 3)
            for test in case.tests:
                self.assertIsInstance(test.args, tuple)
                self.assertIsInstance(test.expected, int)

    def test_render_translation_unit_wraps_function_and_harness(self) -> None:
        case = fixtures.builtin_cases()[0]
        rendered = fixtures.render_translation_unit(case, case.function_source)
        self.assertIn(case.function_source.strip(), rendered)
        self.assertIn("int main(void)", rendered)
        self.assertIn("return 0;", rendered)
        self.assertIn("return 100 +", rendered)

    def test_case_by_id_is_stable(self) -> None:
        first = fixtures.case_by_id("absdiff")
        second = fixtures.case_by_id("absdiff")
        self.assertEqual(first.case_id, second.case_id)
        self.assertEqual(first.function_source, second.function_source)


if __name__ == "__main__":
    unittest.main()
