from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import submission_evidence_corrections as sec


REPO_ROOT = Path(__file__).resolve().parents[3]


class SubmissionEvidenceCorrectionsTest(unittest.TestCase):
    def test_provenance_category_mapping_is_orthogonal(self) -> None:
        ghidra_stress = sec.classify_candidate_provenance(
            "ghidra",
            {"mutation_type": "phase6_fixture_ifchain_semantic_drift"},
            {},
        )
        self.assertEqual(ghidra_stress["base_candidate_origin"], "raw_ghidra_output")
        self.assertEqual(ghidra_stress["compile_processing"], "syntax_normalization")
        self.assertEqual(ghidra_stress["semantic_transformation"], "fixture_overfit_construction")
        self.assertEqual(ghidra_stress["evidence_stratum"], "controlled_stress_candidate")

        ghidra_control = sec.classify_candidate_provenance(
            "ghidra",
            {"mutation_type": "phase6_behavior_preserving_noop_guard"},
            {},
        )
        self.assertEqual(ghidra_control["semantic_transformation"], "behavior_preserving_noop")
        self.assertEqual(ghidra_control["evidence_stratum"], "behavior_preserving_control")

        llm = sec.classify_candidate_provenance(
            "llm_public",
            {"metadata": {"prompt_id": "strict_rewrite"}},
            {},
        )
        self.assertEqual(llm["base_candidate_origin"], "raw_llm_generation")
        self.assertEqual(llm["compile_processing"], "function_extraction")
        self.assertEqual(llm["semantic_transformation"], "llm_rewrite")
        self.assertEqual(llm["evidence_stratum"], "natural_llm_output")

    def test_legacy_label_to_paper_label_mapping(self) -> None:
        self.assertEqual(
            sec.paper_label_for_source_record(
                {"compiled": True, "label": "plausible_wrong", "diagnostics": {"primary_exit_code": 0}}
            ),
            "semantic_wrong",
        )
        self.assertEqual(
            sec.paper_label_for_source_record(
                {"compiled": True, "label": "faithful", "diagnostics": {"primary_exit_code": 0}}
            ),
            "no_mismatch_under_labeling_protocol",
        )
        self.assertEqual(
            sec.paper_label_for_source_record(
                {"compiled": False, "label": "compile_fail", "diagnostics": {"primary_exit_code": 1}}
            ),
            "non_evaluable",
        )
        self.assertEqual(
            sec.paper_label_for_source_record(
                {"compiled": True, "label": "plausible_wrong", "diagnostics": {"primary_exit_code": 124}}
            ),
            "non_evaluable",
        )

    def test_primary_membership_reconstruction_matches_phase18_tables(self) -> None:
        rows = _read_csv(REPO_ROOT / "results/decompile_faithfulness/primary_evaluation_reconciliation.csv")
        by_dataset = {row["dataset"]: row for row in rows}
        public = by_dataset["phase7c2_static_hard_public"]
        self.assertEqual(int(public["generated_records"]), 524)
        self.assertEqual(int(public["compile_ready"]), 503)
        self.assertEqual(int(public["candidates_in_current_full_result_table"]), 478)
        self.assertEqual(int(public["excluded_no_generated_final_method_inputs"]), 25)

        llm = by_dataset["phase7e_llm_public_full_topup"]
        self.assertEqual(int(llm["attempts"]), 224)
        self.assertEqual(int(llm["generated_records"]), 195)
        self.assertEqual(int(llm["compile_ready"]), 143)
        self.assertEqual(int(llm["candidates_in_current_full_result_table"]), 136)

        ghidra = by_dataset["phase6r_ghidra_full"]
        self.assertEqual(int(ghidra["generated_records"]), 228)
        self.assertEqual(int(ghidra["compile_ready"]), 166)
        self.assertEqual(int(ghidra["candidates_in_current_full_result_table"]), 166)

    def test_runtime_failures_do_not_enter_semantic_denominators(self) -> None:
        rows = _read_csv(REPO_ROOT / "results/decompile_faithfulness/primary_evaluation_reconciliation.csv")
        public = {row["dataset"]: row for row in rows}["phase7c2_static_hard_public"]
        self.assertEqual(int(public["wrong_candidates_in_result_table"]), 258)
        self.assertEqual(int(public["no_mismatch_candidates_in_result_table"]), 211)
        self.assertEqual(int(public["non_evaluable_candidates_in_result_table"]), 9)
        self.assertEqual(int(public["primary_evaluable_candidates"]), 469)

    def test_overlap_summary_uses_primary_semantic_wrong_denominator(self) -> None:
        rows = _read_csv(REPO_ROOT / "results/decompile_faithfulness/oracle_overlap_summary_v2.csv")
        by_scope = {
            row["group"]: row for row in rows
            if row["group_type"] == "scope"
        }
        self.assertEqual(int(by_scope["all_compiled_wrong_label_records"]["wrong_candidate_denominator"]), 377)
        self.assertEqual(int(by_scope["current_full_result_tables"]["wrong_candidate_denominator"]), 368)
        self.assertEqual(
            int(by_scope["current_full_result_tables"]["candidates_with_reconstructed_exact_witness_overlap_under_current_artifact"]),
            354,
        )
        self.assertEqual(int(by_scope["primary_paired_cases"]["wrong_candidate_denominator"]), 340)

    def test_method_freeze_hash_integrity(self) -> None:
        integrity = json.loads(
            (REPO_ROOT / "analysis/decompile_faithfulness/method_freeze_integrity.json").read_text(encoding="utf-8")
        )
        self.assertEqual(integrity["method_freeze_commit"], sec.METHOD_FREEZE_COMMIT)
        self.assertTrue(integrity["summary"]["all_method_files_current_match_freeze"])
        self.assertEqual(integrity["summary"]["method_file_count"], 9)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
