from __future__ import annotations

import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest import mock

from analysis.decompile_faithfulness import dynamic_trace, fixtures


class DecompileFaithfulnessDynamicTraceTest(unittest.TestCase):
    def test_generated_trace_inputs_are_deterministic_and_exclude_fixture_tests(self) -> None:
        case = fixtures.case_by_id("signum")

        first = dynamic_trace.generate_trace_inputs(case, max_inputs=32, include_fixture_tests=False)
        second = dynamic_trace.generate_trace_inputs(case, max_inputs=32, include_fixture_tests=False)
        fixture_args = {test.args for test in case.tests}

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 32)
        self.assertTrue(first)
        self.assertTrue(all(trace_input.args not in fixture_args for trace_input in first))
        self.assertEqual(first, sorted(first, key=lambda item: item.args))

    def test_generated_trace_inputs_can_include_fixture_tests_for_diagnostics(self) -> None:
        case = fixtures.case_by_id("clamp8")

        inputs = dynamic_trace.generate_trace_inputs(case, max_inputs=64, include_fixture_tests=True)
        input_args = {trace_input.args for trace_input in inputs}

        self.assertTrue({test.args for test in case.tests}.issubset(input_args))

    def test_domain_trace_inputs_keep_gcd_positive_inside_positive_domain(self) -> None:
        case = fixtures.case_by_id("gcd_positive")

        domain = dynamic_trace.infer_trace_domain(case)
        inputs = dynamic_trace.generate_domain_trace_inputs(
            case,
            max_inputs=128,
            include_fixture_tests=False,
        )
        fixture_args = {test.args for test in case.tests}

        self.assertTrue(domain.all_positive)
        self.assertTrue(inputs)
        self.assertTrue(all(all(value > 0 for value in trace_input.args) for trace_input in inputs))
        self.assertTrue(all(trace_input.args not in fixture_args for trace_input in inputs))

    def test_domain_trace_inputs_keep_signed_cases_wide(self) -> None:
        case = fixtures.case_by_id("signum")

        domain = dynamic_trace.infer_trace_domain(case)
        inputs = dynamic_trace.generate_domain_trace_inputs(
            case,
            max_inputs=64,
            include_fixture_tests=True,
        )
        values = {trace_input.args[0] for trace_input in inputs}

        self.assertFalse(domain.all_positive)
        self.assertTrue(domain.has_zero)
        self.assertTrue(any(value < 0 for value in values))
        self.assertIn(0, values)
        self.assertTrue(any(value > 0 for value in values))

    def test_render_trace_harness_prints_one_output_per_input(self) -> None:
        case = fixtures.case_by_id("absdiff")
        inputs = [
            dynamic_trace.TraceInput(args=(7, 3), bucket="fixture"),
            dynamic_trace.TraceInput(args=(3, 7), bucket="fixture"),
        ]

        harness = dynamic_trace.render_trace_harness(case, case.function_source, inputs)

        self.assertIn("#include <stdio.h>", harness)
        self.assertIn("int absdiff(int a, int b)", harness)
        self.assertIn('printf("%d\\n", absdiff(7, 3));', harness)
        self.assertIn('printf("%d\\n", absdiff(3, 7));', harness)

    def test_parse_trace_stdout_rejects_wrong_output_count(self) -> None:
        with self.assertRaises(ValueError):
            dynamic_trace.parse_trace_stdout("1\n2\n", expected_count=3)

    def test_run_trace_executes_generated_harness(self) -> None:
        case = fixtures.case_by_id("absdiff")
        inputs = [
            dynamic_trace.TraceInput(args=(7, 3), bucket="fixture"),
            dynamic_trace.TraceInput(args=(3, 7), bucket="fixture"),
            dynamic_trace.TraceInput(args=(5, 5), bucket="fixture"),
        ]

        with tempfile.TemporaryDirectory() as td:
            run = dynamic_trace.run_trace(
                case=case,
                candidate_id="original",
                function_source=case.function_source,
                inputs=inputs,
                output_dir=Path(td),
                opt_level="O0",
            )

        self.assertTrue(run.compiled, run.stderr)
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.outputs, (4, 4, 0))

    def test_trace_distance_scores_output_mismatches_without_labels(self) -> None:
        inputs = [
            dynamic_trace.TraceInput(args=(-1,), bucket="negative"),
            dynamic_trace.TraceInput(args=(0,), bucket="zero"),
            dynamic_trace.TraceInput(args=(1,), bucket="positive"),
            dynamic_trace.TraceInput(args=(128,), bucket="boundary"),
        ]

        distance = dynamic_trace.trace_distance(
            inputs=inputs,
            original_outputs=(-1, 0, 1, 1),
            candidate_outputs=(1, 0, -1, 1),
        )

        self.assertAlmostEqual(distance.components["trace_input_count"], 4.0)
        self.assertAlmostEqual(distance.components["trace_mismatch_count"], 2.0)
        self.assertAlmostEqual(distance.components["trace_mismatch_rate"], 0.5)
        self.assertGreater(distance.components["trace_sign_mismatch_rate"], 0.0)
        self.assertGreater(distance.components["trace_total"], 0.5)

    def test_run_trace_records_timeout_as_failed_run(self) -> None:
        case = fixtures.case_by_id("absdiff")
        inputs = [dynamic_trace.TraceInput(args=(7, 3), bucket="fixture")]
        compile_ok = subprocess.CompletedProcess(["gcc"], 0, "", "")

        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(dynamic_trace.ccompile, "run_command") as run_command:
                run_command.side_effect = [
                    compile_ok,
                    subprocess.TimeoutExpired(cmd=["trace.exe"], timeout=10),
                ]

                run = dynamic_trace.run_trace(
                    case=case,
                    candidate_id="timeout",
                    function_source=case.function_source,
                    inputs=inputs,
                    output_dir=Path(td),
                    opt_level="O0",
                )

        self.assertTrue(run.compiled)
        self.assertEqual(run.exit_code, 124)
        self.assertEqual(run.outputs, ())
        self.assertIn("timed out", run.stderr)


if __name__ == "__main__":
    unittest.main()
