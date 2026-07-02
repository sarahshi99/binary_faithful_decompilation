from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_dynamic_trace_v2_audit as audit


class DecompileFaithfulnessDynamicTraceV2Test(unittest.TestCase):
    def test_dynamic_distance_uses_domain_trace_inputs(self) -> None:
        trace_inputs = [dynamic_trace.TraceInput(args=(1, 2), bucket="positive_domain")]
        original_run = dynamic_trace.TraceRun(
            "gcd_positive",
            "original",
            True,
            0,
            (1,),
            "1\n",
            "",
            Path("original.c"),
            Path("original.exe"),
        )
        candidate_run = dynamic_trace.TraceRun(
            "gcd_positive",
            "candidate",
            True,
            0,
            (2,),
            "2\n",
            "",
            Path("candidate.c"),
            Path("candidate.exe"),
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = root / "gcd_positive__original__O0.function.c"
            candidate = root / "gcd_positive__candidate__O0.function.c"
            original.write_text("int gcd_positive(int a, int b) { return a; }\n", encoding="utf-8")
            candidate.write_text("int gcd_positive(int a, int b) { return b; }\n", encoding="utf-8")

            with mock.patch.object(audit.dynamic_trace, "generate_domain_trace_inputs") as gen:
                with mock.patch.object(audit.dynamic_trace, "run_trace") as run_trace:
                    gen.return_value = trace_inputs
                    run_trace.side_effect = [
                        original_run,
                        candidate_run,
                        original_run,
                        original_run,
                    ]

                    result = audit._dynamic_distance_for_paths(audit.SourcePaths(original, candidate))

        self.assertEqual(gen.call_count, 1)
        self.assertAlmostEqual(result["trace_domain_positive"], 1.0)
        self.assertAlmostEqual(result["trace_input_count"], 1.0)

    def test_aggregate_records_keeps_v2_domain_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "phase1h"
            candidates = root / "o0" / "candidates"
            candidates.mkdir(parents=True)
            (candidates / "gcd_positive__original__O0.function.c").write_text("", encoding="utf-8")
            (candidates / "gcd_positive__candidate__O0.function.c").write_text("", encoding="utf-8")
            (root / "o0" / "records.jsonl").write_text(
                '{"case_id":"gcd_positive","candidate_id":"candidate","label":"plausible_wrong",'
                '"mutation_type":"manual","slot_concentration":0.4}\n',
                encoding="utf-8",
            )

            records = audit._aggregate_records(
                [root],
                distance_fn=lambda _paths: {
                    "trace_input_count": 8.0,
                    "trace_mismatch_count": 4.0,
                    "trace_mismatch_rate": 0.5,
                    "trace_abs_error_mean": 1.0,
                    "trace_abs_error_max": 2.0,
                    "trace_sign_mismatch_rate": 0.0,
                    "trace_zero_mismatch_rate": 0.0,
                    "trace_boundary_mismatch_rate": 0.5,
                    "trace_total": 0.75,
                    "trace_domain_positive": 1.0,
                    "trace_domain_nonnegative": 1.0,
                    "trace_domain_filtered_count": 12.0,
                    "fixture_mismatch_rate": 1.0,
                    "fixture_behavior_passed": 0.0,
                },
            )

        self.assertAlmostEqual(records[0]["features"]["trace_domain_positive"], 1.0)
        self.assertAlmostEqual(records[0]["features"]["trace_domain_filtered_count"], 12.0)
        self.assertAlmostEqual(records[0]["features"]["min_slot"], 0.4)

    def test_v2_formulas_match_v1_formula_names(self) -> None:
        self.assertEqual(
            [formula.name for formula in audit._formulas()],
            [
                "trace_mismatch_rate",
                "trace_total",
                "trace_total_plus_min_slot_0.10",
                "trace_total_plus_min_slot_0.25",
                "min_slot",
            ],
        )

    def test_v3_boundary_inputs_keep_generic_zero_boundary(self) -> None:
        signum = dynamic_trace.generate_boundary_trace_inputs(
            audit.fixtures.case_by_id("signum"),
            include_fixture_tests=False,
        )
        is_power = dynamic_trace.generate_boundary_trace_inputs(
            audit.fixtures.case_by_id("is_power_of_two"),
            include_fixture_tests=False,
        )

        self.assertIn((0,), {trace_input.args for trace_input in signum})
        self.assertIn((0,), {trace_input.args for trace_input in is_power})
        self.assertTrue(
            all(
                trace_input.bucket == "v3_boundary"
                for trace_input in signum
                if trace_input.args in {(-1,), (0,), (1,)}
            )
        )

    def test_v3_boundary_inputs_do_not_replay_all_fixtures(self) -> None:
        case = audit.fixtures.case_by_id("signum")
        trace_inputs = dynamic_trace.generate_boundary_trace_inputs(
            case,
            include_fixture_tests=False,
        )
        args = {trace_input.args for trace_input in trace_inputs}

        self.assertIn((0,), args)
        self.assertNotIn((-5,), args)
        self.assertNotIn((9,), args)


if __name__ == "__main__":
    unittest.main()
