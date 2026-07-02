# Binary-Faithful Decompilation Phase 1K Dynamic Trace v2 Design

> **Scope guard:** Work only under `/home/shx/projects/binary_faithful_decompilation`. Do not use subagents, Task/Spawn, reviewer subagents, `tool_search`, multi-agent discovery, GPU jobs, network, or dependency installation.

## Context

Phase 1K Route A produced the first strong semantic signal after the static-feature failures:

- Leave-one-case-out AUC: `0.8750`
- Fixture collapse: `False`
- Hard cases: `signum=0.7500`, `gcd_positive=0.5000`, `max3=1.0000`, `sum_to_n=1.0000`

The remaining blocker is `gcd_positive`. Inspection shows that v1 generated negative and zero-valued inputs for a case whose fixtures and name define a positive-integer domain. Those inputs are outside the intended source-known contract. They incorrectly punish faithful subtraction-style gcd rewrites that are equivalent for positive inputs but may timeout or differ for zero/negative inputs.

## Design Decision

Dynamic Trace v2 should add **domain-aware generated inputs** inferred only from source-known fixture tests and case metadata, without reading labels or candidate behavior.

Do not replace the Phase 1K v1 report. v2 should produce separate output files so v1 remains an audit trail.

## Input Domain Policy

For every case, infer simple per-argument domain facts from fixture tests:

- `all_positive`: every observed fixture value for every argument is `> 0`.
- `all_nonnegative`: every observed fixture value for every argument is `>= 0`.
- `has_negative`, `has_zero`, `has_positive`.

Use those facts to filter the generated pool:

- If `all_positive`, primary generated inputs must use strictly positive values only.
- Else if `all_nonnegative`, primary generated inputs must use nonnegative values only.
- Else keep the v1 mixed signed pool.

This is intentionally conservative. It does not inspect candidate labels, candidate source, or candidate output. It uses only source-known fixture-domain evidence.

For `gcd_positive`, the fixture-domain policy yields strictly positive pairs and should stop penalizing faithful rewrites for undefined/out-of-domain behavior.

## v2 Feature Policy

Reuse the v1 trace distance components:

- `trace_input_count`
- `trace_mismatch_count`
- `trace_mismatch_rate`
- `trace_abs_error_mean`
- `trace_abs_error_max`
- `trace_sign_mismatch_rate`
- `trace_zero_mismatch_rate`
- `trace_boundary_mismatch_rate`
- `trace_total`

Add domain diagnostics:

- `trace_domain_positive`
- `trace_domain_nonnegative`
- `trace_domain_filtered_count`

Continue reporting fixture diagnostics separately:

- `fixture_mismatch_rate`
- `fixture_behavior_passed`

## Candidate Formulas

Keep formulas simple and compatible with v1:

- `trace_mismatch_rate`
- `trace_total`
- `trace_total_plus_min_slot_0.10`
- `trace_total_plus_min_slot_0.25`
- `min_slot`

Do not add a case-specific formula for gcd. The expected gain should come from better input-domain construction, not a hand-tuned scorer.

## Success Gate

Dynamic Trace v2 passes if:

- overall LOCO AUC `>= 0.8750`;
- `gcd_positive` held-out AUC `> 0.5000`;
- `fixture_collapse` remains `False`;
- no GPU, network, symbolic dependency install, or subagent was used.

If those pass, the next research state is still **narrow localized-bug paper**, not real-project transfer. v2 only strengthens the source-known localized semantic bug audit.

## Outputs

Create:

- `analysis/decompile_faithfulness/run_dynamic_trace_v2_audit.py`
- `tests/test_decompile_faithfulness_dynamic_trace_v2.py`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.json`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.md`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.zh.md`
- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl`

Modify:

- `analysis/decompile_faithfulness/dynamic_trace.py`
- `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md`

## Spec Self-Review

- Placeholder scan: no TODO/TBD placeholders remain.
- Scope check: CPU-only, no GPU, no network, no dependencies, no subagents.
- Leakage check: input domains use fixture argument values only, not labels or candidate outputs.
- Paper-boundary check: v2 supports source-known localized-bug auditing; it does not justify real-project transfer by itself.
