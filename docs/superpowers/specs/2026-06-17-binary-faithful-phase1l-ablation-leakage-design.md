# Binary-Faithful Decompilation Phase 1L Ablation / Leakage Audit Design

> **Scope guard:** Work only under `/home/shx/projects/binary_faithful_decompilation`. Do not use subagents, Task/Spawn, reviewer subagents, `tool_search`, multi-agent discovery, GPU jobs, network, or dependency installation.

## Context

Phase 1K-v2 passed the localized-bug gate:

- v1 mixed-domain dynamic trace LOCO AUC: `0.8750`
- v2 fixture-domain-aware dynamic trace LOCO AUC: `0.9531`
- `gcd_positive`: `0.5000 -> 1.0000`
- `fixture_collapse`: `False`

Before treating v2 as a paper-worthy result, Phase 1L must show that the gain is not:

- merely the existing fixture-test oracle;
- label leakage;
- candidate-output leakage;
- a hand-written `gcd_positive` patch;
- static-only `min_slot` wearing a dynamic-trace label.

## Design Decision

Phase 1L is a **read-only ablation over existing Phase 1K records**. It should not recompile, rerun trace harnesses, use GPU, install dependencies, or change candidate files.

Input files:

- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl`
- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl`

Compare these variants:

1. `mixed_domain_v1_trace_mismatch`
   - source: v1 records
   - score: `trace_mismatch_rate`

2. `domain_aware_v2_trace_mismatch`
   - source: v2 records
   - score: `trace_mismatch_rate`

3. `fixture_only_oracle`
   - source: v2 records
   - score: `fixture_mismatch_rate`

4. `static_only_min_slot`
   - source: v2 records
   - score: `min_slot`

5. Optional diagnostic: `domain_aware_v2_trace_total`
   - source: v2 records
   - score: `trace_total`

Use the same within-case pairwise AUC definition as Phase 1K. Higher scores should mean "more suspicious / more likely wrong".

## Leakage Audit Checks

The report must explicitly state:

- domain inference source: fixture argument values only;
- no label use in domain inference;
- no candidate output use in domain inference;
- no candidate id use in domain inference;
- no per-case label-tuned formula selection for v2 primary result;
- fixture-only oracle is reported as a comparator, not as the method.

Use record features to check:

- whether v2's best signal equals fixture-only behavior for every candidate;
- whether v2 improves over v1 specifically on `gcd_positive`;
- whether static-only `min_slot` is meaningfully weaker than v2.

## Success Gate

Pass if:

- `domain_aware_v2_trace_mismatch` overall pairwise AUC `>= 0.95`;
- `domain_aware_v2_trace_mismatch` `gcd_positive` AUC `>= 1.0`;
- v2 is not identical to fixture-only over all records;
- v2 beats `static_only_min_slot` by at least `0.10` overall AUC;
- leakage audit verdict is `no-label-or-output-leakage-found`.

## Outputs

Create:

- `analysis/decompile_faithfulness/run_phase1l_ablation_audit.py`
- `tests/test_decompile_faithfulness_phase1l_ablation.py`
- `docs/paper_agent/decompile_faithfulness_phase1l_ablation.json`
- `docs/paper_agent/decompile_faithfulness_phase1l_ablation.md`
- `docs/paper_agent/decompile_faithfulness_phase1l_ablation.zh.md`

Modify:

- `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md`

## Spec Self-Review

- Placeholder scan: no TODO/TBD placeholders remain.
- Scope check: read-only over existing records; CPU-only; no GPU/network/dependencies/subagents.
- Leakage check: the method-side domain inference is defined as fixture-argument-only.
- Paper-boundary check: success supports source-known localized semantic bug auditing, not general real-project transfer.
