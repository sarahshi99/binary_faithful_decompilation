from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import analyze_phase2_results as analysis


class DecompileFaithfulnessPhase2ResultAnalysisTest(unittest.TestCase):
    def test_build_summary_counts_case_prompt_and_auc(self) -> None:
        records = [
            _record("absdiff", "a_faithful", "strict_rewrite", "faithful", 0.0),
            _record("absdiff", "a_wrong", "strict_bug", "plausible_wrong", 0.4),
            {
                "case_id": "absdiff",
                "candidate_id": "a_compile_fail",
                "label": "compile_fail",
                "compiled": False,
                "exit_code": 1,
                "compile_stderr": "error: expected expression",
                "metadata": {"prompt_id": "strict_bug"},
            },
        ]
        generations = [
            _generation("absdiff", "a_faithful", "strict_rewrite", "parsed_function"),
            _generation("absdiff", "a_wrong", "strict_bug", "parsed_function"),
            _generation("absdiff", "a_compile_fail", "strict_bug", "parsed_function"),
            _generation("absdiff", "a_parse_fail", "strict_bug", "parse_failed", "missing"),
        ]

        summary = analysis.build_summary(records, generations)

        self.assertEqual(summary["overall"]["generation_count"], 4)
        self.assertEqual(summary["overall"]["compile_pass_count"], 2)
        self.assertEqual(summary["overall"]["trace_pairwise_auc"], 1.0)
        self.assertEqual(summary["case_table"]["absdiff"]["compile_pass"], 2)
        self.assertTrue(summary["case_table"]["absdiff"]["paired"])
        self.assertEqual(summary["prompt_table"]["strict_bug"]["labels"]["plausible_wrong"], 1)
        self.assertEqual(
            summary["failure_analysis"]["compile_failure_categories"],
            {"syntax_or_compile_error": 1},
        )

    def test_compile_failure_category_timeout(self) -> None:
        record = {
            "case_id": "count_bits8",
            "candidate_id": "loop",
            "label": "compile_fail",
            "exit_code": 124,
            "compile_stderr": "command timed out after 10 seconds",
        }

        self.assertEqual(analysis._compile_failure_category(record), "timeout")


def _record(
    case_id: str,
    candidate_id: str,
    prompt_id: str,
    label: str,
    trace_total: float,
) -> dict:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "compiled": True,
        "exit_code": 0 if label == "faithful" else 100,
        "features": {
            "trace_total": trace_total,
            "trace_mismatch_rate": trace_total,
            "fixture_mismatch_rate": 0.0 if label == "faithful" else trace_total,
        },
        "metadata": {"prompt_id": prompt_id},
    }


def _generation(
    case_id: str,
    candidate_id: str,
    prompt_id: str,
    cleaning_status: str,
    cleaning_reason: str = "",
) -> dict:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "prompt_id": prompt_id,
        "cleaning_status": cleaning_status,
        "cleaning_reason": cleaning_reason,
    }


if __name__ == "__main__":
    unittest.main()
