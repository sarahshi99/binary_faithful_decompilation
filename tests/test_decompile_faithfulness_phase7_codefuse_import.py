from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_phase7_codefuse_import as codefuse


class Phase7CodeFuseImportTest(unittest.TestCase):
    def test_extract_scalar_functions_filters_pointer_and_float(self) -> None:
        source = """
int ok_add(int a, int b) {
    return a + b;
}

int pointer_bad(int *p) {
    return *p;
}

float float_bad(float x) {
    return x + 1.0f;
}

int calls_bad(int x) {
    return helper(x);
}
"""
        functions = codefuse.extract_scalar_functions(source, "demo.c")
        self.assertEqual([item.name for item in functions], ["ok_add"])
        self.assertEqual(functions[0].arity, 2)

    def test_extract_scalar_functions_defers_state_cpp_and_duplicate_cases(self) -> None:
        source = """
int ok_add(int a, int b) {
    return a + b;
}

int static_local(int reset) {
    static int counter = 0;
    counter += reset;
    return counter;
}

int tls_access(int val) {
    return val * 2;
}

int cpp_exception(int x) {
    if (x < 0) return -1;
    return x;
}

int mips_func(int a) {
    return a + 1;
}

int mips_func(int a) {
    return a + 2;
}
"""
        functions = codefuse.extract_scalar_functions(source, "demo.c")
        self.assertEqual([item.name for item in functions], ["ok_add", "mips_func"])

    def test_fixture_args_for_arity_are_positive_and_stable(self) -> None:
        self.assertEqual(
            codefuse.fixture_args_for_arity(2),
            ((1, 2), (5, 3), (8, 4)),
        )
        self.assertEqual(codefuse.fixture_args_for_arity(0), ((),))

    def test_case_id_sanitizes_source_and_function_name(self) -> None:
        self.assertEqual(
            codefuse.case_id_for_function("5-23.c", "is okay?"),
            "codefuse_5_23_is_okay",
        )

    def test_function_name_is_deferred_for_out_of_scope_semantics(self) -> None:
        self.assertTrue(codefuse.function_name_is_deferred("tls_access"))
        self.assertTrue(codefuse.function_name_is_deferred("call_thiscall"))
        self.assertTrue(codefuse.function_name_is_deferred("cpp_exception"))
        self.assertFalse(codefuse.function_name_is_deferred("loop_for_fixed"))

    def test_import_verdict_distinguishes_scale(self) -> None:
        self.assertEqual(
            codefuse.import_verdict(imported=50, oracle_ready=30),
            "pass-phase7-codefuse-import",
        )
        self.assertEqual(
            codefuse.import_verdict(imported=10, oracle_ready=10),
            "needs-more-codefuse-functions",
        )
        self.assertEqual(
            codefuse.import_verdict(imported=50, oracle_ready=0),
            "blocked-codefuse-oracle-preflight",
        )


if __name__ == "__main__":
    unittest.main()
