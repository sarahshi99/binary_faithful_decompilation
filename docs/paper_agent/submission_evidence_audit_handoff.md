# Submission Evidence Audit Handoff

## Git

- Branch: `phase1a-audit`
- HEAD commit: `06dda89912103b94fc065d6f073581a7811154b1`
- Freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`

## Commands Executed

- `git status --short --branch`
- `git rev-parse HEAD`
- `rg ...` code/data discovery commands
- `python -m analysis.decompile_faithfulness.submission_evidence_audit`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze`
- `python -m json.tool` over generated JSON outputs
- `git diff --check`

## Tests Passed

Probe-order regression tests snapshot the exact ordered prefix for single integer, single char, mixed integer/char, duplicate source literals, empty source-literal queues, and one exhausted interleave queue.

## Candidate Provenance

- Total candidate records: `947`
- By dataset: `{'phase6r_ghidra_full': 228, 'phase7c2_static_hard_public': 524, 'phase7e_llm_public_full_topup': 195}`
- Wrong labels: `{'phase6r_ghidra_full': 74, 'phase7c2_static_hard_public': 267, 'phase7e_llm_public_full_topup': 36}`
- 100% of candidate records have stable dataset/case/candidate identifiers.

## Missing Metadata

Unknown values are explicit rather than inferred. Nonzero missing-field counts:

```json
{
  "architecture": 941,
  "argument_types": 30,
  "compiler": 228,
  "producing_tool_or_model_version": 524,
  "sanitizer_status": 947
}
```

## Oracle Overlap

- Exact witness overlap: `354` / `377` wrong labels = `0.9390`.
- Exact overlap by dataset: `{"phase6r_ghidra_full": 0.918918918918919, "phase7c2_static_hard_public": 0.9363295880149812, "phase7e_llm_public_full_topup": 1.0}`
- Probe-family overlap rates by dataset:

```json
{
  "phase6r_ghidra_full": {
    "controlled_construction_records": 1.0,
    "exact_fixtures": 0.0,
    "exhaustive_enumeration": 0.0,
    "fixture_plus_minus_1": 0.972972972972973,
    "fuzzing": 0.0,
    "generic_0_1_values": 0.7432432432432432,
    "generic_hard_input_cartesian_products": 1.0,
    "legacy_ascii_anchors": 0.17567567567567569,
    "operator_character_lists": 0.0,
    "random_inputs": 0.0,
    "source_literals": 0.0,
    "symbolic_concolic_inputs": 0.0
  },
  "phase7c2_static_hard_public": {
    "controlled_construction_records": 1.0,
    "exact_fixtures": 0.0,
    "exhaustive_enumeration": 0.0,
    "fixture_plus_minus_1": 0.9700374531835206,
    "fuzzing": 0.0,
    "generic_0_1_values": 0.3146067415730337,
    "generic_hard_input_cartesian_products": 1.0,
    "legacy_ascii_anchors": 0.03745318352059925,
    "operator_character_lists": 0.0,
    "random_inputs": 0.0,
    "source_literals": 0.0,
    "symbolic_concolic_inputs": 0.0
  },
  "phase7e_llm_public_full_topup": {
    "controlled_construction_records": 0.0,
    "exact_fixtures": 0.0,
    "exhaustive_enumeration": 0.0,
    "fixture_plus_minus_1": 1.0,
    "fuzzing": 0.0,
    "generic_0_1_values": 0.19444444444444445,
    "generic_hard_input_cartesian_products": 1.0,
    "legacy_ascii_anchors": 0.05555555555555555,
    "operator_character_lists": 0.0,
    "random_inputs": 0.0,
    "source_literals": 0.0,
    "symbolic_concolic_inputs": 0.0
  }
}
```

Generator-family overlap is not claimed as leakage by itself. The audit distinguishes exact witness reuse, shared input family, and unresolved/full independence.

## Development Coupling

Phase 16 inspected Ghidra `char_boundary` and `multi_arg` misses. Phase 17 explicitly tested a generic operator-character fix after seeing `ta_infix_precedence_two`; Phase 18 introduced source-literal char interleaving to recover that case without regressing broader coverage. Therefore current results on Ghidra char-boundary/multi-arg, and any aggregate tables containing those same cases, are pre-freeze/development evidence.

Development-coupled cases/families:

- `ta_infix_precedence_two`
- Ghidra `char_boundary`
- Ghidra `multi_arg`
- Phase 17 broad regressions on public/static and LLM-public under `operator_char_class_first`

## Dataset Flow

```json
[
  {
    "candidate_attempts": 524,
    "compile_ready_candidates": 503,
    "dataset": "phase7c2_static_hard_public",
    "executable_candidates": 494,
    "faithful_class_candidates": 236,
    "final_paired_cases": 50,
    "generated_candidates": 524,
    "oracle_adjudicable_candidates": 503,
    "project_names": "CodeFuse-DeBench",
    "projects": 1,
    "source_functions": 56,
    "supported_signatures": 56,
    "wrong_candidates": 267
  },
  {
    "candidate_attempts": 224,
    "compile_ready_candidates": 143,
    "dataset": "phase7e_llm_public_full_topup",
    "executable_candidates": 143,
    "faithful_class_candidates": 107,
    "final_paired_cases": 24,
    "generated_candidates": 195,
    "oracle_adjudicable_candidates": 143,
    "project_names": "CodeFuse-DeBench",
    "projects": 1,
    "source_functions": 56,
    "supported_signatures": 56,
    "wrong_candidates": 36
  },
  {
    "candidate_attempts": 228,
    "compile_ready_candidates": 166,
    "dataset": "phase6r_ghidra_full",
    "executable_candidates": 166,
    "faithful_class_candidates": 92,
    "final_paired_cases": 26,
    "generated_candidates": 228,
    "oracle_adjudicable_candidates": 166,
    "project_names": "c_algorithms;thealgorithms_c",
    "projects": 2,
    "source_functions": 38,
    "supported_signatures": 38,
    "wrong_candidates": 74
  }
]
```

## Proposed Unseen Projects

`libtommath`, `cJSON`, `uthash` examples, `musl`, `zlib`, `mbedtls`, `sqlite` utility functions, and small project-disjoint C benchmark suites are proposed in `docs/paper_agent/frozen_holdout_preregistration.md`.

## Unresolved Risks

- Architecture, sanitizer status, and some compiler versions are not stored in candidate records.
- Exact label witnesses were reconstructed from current code and candidate sources; historical trace files do not store per-input label witnesses in records.
- Existing Phase 19 readiness markdown appears to retain a Phase 14 heading, so historical doc naming should be treated carefully.
- LLM-public provenance covers candidate records; raw parse-failed generations are counted in flow attempts but do not have full candidate rows.

## Independence Verdict

The current three perfect-result tables should not be described as fully independent test evidence. They are valid frozen, source-known, pre-freeze/development evidence with transparent provenance and overlap accounting. A project-disjoint prospective holdout is required for independent test evidence.
