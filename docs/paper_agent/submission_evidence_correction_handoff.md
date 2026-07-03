# Submission Evidence Correction Handoff

## Git

- Branch: `phase1b-evidence-corrections`
- Method freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`
- Evidence audit commit: `c974129c231ff1274e5af714fdc9f01dec927019`
- Correction implementation commit: `d4b50b05396eaa68a9dea6cd2c406e201c35c1f2`

## Commands Executed

- `git checkout -b phase1b-evidence-corrections`
- `rg`, `sed`, and JSON inspection commands over Phase18/20 artifacts
- `python -m analysis.decompile_faithfulness.submission_evidence_corrections`
- focused unittest commands listed in the final terminal transcript
- JSON validation via `python -m json.tool`
- `git diff --check`

## Method Integrity

- Method hashes unchanged: `True`
- Method-affecting files checked: `9`
- Unchanged files: `9`

## Corrected Provenance Counts

- Ghidra semantic wrong as natural raw/minimally processed decompiler errors: `0`
- Ghidra-derived controlled stress semantic wrong: `74`
- LLM semantic wrong natural generations: `36`
- Candidates with documented actual semantic repair: `0`
- Original-source or behavior-preserving comparison controls: `264`

## Primary Evaluation Reconciliation

```json
[
  {
    "attempts": 524,
    "candidates_in_current_full_result_table": 478,
    "candidates_in_paired_cases": 466,
    "compile_ready": 503,
    "count_difference_explanation": "524 generated records; 21 failed compile pre-primary; 25 compile-ready records from zero-input unsupported signatures were not rerun; 478 records entered the current full result table; 9 primary budget rows became non_evaluable runtime failures, leaving 469 evaluable.",
    "dataset": "phase7c2_static_hard_public",
    "excluded_candidates": 46,
    "excluded_missing_case_manifest": 0,
    "excluded_no_generated_final_method_inputs": 25,
    "excluded_not_compile_ready": 21,
    "excluded_other": 0,
    "exclusion_reasons_json": "{\"no_generated_final_method_inputs\": 25, \"not_compile_ready\": 21}",
    "executable": 494,
    "generated_records": 524,
    "no_mismatch_candidates_in_result_table": 211,
    "non_evaluable_candidates_in_result_table": 9,
    "oracle_adjudicable": 494,
    "paired_cases": 50,
    "phase18_candidate_count_metric": 478,
    "phase18_compile_pass_count_metric": 469,
    "phase18_eval_count_metric": 469,
    "phase18_wrong_count_metric": 258,
    "primary_evaluable_candidates": 469,
    "wrong_candidates_in_result_table": 258
  },
  {
    "attempts": 224,
    "candidates_in_current_full_result_table": 136,
    "candidates_in_paired_cases": 79,
    "compile_ready": 143,
    "count_difference_explanation": "224 raw generations produced 195 parsed candidate records; 52 failed compile; 7 compile-ready records from zero-input unsupported signatures were not rerun; 136 records entered and completed primary evaluation.",
    "dataset": "phase7e_llm_public_full_topup",
    "excluded_candidates": 59,
    "excluded_missing_case_manifest": 0,
    "excluded_no_generated_final_method_inputs": 7,
    "excluded_not_compile_ready": 52,
    "excluded_other": 0,
    "exclusion_reasons_json": "{\"no_generated_final_method_inputs\": 7, \"not_compile_ready\": 52}",
    "executable": 143,
    "generated_records": 195,
    "no_mismatch_candidates_in_result_table": 100,
    "non_evaluable_candidates_in_result_table": 0,
    "oracle_adjudicable": 143,
    "paired_cases": 24,
    "phase18_candidate_count_metric": 136,
    "phase18_compile_pass_count_metric": 136,
    "phase18_eval_count_metric": 136,
    "phase18_wrong_count_metric": 36,
    "primary_evaluable_candidates": 136,
    "wrong_candidates_in_result_table": 36
  },
  {
    "attempts": 228,
    "candidates_in_current_full_result_table": 166,
    "candidates_in_paired_cases": 144,
    "compile_ready": 166,
    "count_difference_explanation": "228 Ghidra-derived records; 62 did not become compile-ready normalized C; all 166 compile-ready records entered and completed primary evaluation.",
    "dataset": "phase6r_ghidra_full",
    "excluded_candidates": 62,
    "excluded_missing_case_manifest": 0,
    "excluded_no_generated_final_method_inputs": 0,
    "excluded_not_compile_ready": 62,
    "excluded_other": 0,
    "exclusion_reasons_json": "{\"not_compile_ready\": 62}",
    "executable": 166,
    "generated_records": 228,
    "no_mismatch_candidates_in_result_table": 92,
    "non_evaluable_candidates_in_result_table": 0,
    "oracle_adjudicable": 166,
    "paired_cases": 26,
    "phase18_candidate_count_metric": 166,
    "phase18_compile_pass_count_metric": 166,
    "phase18_eval_count_metric": 166,
    "phase18_wrong_count_metric": 74,
    "primary_evaluable_candidates": 166,
    "wrong_candidates_in_result_table": 74
  }
]
```

## Current-Table Reconstructed Overlap

The current-table-specific rate is reported as reconstructed exact witness overlap under the current artifact.

```json
{
  "all_compiled_wrong_label_records": {
    "candidates_with_reconstructed_exact_witness_overlap_under_current_artifact": 354,
    "group": "all_compiled_wrong_label_records",
    "group_type": "scope",
    "historical_exact_witness_reuse": 0,
    "no_demonstrated_overlap": 0,
    "only_probe_family_overlap": 23,
    "overlap_rate": 0.9389920424403183,
    "unresolved_reconstruction_count": 0,
    "wrong_candidate_denominator": 377
  },
  "controlled_stress_candidates_only": {
    "candidates_with_reconstructed_exact_witness_overlap_under_current_artifact": 318,
    "group": "controlled_stress_candidates_only",
    "group_type": "scope",
    "historical_exact_witness_reuse": 0,
    "no_demonstrated_overlap": 0,
    "only_probe_family_overlap": 14,
    "overlap_rate": 0.9578313253012049,
    "unresolved_reconstruction_count": 0,
    "wrong_candidate_denominator": 332
  },
  "current_full_result_tables": {
    "candidates_with_reconstructed_exact_witness_overlap_under_current_artifact": 354,
    "group": "current_full_result_tables",
    "group_type": "scope",
    "historical_exact_witness_reuse": 0,
    "no_demonstrated_overlap": 0,
    "only_probe_family_overlap": 14,
    "overlap_rate": 0.9619565217391305,
    "unresolved_reconstruction_count": 0,
    "wrong_candidate_denominator": 368
  },
  "natural_tool_or_llm_outputs_only": {
    "candidates_with_reconstructed_exact_witness_overlap_under_current_artifact": 36,
    "group": "natural_tool_or_llm_outputs_only",
    "group_type": "scope",
    "historical_exact_witness_reuse": 0,
    "no_demonstrated_overlap": 0,
    "only_probe_family_overlap": 0,
    "overlap_rate": 1.0,
    "unresolved_reconstruction_count": 0,
    "wrong_candidate_denominator": 36
  },
  "primary_paired_cases": {
    "candidates_with_reconstructed_exact_witness_overlap_under_current_artifact": 326,
    "group": "primary_paired_cases",
    "group_type": "scope",
    "historical_exact_witness_reuse": 0,
    "no_demonstrated_overlap": 0,
    "only_probe_family_overlap": 14,
    "overlap_rate": 0.9588235294117647,
    "unresolved_reconstruction_count": 0,
    "wrong_candidate_denominator": 340
  }
}
```

## Remaining Unknown Metadata

```json
{
  "phase6r_ghidra_full": [
    "exact GCC version",
    "host architecture unless recovered from object metadata",
    "sanitizer runtime status per candidate"
  ],
  "phase7c2_static_hard_public": [
    "exact GCC version",
    "host CPU model",
    "sanitizer runtime status per candidate"
  ],
  "phase7e_llm_public_full_topup": [
    "exact model checkpoint hash in local model path",
    "exact GPU model per run",
    "exact GCC version",
    "sanitizer runtime status per candidate"
  ]
}
```

## Development Coupling

The current Public, LLM-public, and Ghidra tables remain pre-freeze/development evidence. Ghidra `char_boundary`/`multi_arg` misses and `ta_infix_precedence_two` were inspected before Phase18 and directly motivated `source_literal_char_interleave`.

## Prospective Holdout

The preregistration is corrected and ready for acquisition-and-sealing review. The final holdout auditor has not been run and must not be run until a sealed holdout manifest is committed and reviewed.

## Independence Verdict

The current three perfect-result tables cannot be described as independent test evidence. They can be described as frozen pre-freeze/development evidence with corrected provenance, label semantics, and overlap denominators.
